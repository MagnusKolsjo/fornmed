"""
Bygger sökindexet: en sökpost per verk och per entitet med tid och plats.

Sökposten samlar det som sökningens filter och fasetter, kartan och
tidslinjen behöver, i en form som är densamma för alla källor:

- tre tider: tillkomst (verkets datering), förlaga (äldsta daterade vittne)
  och händelse (spannet för de påståenden som bygger på verket eller nämner
  entiteten)
- platser i rollerna handelse, tillkomst, forvaring och lage

Det som visas först är händelsen: när och var det påståendena beskriver ägde
rum. Saknas den visas tillkomsten, och sokpost.tid_kalla säger vilken det
är. Den andra informationen finns kvar i sina egna kolumner, så att den kan
visas för den som vill granska källan.

Förlagan är tills vidare det äldsta daterade vittnet. Vilket vittne en utgåva
bygger på är inte registrerat, och för de flesta brev saknar vittnena datering.

Indexet härleds helt ur övriga tabeller och byggs om från grunden, så det
kan köras om när som helst. Kör det efter inläsningar och platskopplingar och
före en leverans.

Användning:
    python sokindex.py
"""

import argparse
import logging
from collections import Counter, defaultdict

import db
from fragor import _rader, _sokform, _sprak

log = logging.getLogger(__name__)

SAMMANFATTNING_MAX_TECKEN = 400

# verk_plats-roller som anger var källan kom till. Socknen räknas bara när
# fyndplatsen saknas; härad, kommun och område är sammanhang, inte platsen.
TILLKOMSTROLLER = ("utfardandeort", "fyndplats")
SOCKENROLL = "socken"

# Vittnestyper som kan vara förlaga till en text. Fotokopior, faksimil, tryckta
# regester och proveniensuppgifter är det inte.
FORLAGETYPER = ("original", "handskrift", "medeltida_avskrift", "medeltida_registratur",
                "eftermedeltida_avskrift", "eftermedeltida_registratur", "tryck")

# Predikat vars plats inte är där något hände utan ett område som tillståndet
# eller normen gäller: kungen av Sverige, lagens bot i Västergötland,
# ämbetets ansvarsområde. Påståendenas tid räknas ändå, platsen inte.
PLATS_ANGER_OMRADE = {
    "innehar_ambete", "mister_ambete", "utnamner", "har_stand", "eftertrader", "styr_over", "ager",
    "ar_del_av", "ar_belagen_i", "foralder_till", "gift_med", "syskon_till", "harkomst", "omnamns",
    "stiftar_lag", "infor_palaga", "faststaller_grans", "indelar",
    "paforljd", "tillfaller", "handlaggs_vid", "utses_av", "kraver", "diskvalificerar", "definieras_som",
}

# Platsslag som är för stora för att ge ett läge på kartan. Land, landskap och
# län ändrar gränser; det är den minsta platsen som visas.
OMRADESSLAG = {"land", "landskap", "lan", "omrade", "område"}

KOLUMNER = ["id", "objekttyp", "undertyp", "kallsamling_id", "rubrik", "sammanfattning", "sprak",
            "soknamn", "tillkomst_edtf", "tillkomst_fran", "tillkomst_till", "forlaga_typ",
            "forlaga_edtf", "forlaga_fran", "forlaga_till", "handelse_fran", "handelse_till",
            "antal_pastaenden", "tid_fran", "tid_till", "tid_kalla"]
PLATSKOLUMNER = ["sokpost_id", "plats_id", "roll", "primar", "osaker", "antal"]


class Spann:
    """Tidsspann och platser för de påståenden som hör till ett objekt."""

    def __init__(self) -> None:
        self.fran: int | None = None
        self.till: int | None = None
        self.antal = 0
        self.platser: Counter = Counter()

    def lagg_till(self, tid_fran: int | None, tid_till: int | None, plats_id: str | None) -> None:
        self.antal += 1
        if tid_fran is not None:
            self.fran = tid_fran if self.fran is None else min(self.fran, tid_fran)
        if tid_till is not None:
            self.till = tid_till if self.till is None else max(self.till, tid_till)
        if plats_id:
            self.platser[plats_id] += 1


def _kort(text: str | None) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    if len(text) <= SAMMANFATTNING_MAX_TECKEN:
        return text
    return text[:SAMMANFATTNING_MAX_TECKEN].rsplit(" ", 1)[0] + " …"


def _pastaenden() -> tuple[dict[str, Spann], dict[str, Spann]]:
    """Påståendenas tider och platser samlade per verk och per entitet."""
    p = db._prefix()
    per_verk: dict[str, Spann] = defaultdict(Spann)
    per_entitet: dict[str, Spann] = defaultdict(Spann)
    for r in _rader(f"""SELECT pa.verk_id, pt.predikat, pt.subjekt_id, pt.objekt_id, pt.plats_id,
                               pt.tid_fran, pt.tid_till
                        FROM {p}pastaende pt JOIN {p}passage pa ON pa.id = pt.passage_id"""):
        plats_id = None if r["predikat"] in PLATS_ANGER_OMRADE else r["plats_id"]
        per_verk[r["verk_id"]].lagg_till(r["tid_fran"], r["tid_till"], plats_id)
        for entitet_id in {r["subjekt_id"], r["objekt_id"], r["plats_id"]} - {None}:
            per_entitet[entitet_id].lagg_till(r["tid_fran"], r["tid_till"], plats_id)
    return per_verk, per_entitet


def _forlagor() -> dict[str, dict]:
    """Det äldsta daterade vittnet per verk, bland typerna i FORLAGETYPER."""
    p = db._prefix()
    typer = ", ".join(f"'{t}'" for t in FORLAGETYPER)
    forlagor: dict[str, dict] = {}
    for r in _rader(f"""SELECT verk_id, typ, datering_edtf, datering_fran, datering_till FROM {p}vittne
                        WHERE datering_fran IS NOT NULL AND typ IN ({typer})
                        ORDER BY verk_id, datering_fran, id"""):
        forlagor.setdefault(r["verk_id"], r)
    return forlagor


def _sammanfattningar() -> dict[str, str]:
    """Verkets första regest, som sammanfattning av brev och runinskrifter."""
    p = db._prefix()
    ut: dict[str, str] = {}
    for r in _rader(f"""SELECT verk_id, substr(text, 1, {SAMMANFATTNING_MAX_TECKEN * 2}) AS text
                        FROM {p}passage WHERE typ = 'regest' ORDER BY verk_id, ordning, id"""):
        ut.setdefault(r["verk_id"], r["text"])
    return ut


def _verkens_platser() -> dict[str, list[tuple[str, str, bool]]]:
    """Verkets platser i sökindexets roller, som (plats_id, roll, osäker)."""
    p = db._prefix()
    per_verk: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in _rader(f"SELECT verk_id, plats_id, roll, osaker, harledd FROM {p}verk_plats"):
        per_verk[r["verk_id"]][r["roll"]].append((r["plats_id"], bool(r["osaker"]) or bool(r["harledd"])))
    ut: dict[str, list[tuple[str, str, bool]]] = {}
    for verk_id, roller in per_verk.items():
        platser = []
        tillkomst = [x for roll in TILLKOMSTROLLER for x in roller.get(roll, [])]
        for plats_id, osaker in tillkomst or roller.get(SOCKENROLL, []):
            platser.append((plats_id, "tillkomst", osaker))
        for plats_id, osaker in roller.get("forvaring", []):
            platser.append((plats_id, "forvaring", osaker))
        ut[verk_id] = platser
    return ut


def _tid(spann: Spann | None, fran: int | None, till: int | None) -> tuple[int | None, int | None, str | None]:
    """Den tid som visas först: händelsen om den är känd, annars tillkomsten."""
    if spann and spann.fran is not None:
        return spann.fran, spann.till if spann.till is not None else spann.fran, "handelse"
    if fran is not None:
        return fran, till, "tillkomst"
    return None, None, None


def _platsrader(post_id: str, handelse: Counter, ovriga: list[tuple[str, str, bool]],
                omraden: set[str], lage: str | None = None) -> list[tuple]:
    """
    Sökpostens platser. Primära är platsentitetens eget läge, annars
    händelsens platser, annars tillkomstens. Ett land eller landskap är
    bara primärt när det är platsentiteten själv.
    """
    rader: dict[tuple[str, str], list] = {}
    if lage:
        rader[(lage, "lage")] = [post_id, lage, "lage", True, False, 1]
    for plats_id, antal in handelse.items():
        primar = not lage and plats_id not in omraden
        rader[(plats_id, "handelse")] = [post_id, plats_id, "handelse", primar, False, antal]
    har_primar = any(r[3] for r in rader.values())
    for plats_id, roll, osaker in ovriga:
        if (plats_id, roll) not in rader:
            rader[(plats_id, roll)] = [post_id, plats_id, roll, roll == "tillkomst" and not har_primar, osaker, 1]
    return [tuple(r) for r in rader.values()]


def bygg() -> dict[str, int]:
    """Bygger om sokpost och sokpost_plats. Returnerar antal poster och platser."""
    p = db._prefix()
    per_verk, per_entitet = _pastaenden()
    forlagor = _forlagor()
    sammanfattningar = _sammanfattningar()
    verkens_platser = _verkens_platser()
    platser_finns = {r["id"] for r in _rader(f"SELECT id FROM {p}entitet")}
    omraden = {r["entitet_id"] for r in _rader(f"SELECT entitet_id, slag FROM {p}plats_uppgift")
               if r["slag"] in OMRADESSLAG}

    poster: list[tuple] = []
    platsrader: list[tuple] = []

    for v in _rader(f"""SELECT id, kallsamling_id, titel, genre, sprak, datering_edtf, datering_fran,
                               datering_till, beskrivning FROM {p}verk"""):
        spann = per_verk.get(v["id"])
        forlaga = forlagor.get(v["id"]) or {}
        tid_fran, tid_till, tid_kalla = _tid(spann, v["datering_fran"], v["datering_till"])
        poster.append((
            v["id"], "verk", v["genre"], v["kallsamling_id"], v["titel"],
            _kort(sammanfattningar.get(v["id"]) or v["beskrivning"]), db.sprakvarde(_sprak(v["sprak"])),
            _sokform(v["titel"]), v["datering_edtf"], v["datering_fran"], v["datering_till"],
            forlaga.get("typ"), forlaga.get("datering_edtf"), forlaga.get("datering_fran"),
            forlaga.get("datering_till"), spann.fran if spann else None, spann.till if spann else None,
            spann.antal if spann else 0, tid_fran, tid_till, tid_kalla,
        ))
        platsrader += _platsrader(v["id"], spann.platser if spann else Counter(),
                                  verkens_platser.get(v["id"], []), omraden)

    # Namnformerna i källorna och registrets termer (Ansgarius, Anskarius),
    # så att namnsökningen hittar entiteten på varje form
    namnformer: dict[str, set[str]] = defaultdict(set)
    for r in _rader(f"SELECT entitet_id, namnform FROM {p}entitet_namnform"):
        if r["namnform"]:
            namnformer[r["entitet_id"]].add(_sokform(r["namnform"]))
    for r in _rader(f"SELECT entitet_id, term FROM {p}term"):
        if r["term"]:
            namnformer[r["entitet_id"]].add(_sokform(r["term"]))

    platstyper = {"plats", "indelning"}
    for e in _rader(f"SELECT id, typ, namn, beskrivning FROM {p}entitet"):
        spann = per_entitet.get(e["id"])
        tid_fran, tid_till, tid_kalla = _tid(spann, None, None)
        soknamn = " | ".join([_sokform(e["namn"]), *sorted(namnformer.get(e["id"], set()) - {_sokform(e["namn"])})])
        poster.append((
            e["id"], "entitet", e["typ"], None, e["namn"], _kort(e["beskrivning"]), db.sprakvarde([]),
            soknamn, None, None, None, None, None, None, None,
            spann.fran if spann else None, spann.till if spann else None, spann.antal if spann else 0,
            tid_fran, tid_till, tid_kalla,
        ))
        platsrader += _platsrader(e["id"], spann.platser if spann else Counter(), [], omraden,
                                  e["id"] if e["typ"] in platstyper else None)

    platsrader = [r for r in platsrader if r[1] in platser_finns]
    if not db._ar_postgres():
        platsrader = [(*r[:3], int(r[3]), int(r[4]), r[5]) for r in platsrader]

    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {p}sokpost_plats")
        cur.execute(f"DELETE FROM {p}sokpost")
        conn.commit()
        db.upsert(conn, "sokpost", KOLUMNER, ["id"], poster)
        db.upsert(conn, "sokpost_plats", PLATSKOLUMNER, ["sokpost_id", "roll", "plats_id"], platsrader)
    finally:
        conn.close()
    return {"poster": len(poster), "platser": len(platsrader)}


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db.initiera_schema()
    antal = bygg()
    log.info("Sökindexet byggt: %(poster)d poster med %(platser)d platser", antal)


if __name__ == "__main__":
    main()

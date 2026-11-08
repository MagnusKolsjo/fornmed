"""
Länkar från Fornmeds poster till andra datamängder.

Tre slag av länkar tas fram och skrivs till data/lankar/lankar.tsv, som
versioneras, och läses sedan in i tabellen extern_lank:

- Runinskrifterna. Wikidatas objekt med Rundata-signum (P1261) kopplas till
  vittnet med samma signum, alltså stenen eller föremålet. Objektets
  K-samsök-URI:er (P1260) ger dessutom lämningen i Kulturmiljöregistret,
  museiföremål och posten i Samnordisk runtextdatabas. Den sista beskriver
  inskriften och kopplas därför till verket.
- TORA. Platser vars läge kommer från Riksarkivets TORA får länk till
  bebyggelseenheten. Numret står i platslexikonets beslut
  (data/platser/lexikon_beslut.tsv och brevgranskning.tsv).
- Kartverkets ortnamnsregister. Norska platser vars läge kommer från
  registret får länk till ortnamnet. Numret tas fram på samma sätt som
  läget, ur de sparade svaren i data/raw/ssr, och används bara när
  koordinaterna stämmer med platsregistrets. När Kartverkets ortnamn är en
  kyrka som fått representera en socken eller bygd blir länken rdfs:seeAlso:
  kyrkan är platsens läge men inte platsen själv.

Wikidata frågas bara med --hamta; utan flaggan används runinskrifternas
länkar som redan står i filen.

    python lankar.py --hamta      # hämta från Wikidata, härled övriga, läs in
    python lankar.py              # härled TORA och SSR, läs in
"""

import argparse
import csv
import logging
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import db
import platser
from fragor import _rader

log = logging.getLogger("lankar")

FIL = Path(__file__).parent / "data" / "lankar" / "lankar.tsv"
KOLUMNER = ("post_typ", "post_id", "relation", "uri", "kalla", "metod", "granskad")

WDQS = "https://query.wikidata.org/sparql"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
WIKIDATA = "http://www.wikidata.org/entity/"
KSAMSOK = "http://kulturarvsdata.se/"
TORA = "https://data.riksarkivet.se/tora/"
SSR = "https://stadnamn.kartverket.no/fakta/"

TORA_KALLA = "Riksarkivet: TORA"


def _signum(text: str) -> str:
    """Signum i jämförbar form: 'Öl 1', 'Öl  1' och 'öl 1' blir lika."""
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


# -----------------------------------------------------------------------------
# Runinskrifterna via Wikidata
# -----------------------------------------------------------------------------

def hamta_runinskrifter() -> list[dict]:
    """Wikidatas objekt med Rundata-signum och deras K-samsök-URI:er."""
    fraga = "SELECT ?objekt ?signum ?ksam WHERE { ?objekt wdt:P1261 ?signum . OPTIONAL { ?objekt wdt:P1260 ?ksam } }"
    url = WDQS + "?" + urllib.parse.urlencode({"query": fraga})
    begaran = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "text/csv"})
    with urllib.request.urlopen(begaran, timeout=120) as svar:
        rader = list(csv.DictReader(svar.read().decode("utf-8").splitlines()))
    log.info("Wikidata: %d rader med Rundata-signum", len(rader))
    return rader


def runinskrifter(wikidata: list[dict]) -> list[dict]:
    """Länkar för vittnen och verk vars signum finns i Wikidata."""
    vittnen: dict[str, list[dict]] = defaultdict(list)
    for r in _rader(f"SELECT id, verk_id, signum FROM {db._prefix()}vittne "
                    f"WHERE verk_id LIKE {db._ph()} AND signum IS NOT NULL", ("verk:runa:%",)):
        vittnen[_signum(r["signum"])].append(r)

    # Ett signum som Wikidata ger flera objekt, eller som flera vittnen har,
    # går inte att koppla säkert
    objekt_per_signum: dict[str, set[str]] = defaultdict(set)
    for r in wikidata:
        objekt_per_signum[_signum(r["signum"])].add(r["objekt"])

    ut, otydliga = [], 0
    for r in wikidata:
        nyckel = _signum(r["signum"])
        traffar = vittnen.get(nyckel, [])
        if len(traffar) != 1 or len(objekt_per_signum[nyckel]) != 1:
            otydliga += len(traffar) > 1 or len(objekt_per_signum[nyckel]) > 1
            continue
        vittne = traffar[0]
        ut.append({"post_typ": "vittne", "post_id": vittne["id"], "relation": "exactMatch",
                   "uri": r["objekt"], "kalla": "wikidata", "metod": "auktoritet"})
        sokvag = (r.get("ksam") or "").strip().lstrip("/")
        if not sokvag:
            continue
        uri = KSAMSOK + sokvag
        if sokvag.startswith("uu/srdb/"):
            # Samnordisk runtextdatabas beskriver inskriften, inte stenen
            ut.append({"post_typ": "verk", "post_id": vittne["verk_id"], "relation": "exactMatch",
                       "uri": uri, "kalla": "wikidata", "metod": "auktoritet"})
        elif sokvag.startswith(("raa/lamning/", "raa/fmi/")) or "/object/" in sokvag:
            ut.append({"post_typ": "vittne", "post_id": vittne["id"], "relation": "exactMatch",
                       "uri": uri, "kalla": "wikidata", "metod": "auktoritet"})
        else:
            ut.append({"post_typ": "vittne", "post_id": vittne["id"], "relation": "seeAlso",
                       "uri": uri, "kalla": "wikidata", "metod": "auktoritet"})
    log.info("Runinskrifter: %d länkar; %d signum utan entydig träff", len(ut), otydliga)
    return ut


# -----------------------------------------------------------------------------
# Platserna: TORA och Kartverket
# -----------------------------------------------------------------------------

def _platsuppgifter(kalla: str) -> dict[str, dict]:
    pf, ph = db._prefix(), db._ph()
    return {r["entitet_id"]: r for r in _rader(
        f"SELECT u.*, e.namn FROM {pf}plats_uppgift u JOIN {pf}entitet e ON e.id = u.entitet_id "
        f"WHERE u.kalla = {ph}", (kalla,))}


def _samma_lage(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) < 1e-5


def tora() -> list[dict]:
    """
    Platser vars läge kommer från TORA. Platslexikonets beslut gäller ett
    brev; brevets utfärdandeort är den plats som fick beslutets läge.
    """
    beslut = []
    for fil in (platser.LEXIKONFIL, platser.GRANSKNINGSFIL):
        if fil.exists():
            with fil.open(encoding="utf-8", newline="") as f:
                beslut += [r for r in csv.DictReader(f, delimiter="\t")
                           if r.get("kalla") == "tora" and (r.get("ref") or "").startswith("tora:")]
    uppgifter = _platsuppgifter(TORA_KALLA)
    orter: dict[str, set[str]] = defaultdict(set)
    for r in _rader(f"SELECT verk_id, plats_id FROM {db._prefix()}verk_plats WHERE roll = 'utfardandeort'"):
        orter[r["verk_id"]].add(r["plats_id"])

    tora_id: dict[str, set[str]] = defaultdict(set)
    for b in beslut:
        for plats_id in orter.get(b["verk_id"], ()):
            u = uppgifter.get(plats_id)
            if u and _samma_lage(u["latitud"], b["lat"]) and _samma_lage(u["longitud"], b["lon"]):
                tora_id[plats_id].add(b["ref"].split(":", 1)[1])
    ut = [{"post_typ": "entitet", "post_id": pid, "relation": "closeMatch", "uri": TORA + next(iter(nr)),
           "kalla": "tora", "metod": uppgifter[pid]["metod"]}
          for pid, nr in sorted(tora_id.items()) if len(nr) == 1]
    log.info("TORA: %d av %d platser med läge från TORA", len(ut), len(uppgifter))
    return ut


def ssr() -> list[dict]:
    """Norska platser vars läge kommer från Kartverkets ortnamnsregister."""
    traffar = platser._ssr()
    uppgifter = _platsuppgifter(platser.SSR_KALLA)
    ut = []
    for pid, u in sorted(uppgifter.items()):
        # Det nutida namnet är "Hosanger (Osterøy)" när kommunen behövs för att skilja orter åt
        for namn in dict.fromkeys(((u["nutida_namn"] or "").split(" (")[0], u["namn"])):
            lage = platser._ssr_lage(namn, traffar) if namn else None
            if lage and lage.get("stedsnummer") and _samma_lage(lage["latitud"], u["latitud"]) \
                    and _samma_lage(lage["longitud"], u["longitud"]):
                kyrka = lage["typ"] in ("Kirke", "Kirkested") and u.get("slag") != "kyrka"
                ut.append({"post_typ": "entitet", "post_id": pid, "relation": "seeAlso" if kyrka else "closeMatch",
                           "uri": SSR + str(lage["stedsnummer"]), "kalla": "ssr", "metod": u["metod"]})
                break
    log.info("Kartverket: %d av %d platser med läge från ortnamnsregistret", len(ut), len(uppgifter))
    return ut


# -----------------------------------------------------------------------------
# Fil och databas
# -----------------------------------------------------------------------------

def las_fil() -> list[dict]:
    if not FIL.exists():
        return []
    with FIL.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def skriv_fil(rader: list[dict]) -> None:
    FIL.parent.mkdir(parents=True, exist_ok=True)
    rader = sorted({(r["post_typ"], r["post_id"], r["uri"]): r for r in rader}.values(),
                   key=lambda r: (r["kalla"], r["post_typ"], r["post_id"], r["uri"]))
    with FIL.open("w", encoding="utf-8", newline="") as f:
        skrivare = csv.DictWriter(f, fieldnames=KOLUMNER, delimiter="\t", lineterminator="\n")
        skrivare.writeheader()
        for r in rader:
            skrivare.writerow({k: r.get(k, "") for k in KOLUMNER} | {"granskad": r.get("granskad") or "nej"})


def las_in(rader: list[dict]) -> None:
    """Ersätter tabellens innehåll med filens."""
    pf, ph = db._prefix(), db._ph()
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {pf}extern_lank")
        cur.executemany(
            f"INSERT INTO {pf}extern_lank (post_typ, post_id, uri, relation, kalla, metod, granskad) "
            f"VALUES ({', '.join([ph] * 7)})",
            [(r["post_typ"], r["post_id"], r["uri"], r["relation"], r["kalla"], r["metod"],
              r.get("granskad") == "ja") for r in rader])
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--hamta", action="store_true", help="hämta runinskrifternas länkar från Wikidata")
    args = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    db.initiera_schema()
    if args.hamta:
        runor = runinskrifter(hamta_runinskrifter())
    else:
        runor = [r for r in las_fil() if r["kalla"] == "wikidata"]
    rader = runor + tora() + ssr()
    skriv_fil(rader)
    las_in(las_fil())
    print(f"{len(las_fil())} länkar i {FIL.relative_to(Path(__file__).parent)} och i extern_lank")


if __name__ == "__main__":
    main()

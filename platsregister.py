"""
Hämtar och läser in stommen i platsregistret: Sveriges socknar, kommuner, län och
landskap samt världens länder, med koppling till Wikidata.

Stommen kommer från Riksantikvarieämbetets geografiska auktoriteter i K-samsök
(CC0). Wikidata (CC0) ger koordinater och socknarnas nutida kommun. Båda sparas i
data/platser, så att inläsningen inte behöver nätet.

Platserna får id:n som bildas av auktoritetens egen kod: plats:socken:<RAÄ-id>,
plats:kommun:<SCB-kod>, plats:lan:<länskod>, plats:landskap:<kod> och
plats:land:<alpha2>. Ett land eller landskap som redan finns under annat id, som
plats:sdhk:upland, behåller sitt id och kompletteras i stället.

Uppgifterna skrivs till plats_uppgift, och till entitet.wikidata_id där det saknas.
Inläsningen kan köras om; ett befintligt id ändras aldrig.

Användning:
    python platsregister.py hamta     # hämtar auktoriteter och Wikidata till data/platser
    python platsregister.py           # läser in i databasen
"""

import argparse
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import db
from fragor import _rader

log = logging.getLogger("platsregister")

KATALOG = Path(__file__).parent / "data" / "platser"
RAA_FIL = KATALOG / "raa_geo.json"
WIKIDATA_FIL = KATALOG / "wikidata_fakta.json"

RAA_URL = "https://kulturarvsdata.se/resurser/aukt/geo/"
WIKIDATA_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
KALLA = "Riksantikvarieämbetet, K-samsök"

_POST = re.compile(r'<owl:NamedIndividual rdf:about="[^"]*[#;]([^"#;]+)">(.*?)</owl:NamedIndividual>', re.S)


def _hamta_url(url: str, accept: str = "application/json") -> str:
    fraga = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    with urllib.request.urlopen(fraga, timeout=120) as svar:
        return svar.read().decode("utf-8")


def _poster(rdf: str):
    """(kod, namn, wikidata, wikipedia, innehåll) för varje post i auktoriteten."""
    for kod, innehall in _POST.findall(rdf):
        namn = re.search(r'<ksamsok:name(?: xml:lang="sv")?>([^<]+)', innehall)
        if not namn:
            continue
        wikidata = re.search(r"wikidata\.org/entity/(Q\d+)", innehall)
        wikipedia = re.search(r'"(https://sv\.wikipedia\.org/wiki/[^"]+)"', innehall)
        yield kod, namn.group(1).strip(), wikidata.group(1) if wikidata else None, \
            wikipedia.group(1) if wikipedia else None, innehall


def hamta_raa() -> dict:
    """RAÄ:s auktoriteter i kompakt form."""
    def las(slag: str) -> str:
        return _hamta_url(RAA_URL + slag, "application/rdf+xml")

    def under(innehall: str, slag: str) -> str | None:
        m = re.search(rf"{slag}#(\w+)\"", innehall)
        return m.group(1) if m else None

    return {
        "kalla": "Riksantikvarieämbetet, K-samsöks geografiska auktoriteter (CC0)",
        "land": [{"kod": k, "namn": n, "wikidata": w} for k, n, w, _, i in _poster(las("country"))],
        "landskap": [{"kod": k, "namn": n, "wikidata": w} for k, n, w, _, i in _poster(las("province"))],
        "lan": [{"kod": k, "namn": n, "wikidata": w} for k, n, w, _, i in _poster(las("county"))],
        "kommun": [{"kod": k, "namn": n, "wikidata": w, "lan": under(i, "county")}
                   for k, n, w, _, i in _poster(las("municipality"))],
        "socken": [{"kod": k, "namn": n, "wikidata": w, "wikipedia": wp, "landskap": under(i, "province")}
                   for k, n, w, wp, i in _poster(las("parish"))],
    }


def _anspraksvarde(pastaenden: list) -> str | dict | None:
    """Bästa värdet i en Wikidata-egenskap: det föredragna först, föråldrade sist."""
    rangordnade = sorted(pastaenden, key=lambda p: {"preferred": 0, "normal": 1}.get(p.get("rank"), 2))
    for p in rangordnade:
        varde = p.get("mainsnak", {}).get("datavalue", {}).get("value")
        if varde:
            return varde
    return None


def hamta_wikidata(q_id: list[str], kant: dict | None = None) -> dict:
    """Koordinater, kommunkod, land, överordnad plats och namn för Wikidata-posterna."""
    fakta = dict(kant or {})
    saknas = sorted(q for q in set(q_id) if q not in fakta)
    for start in range(0, len(saknas), 50):
        del_ = saknas[start:start + 50]
        fraga = urllib.parse.urlencode({
            "action": "wbgetentities", "format": "json", "ids": "|".join(del_),
            "props": "claims|labels", "languages": "sv|en",
        })
        for forsok in range(4):
            try:
                svar = json.loads(_hamta_url(f"{WIKIDATA_URL}?{fraga}"))
                break
            except OSError as fel:
                log.warning("Wikidata svarar inte (%s), försöker igen", fel)
                time.sleep(5 * (forsok + 1))
        else:
            raise RuntimeError("Wikidata svarar inte")
        for q, post in svar.get("entities", {}).items():
            krav = post.get("claims", {})
            koordinat = _anspraksvarde(krav.get("P625", []))
            land = _anspraksvarde(krav.get("P17", []))
            over = _anspraksvarde(krav.get("P131", []))
            etikett = post.get("labels", {})
            fakta[q] = {
                "namn": (etikett.get("sv") or etikett.get("en") or {}).get("value"),
                "lat": round(koordinat["latitude"], 5) if koordinat else None,
                "lon": round(koordinat["longitude"], 5) if koordinat else None,
                "land": land["id"] if land else None,
                "over": over["id"] if over else None,
                "kommunkod": _anspraksvarde(krav.get("P525", [])),
            }
        log.info("Wikidata: %d av %d", min(start + 50, len(saknas)), len(saknas))
        time.sleep(0.5)
    return fakta


def hamta() -> None:
    KATALOG.mkdir(parents=True, exist_ok=True)
    raa = hamta_raa()
    RAA_FIL.write_text(json.dumps(raa, ensure_ascii=False, indent=0), encoding="utf-8")
    q_id = [p["wikidata"] for slag in ("land", "landskap", "lan", "kommun", "socken")
            for p in raa[slag] if p.get("wikidata")]
    # Orterna som granskningen har knutit till Wikidata
    orter = (KATALOG / "orter.tsv").read_text(encoding="utf-8") if (KATALOG / "orter.tsv").exists() else ""
    q_id += re.findall(r"\bQ\d+\b", orter)
    uppslag = KATALOG / "x_uppslag.tsv"
    if uppslag.exists():
        q_id += re.findall(r"\bQ\d+\b", uppslag.read_text(encoding="utf-8"))
    delade = KATALOG / "delade_orter.json"
    if delade.exists():
        q_id += re.findall(r"\bQ\d+\b", delade.read_text(encoding="utf-8"))
    kant = json.loads(WIKIDATA_FIL.read_text(encoding="utf-8")) if WIKIDATA_FIL.exists() else {}
    fakta = hamta_wikidata(q_id, kant)
    WIKIDATA_FIL.write_text(json.dumps(fakta, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    log.info("%s", {slag: len(raa[slag]) for slag in ("land", "landskap", "lan", "kommun", "socken")})


def _visningsnamn(namn: str, slag: str, fakta: dict) -> str:
    """'Lunds kommun' och 'Adelsö socken': Wikidatas form där den är rätt, som har genitivet."""
    if slag == "kommun" and namn == "Gotland":
        return "Gotlands kommun"
    etikett = fakta.get("namn") or ""
    return etikett if etikett.endswith(f" {slag}") else f"{namn} {slag}"


def las_in() -> None:
    raa = json.loads(RAA_FIL.read_text(encoding="utf-8"))
    fakta = json.loads(WIKIDATA_FIL.read_text(encoding="utf-8"))
    p = db._prefix()
    befintliga: dict[str, str] = {}
    for r in _rader(f"SELECT id, namn FROM {p}entitet WHERE typ IN ('plats', 'indelning')"):
        # Handregistrerade platser går före de ur SDHK; runinskrifternas fyndplatser räknas inte
        if r["id"].startswith("plats:runa:"):
            continue
        # Exakt namn: ordform slår ihop dubbelteckning, och Kina är inte gården Kinna
        nyckel = r["namn"].casefold()
        if nyckel not in befintliga or befintliga[nyckel].startswith("plats:sdhk:"):
            befintliga[nyckel] = r["id"]

    entiteter, namnformer, uppgifter, wikidata = [], [], [], []

    def lagg_till(eid: str, typ: str, namn: str, post: dict, slag: str, kalla: str, **las_i) -> None:
        f = fakta.get(post.get("wikidata") or "", {})
        entiteter.append((eid, typ, namn, f"{slag.capitalize()} ur Riksantikvarieämbetets auktoriteter",
                          post.get("wikidata"), json.dumps({"raa_kod": post["kod"]}, ensure_ascii=False)))
        uppgifter.append((eid, slag, post["namn"], las_i.get("land_id"), las_i.get("landskap_id"), las_i.get("lan_id"),
                          las_i.get("kommun_id"), f.get("lat"), f.get("lon"), kalla, "auktoritet"))

    def befintlig_eller(eid: str, namn: str, post: dict, slag: str, typ: str, **las_i) -> str:
        """Land och landskap som redan finns behåller sina id:n."""
        finns = befintliga.get(namn.casefold())
        if finns:
            f = fakta.get(post.get("wikidata") or "", {})
            wikidata.append((post.get("wikidata"), finns))
            uppgifter.append((finns, slag, post["namn"], las_i.get("land_id"), None, None, None, f.get("lat"), f.get("lon"), KALLA, "auktoritet"))
            return finns
        lagg_till(eid, typ, namn, post, slag, KALLA, **las_i)
        return eid

    land = {x["kod"]: befintlig_eller(f"plats:land:{x['kod']}", x["namn"], x, "land", "plats") for x in raa["land"]}
    sverige = land["se"]
    landskap = {x["kod"]: befintlig_eller(f"plats:landskap:{x['kod']}", x["namn"], x, "landskap", "indelning", land_id=sverige)
                for x in raa["landskap"]}
    lan = {}
    for x in raa["lan"]:
        lan[x["kod"]] = f"plats:lan:{x['kod']}"
        lagg_till(lan[x["kod"]], "indelning", x["namn"], x, "lan", KALLA, land_id=sverige)
    kommun_per_q, lan_per_kommun = {}, {}
    for x in raa["kommun"]:
        eid = f"plats:kommun:{x['kod']}"
        kommun_per_q[x["wikidata"]] = eid
        lan_per_kommun[eid] = lan.get(x["kod"][:2])
        namn = _visningsnamn(x["namn"], "kommun", fakta.get(x["wikidata"] or "", {}))
        lagg_till(eid, "indelning", namn, x, "kommun", KALLA, land_id=sverige, lan_id=lan_per_kommun[eid])
        namnformer.append((eid, x["namn"]))
    for x in raa["socken"]:
        eid = f"plats:socken:{x['kod']}"
        f = fakta.get(x.get("wikidata") or "", {})
        kommun = kommun_per_q.get(f.get("over"))
        kalla = f"{KALLA}; Wikidata" if f else KALLA
        lagg_till(eid, "indelning", _visningsnamn(x["namn"], "socken", f), x, "socken", kalla, land_id=sverige,
                  landskap_id=landskap.get(x["landskap"]), lan_id=lan_per_kommun.get(kommun), kommun_id=kommun)
        namnformer.append((eid, x["namn"]))

    conn = db._hamta_db()
    try:
        db.upsert(conn, "entitet", ["id", "typ", "namn", "beskrivning", "wikidata_id", "extra"], ["id"], entiteter)
        db.upsert(conn, "entitet_namnform", ["entitet_id", "namnform"], ["entitet_id", "namnform"], namnformer)
        cur = conn.cursor()
        ph = db._ph()
        for q, eid in wikidata:
            if q:
                cur.execute(f"UPDATE {p}entitet SET wikidata_id = {ph} WHERE id = {ph} AND wikidata_id IS NULL", (q, eid))
        conn.commit()
        db.upsert(conn, "plats_uppgift", ["entitet_id", "slag", "nutida_namn", "land_id", "landskap_id", "lan_id", "kommun_id",
                                          "latitud", "longitud", "kalla", "metod"], ["entitet_id"], uppgifter)
    finally:
        conn.close()
    log.info("Stommen: %d nya eller uppdaterade platser, %d kompletterade, %d med koordinater.",
             len(entiteter), len(wikidata), sum(1 for u in uppgifter if u[7] is not None))


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("steg", nargs="?", choices=["hamta"])
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if argument.steg == "hamta":
        hamta()
    else:
        db.initiera_schema()
        las_in()


if __name__ == "__main__":
    main()

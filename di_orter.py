"""
Prövar språkmodellens förslag på nutida namn för Diplomatarium Islandicums utfärdandeorter och
skriver de som håller till data/platser/di_orter.tsv.

Förslagen (data/platser/di_normalisering/svar_*.jsonl) godtas aldrig på modellens ord. En isländsk
ort måste ha den föreslagna sýslan, eftersom gårdsnamnen (Saurbær, Breiðabólstaður) återkommer
över hela landet. I Icelandic Saga Map ska det finnas en enda plats med namnet och kartans
sysselkod ska stämma. Annars prövas Wikidata: en enda isländsk plats med namnet som etikett eller
alias (gård, kloster och kyrka inom 2 km räknas som en), och en plats i Saga Map inom 20 km med
samma sýsla. Orter i andra länder prövas som i
dn_orter.py. Regioner och okända orter får inget läge.

Användning:
    python di_orter.py
"""

import csv
import glob
import json
import logging
import math
import re
import time
from pathlib import Path

from dn_orter import _landkod, _wikidata, wikidata_lage
from platser import _isl_nyckel

log = logging.getLogger("di_orter")

KATALOG = Path(__file__).parent / "data" / "platser"
UT = KATALOG / "di_orter.tsv"
SAGAMAP = Path(__file__).parent / "data" / "raw" / "sagamap" / "platser.json"
UTAN_LAGE = {"region", "okand"}
NARA_KM = 20
SAMMA_KM = 2
RIKTNING = {"Austur": "Aus", "Vestur": "Ves", "Norður": "Nor", "Suður": "Suð"}
# Sýslor som delats i en östra och västra (norra, södra) del; utan riktning gäller båda
DELADE = {"Húnav": "Hún", "Ísafj": "Ísa", "Barða": "Bar", "Þinge": "Þin", "Skaft": "Ska", "Múlas": "Múl"}


def syssla_stammer(kod: str | None, syssla: str) -> bool:
    """Om Saga Maps sysselkod (AusHún01, Snæfe02) avser den föreslagna sýslan (Austur-Húnavatnssýsla)."""
    kod = re.sub(r"\d+$", "", kod or "")
    if not kod or kod.startswith("Foreign"):
        return False
    if (m := re.match(r"(Austur|Vestur|Norður|Suður)-(\w+)", syssla)):
        return kod == RIKTNING[m[1]] + m[2][:3]
    for ord_ in re.findall(r"\w+", syssla):
        if len(ord_) >= 5 and len(kod) >= 5 and kod.startswith(ord_[:5]):
            return True
        if ord_[:5] in DELADE and kod[:3] in {*RIKTNING.values(), "Mið"} and kod[3:] == DELADE[ord_[:5]]:
            return True
    return False


def _avstand_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (a[0] - b[0]) * 111.2
    dx = (a[1] - b[1]) * 111.2 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def sagamap_lage(forslag: dict, kartan: dict[str, list[dict]]) -> dict | None:
    """En enda plats i Saga Map med namnet och den föreslagna sýslan."""
    namn = forslag["nutida"].split(" í ")[0].split(" á ")[0]
    kandidater = [k for k in kartan.get(_isl_nyckel(namn), []) if syssla_stammer(k.get("county"), forslag["syssla"])]
    if len(kandidater) != 1:
        return None
    k = kandidater[0]
    return {"latitud": float(k["coordinates"][0]), "longitud": float(k["coordinates"][1]),
            "kalla": f"Icelandic Saga Map {k['id']}", "wikidata": ""}


def isl_wikidata_lage(forslag: dict, kodade: list[tuple[tuple[float, float], str]], landcache: dict) -> dict | None:
    """En enda isländsk plats i Wikidata med namnet (entiteter inom SAMMA_KM räknas som en), och
    inom NARA_KM från den en plats i Saga Map i samma sýsla."""
    namn = forslag["nutida"].casefold()
    traffar = _wikidata(action="wbsearchentities", search=forslag["nutida"], language="is", type="item", limit=10)
    godkanda = []
    for q in [t["id"] for t in traffar.get("search", [])]:
        time.sleep(0.1)
        e = _wikidata(action="wbgetentities", ids=q, props="labels|aliases|claims").get("entities", {}).get(q, {})
        etiketter = {v["value"].casefold() for v in e.get("labels", {}).values()}
        etiketter |= {a["value"].casefold() for lista in e.get("aliases", {}).values() for a in lista}
        koord = e.get("claims", {}).get("P625", [])
        lander = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P17", [])]
        if namn not in etiketter or not koord or not any(_landkod(l, landcache) == "is" for l in lander if l):
            continue
        v = koord[0]["mainsnak"]["datavalue"]["value"]
        punkt = (v["latitude"], v["longitude"])
        if any(_avstand_km(punkt, p) <= NARA_KM and syssla_stammer(kod, forslag["syssla"]) for p, kod in kodade):
            godkanda.append({"latitud": punkt[0], "longitud": punkt[1], "kalla": f"Wikidata {q}", "wikidata": q})
    # Gården, klostret och kyrkan kan vara egna entiteter; de räknas som en plats om de ligger samlade
    forsta = godkanda[0] if godkanda else None
    if forsta and all(_avstand_km((g["latitud"], g["longitud"]), (forsta["latitud"], forsta["longitud"])) <= SAMMA_KM
                      for g in godkanda):
        return forsta
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    kartan: dict[str, list[dict]] = {}
    kodade = []
    for plats in json.loads(SAGAMAP.read_text(encoding="utf-8")):
        if plats.get("coordinates") and plats.get("name"):
            kartan.setdefault(_isl_nyckel(plats["name"]), []).append(plats)
            if plats.get("county"):
                kodade.append(((float(plats["coordinates"][0]), float(plats["coordinates"][1])), plats["county"]))
    forslag = []
    for fil in sorted(glob.glob(str(KATALOG / "di_normalisering" / "svar_*.jsonl"))):
        forslag += [json.loads(r) for r in open(fil, encoding="utf-8") if r.strip()]
    rader, utfall, landcache = [], {}, {}
    for f in forslag:
        if not f.get("nutida") or f.get("typ") in UTAN_LAGE:
            utfall["utan läge"] = utfall.get("utan läge", 0) + 1
            continue
        lage = None
        try:
            if f.get("land") != "is":
                lage = wikidata_lage(f, landcache)
            elif f.get("syssla"):
                lage = sagamap_lage(f, kartan) or isl_wikidata_lage(f, kodade, landcache)
        except Exception as e:
            log.warning("%s: %s", f["namn"], e)
        nyckel = "godtagen" if lage else "inte bekräftad"
        utfall[nyckel] = utfall.get(nyckel, 0) + 1
        if lage:
            rader.append([f["namn"], f["nutida"], f.get("land", ""), f.get("typ", ""), f.get("syssla", ""),
                          lage["latitud"], lage["longitud"], lage["kalla"], lage["wikidata"],
                          f.get("sakerhet", ""), f.get("motivering", "")])
    with UT.open("w", encoding="utf-8", newline="") as fh:
        skrivare = csv.writer(fh, delimiter="\t", lineterminator="\n")
        skrivare.writerow(["namn", "nutida", "land", "typ", "syssla", "lat", "lon", "kalla", "wikidata", "sakerhet", "motivering"])
        skrivare.writerows(rader)
    log.info("%d förslag: %s", len(forslag), utfall)


if __name__ == "__main__":
    main()

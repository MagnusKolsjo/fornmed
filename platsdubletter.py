"""
Hittar platser som finns under två id:n och skriver dem till data/platser/platsdubletter.tsv.

Samma ort kan ha kommit in från flera håll: som brevort i SDHK, som fyndplats i Rundata,
som socken i RAÄ:s auktoriteter och som ort i DN, DF eller DI. Två platser räknas som
samma när

- namnet är detsamma (efter normalisering, utan registrets egen parentes som
  "(Hycklinge socken)" eller "(Uppland)") och lägena ligger högst GRANS_KM från
  varandra, eller
- de har samma nutida namn och samma socken, och namnen är detsamma eller bara
  stavas olika ("Rumblaborg", "Rumlaborg").

Platser vars namn anger en händelse eller ett tillfälle ("Edsbergs ting", "Kumla
ting") slås aldrig ihop med orten. Två av RAÄ:s socknar eller kommuner slås inte ihop
med varandra, och två fyndplatser i Rundata bara när de har samma socken, eftersom
källan skiljer dem åt med avsikt: parentesen i "Narsaq (Ø 42)" och "Narsaq (Ø 17a)"
anger två olika ruiner. En plats med fler än en kandidat avgörs inte.

Den plats som behålls väljs efter id:ts slag (BEHALL): auktoriteten först, sedan
projektets handregistrerade platser, brevorterna, de nordiska diplomatariernas och sist
fyndplatserna. Inom samma slag behålls det id som har flest kopplingar.

Filen är en lista över beslut. En rad som en gång har skrivits ändras aldrig, eftersom
den gamla id:n kan vara publicerad: nya dubletter läggs till efter de gamla. platser.py
läser filen och låter den gamla id:n hänvisa till den nya (identifieringen ersatt_av).
Kör platser.py först, så att lägena finns, och sedan platser.py igen efter det här.

Användning:
    python platsdubletter.py            # visa nya dubletter
    python platsdubletter.py --skriv    # lägg till dem i filen
"""

import argparse
import csv
import logging
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import db
from fragor import _rader
from normalisering import ordform

log = logging.getLogger("platsdubletter")

FIL = Path(__file__).parent / "data" / "platser" / "platsdubletter.tsv"
GRANS_KM = 2.0
# Namn som anger ett tillfälle eller en församling av människor på orten, inte orten själv
TILLFALLE = re.compile(r"\b(?:\w*ting|tinget|möte|mötet|marknad|marknaden|landsting|herredag|riksdag)\b", re.I)
AUKTORITET = ("plats:socken:", "plats:kommun:", "plats:lan:", "plats:landskap:", "plats:land:")
# Ordningen när en av två platser ska behållas
BEHALL = [AUKTORITET, ("plats:sdhk:", "plats:df:", "plats:dn:", "plats:di:", "plats:runa:", "plats:wd:", "plats:museum:")]


def _slag(pid: str) -> int:
    """Lägre tal behålls: auktoritet 0, handregistrerad 1, brevort 2, DF/DN/DI 3, fyndplats 4, Wikidata 5."""
    if pid.startswith(AUKTORITET):
        return 0
    for i, prefix in enumerate(("plats:sdhk:", ("plats:df:", "plats:dn:", "plats:di:"), "plats:runa:", "plats:wd:")):
        if pid.startswith(prefix):
            return i + 2
    return 1


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    skala = math.cos(math.radians((a[0] + b[0]) / 2))
    return 111.2 * math.hypot(a[0] - b[0], skala * (a[1] - b[1]))


def grundnamn(pid: str, namn: str) -> str:
    """'Bro (Hycklinge socken)' → 'bro'. I Rundatas och Wikidatas namn är parentesen en del av namnet."""
    if pid.startswith(("plats:runa:", "plats:wd:")):
        return ordform(namn)
    return ordform(re.sub(r"\s*\([^)]*\)\s*$", "", namn))


def las_beslut() -> dict[str, tuple[str, str]]:
    if not FIL.exists():
        return {}
    with FIL.open(encoding="utf-8", newline="") as f:
        return {r["gammalt_id"]: (r["nytt_id"], r["grund"]) for r in csv.DictReader(f, delimiter="\t")}


def hitta() -> list[tuple[str, str, str]]:
    """Nya dubletter som (gammalt id, nytt id, grund), utan sådana som redan står i filen."""
    p = db._prefix()
    ersatta = {r["entitet_id"] for r in _rader(f"SELECT entitet_id FROM {p}identifiering WHERE kommentar = 'ersatt_av'")}
    beslut = las_beslut()
    platser = {}
    for r in _rader(f"""SELECT e.id, e.namn, u.nutida_namn, u.socken_id, u.latitud, u.longitud
                         FROM {p}entitet e LEFT JOIN {p}plats_uppgift u ON u.entitet_id = e.id
                         WHERE e.typ IN ('plats', 'indelning') ORDER BY e.id"""):
        if r["id"] in ersatta or r["id"] in beslut or TILLFALLE.search(r["namn"]):
            continue
        platser[r["id"]] = r
    kopplingar = Counter()
    for r in _rader(f"""SELECT plats_id, count(*) AS n FROM (
                          SELECT plats_id FROM {p}verk_plats UNION ALL
                          SELECT plats_id FROM {p}pastaende WHERE plats_id IS NOT NULL) x GROUP BY plats_id"""):
        kopplingar[r["plats_id"]] = r["n"]

    par: dict[frozenset, str] = {}
    per_namn: dict[str, list[dict]] = {}
    for r in platser.values():
        if r["latitud"] is not None:
            per_namn.setdefault(grundnamn(r["id"], r["namn"]), []).append(r)
    for namn, lista in per_namn.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                if a["id"].startswith("plats:runa:") and b["id"].startswith("plats:runa:"):
                    continue
                km = _km((a["latitud"], a["longitud"]), (b["latitud"], b["longitud"]))
                if km <= GRANS_KM:
                    par.setdefault(frozenset((a["id"], b["id"])), f"samma namn, {km:.1f} km")
    per_socken: dict[tuple[str, str], list[dict]] = {}
    for r in platser.values():
        if r["socken_id"] and r["nutida_namn"]:
            per_socken.setdefault((ordform(r["nutida_namn"]), r["socken_id"]), []).append(r)
    for (_, socken), lista in per_socken.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                na, nb = grundnamn(a["id"], a["namn"]), grundnamn(b["id"], b["namn"])
                if na == nb or SequenceMatcher(None, na, nb).ratio() >= 0.85:
                    par.setdefault(frozenset((a["id"], b["id"])), f"samma nutida namn och socken ({socken})")

    # Paren bildar grupper: Gripsholm finns som brevort, fyndplats och DF-ort. En grupp slås
    # ihop till en plats, utom när den rymmer två auktoritetsplatser eller två fyndplatser,
    # som källan själv håller isär; då avgörs den inte.
    forald: dict[str, str] = {}

    def rot(x: str) -> str:
        while forald.get(x, x) != x:
            x = forald[x]
        return x

    for nyckel in par:
        a, b = sorted(nyckel)
        forald.setdefault(a, a)
        forald.setdefault(b, b)
        forald[rot(b)] = rot(a)
    grupper: dict[str, list[str]] = {}
    for pid in forald:
        grupper.setdefault(rot(pid), []).append(pid)
    nya = []
    for medlemmar in grupper.values():
        medlemmar.sort()
        fynd = [m for m in medlemmar if m.startswith("plats:runa:")]
        samma_socken = len({platser[m]["socken_id"] for m in fynd}) == 1 and platser[fynd[0]]["socken_id"] if fynd else True
        if sum(m.startswith(AUKTORITET) for m in medlemmar) > 1 or (len(fynd) > 1 and not samma_socken):
            log.info("Avgörs inte: %s", ", ".join(medlemmar))
            continue
        behall = min(medlemmar, key=lambda x: (_slag(x), -kopplingar[x], x))
        for m in medlemmar:
            if m != behall:
                grund = par.get(frozenset((m, behall))) or next(g for k, g in par.items() if m in k)
                nya.append((m, behall, grund))
    return nya


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--skriv", action="store_true", help="lägg till de nya dubletterna i filen")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    nya = hitta()
    namn = {r["id"]: r["namn"] for r in _rader(f"SELECT id, namn FROM {db._prefix()}entitet WHERE typ IN ('plats', 'indelning')")}
    for ersatt, behall, grund in nya:
        print(f"{ersatt}\t{namn.get(ersatt)}\t→ {behall}\t{namn.get(behall)}\t{grund}")
    log.info("%d nya dubletter", len(nya))
    if argument.skriv and nya:
        ny_fil = not FIL.exists()
        with FIL.open("a", encoding="utf-8", newline="") as f:
            skrivare = csv.writer(f, delimiter="\t", lineterminator="\n")
            if ny_fil:
                skrivare.writerow(["gammalt_id", "nytt_id", "grund"])
            skrivare.writerows(nya)


if __name__ == "__main__":
    main()

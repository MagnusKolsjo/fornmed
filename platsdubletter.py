"""
Hittar platser som finns under två id:n och skriver dem till data/platser/platsdubletter.tsv.

Samma ort kan ha kommit in från flera håll: som brevort i SDHK, som fyndplats i Rundata,
som socken i RAÄ:s auktoriteter och som ort i DN, DF eller DI. Två platser räknas som
samma när

- namnet är detsamma (efter normalisering, utan registrets egen parentes som
  "(Hycklinge socken)" eller "(Uppland)") och lägena ligger högst GRANS_KM från
  varandra, eller
- de har samma nutida namn och samma socken, och namnen är detsamma eller bara
  stavas olika ("Rumblaborg", "Rumlaborg"), eller
- de har samma Wikidata-objekt och är på samma nivå: ingen av dem är en byggnad på
  den andras ort, ett tillfälle på orten eller en del av den andras namn ("Mo Lom",
  "Lom"), de har inte olika slag (by och socken), och ingen av dem är en kommun eller
  ett län. "X i Y" jämförs som X ("Ås kloster i Halland", "Ås kloster"). Det är
  den enda regeln som slår ihop tillfällen, och då bara med varandra: Islandicums
  OCR-läsningar av alþingi är samma ting.
- de kommer ur samma diplomatarium (DN, DI eller DF), har samma nutida namn och läge
  inom DIPLOMATARIUM_KM, och namnen liknar varandra. Det fångar stavningsvarianter
  ("Tunsberg", "Tønsberg") och OCR-läsfel i Diplomatarium Islandicum ("Skalholti",
  "Skalholtl") bland platser som saknar socken. Namn som anger olika nivåer
  ("Vanse", "Vanse kirke"; "Tunsberg", "Tunsberghus") eller där det ena namnet är det
  andra med ett tillägg ("Lom", "Mo Lom") slås inte ihop, eftersom de avser olika
  platser som fått samma ungefärliga läge.

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
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import db
from fragor import _rader
from normalisering import ordform

log = logging.getLogger("platsdubletter")

FIL = Path(__file__).parent / "data" / "platser" / "platsdubletter.tsv"
GRANS_KM = 2.0
# Diplomatarieorterna har fått sitt läge ur samma normalisering, så samma plats har
# samma koordinater; avståndet tål bara avrundning
DIPLOMATARIUM_KM = 0.1
DIPLOMATARIUM = ("plats:dn:", "plats:di:", "plats:df:")
# Alþingi, Öxarárþingi och lögréttan är tinget och lagrådet, inte Þingvellir där de
# samlades. Mönstret känner igen dem också i Islandicums OCR-läsfel (Alþlngi, AlJ>ingi,
# Öxarárþlngi, Öxafárþlrtgi), som tillfällesregeln ovan inte fångar.
# "alp" är OCR:ns läsning av "alþ", men Álptamýri är en gård
ISLANDSKT_TING = re.compile(r"^(?:al[þjpf>]|alj)(?!ta)|oxa[rf]|logrett")
# Ord som anger en byggnad eller anläggning på orten och inte orten själv
# "liusi" är Islandicums vanligaste OCR-läsning av "húsi" (Koltlingsliúsi för Koldinghus)
NIVA = re.compile(r"(kirke|kirkja|kirkju|kyrkje|kyrka|kyrckia|kirckia|kirken|kloster|klaustr|slott|borg|hus|husi|liusi|gård|gaard)$")
# Namn som anger ett tillfälle eller en församling av människor på orten, inte orten själv
# Isländskans þing (Alþingi, Öxarárþingi) är tinget, inte Þingvellir där det hölls
TILLFALLE = re.compile(r"\b(?:\w*ting|tinget|möte|mötet|marknad|marknaden|landsting|herredag|riksdag|\w*þingi?)\b", re.I)
AUKTORITET = ("plats:socken:", "plats:kommun:", "plats:lan:", "plats:landskap:", "plats:land:")
# Nutida förvaltningsenheter slås aldrig ihop med en ort ur källorna efter Wikidata-objektet:
# Orusts kommun är inte Ordost, och Södertälje kommun inte Södertälje stad
NUTIDA_ENHET = ("plats:kommun:", "plats:lan:")
# "Visborg på Gotland", "Ås kloster i Halland": det första ledet är platsen
I_STALLET = re.compile(r"\s+(?:i|på|vid|uti|under)\s+.+$", re.I)
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


def _skrivform(namn: str) -> str:
    """'Vanse kirke (Farsund)' → 'vanse kirke'; 'Tunsbergshúsí' → 'tunsbergshusi'."""
    utan_parentes = re.sub(r"\s*\([^)]*\)\s*", " ", namn).strip(" .,-").casefold()
    return "".join(t for t in unicodedata.normalize("NFKD", utan_parentes) if not unicodedata.combining(t))


def _samma_niva(a: str, b: str) -> bool:
    """
    Falskt när namnen avser olika nivåer: en byggnad och orten ("vanse kirke", "vanse";
    "tunsberghus", "tunsberg"), eller en plats i en annan ("mo lom", "lom").
    """
    orda, ordb = a.split(), b.split()
    if orda != ordb and (set(orda) < set(ordb) or set(ordb) < set(orda)):
        return False
    return bool(NIVA.search(a.replace(" ", ""))) == bool(NIVA.search(b.replace(" ", "")))


# Byggnader när två platser har samma Wikidata-objekt. "borg" saknas: i Islandicum är
# Rómaborg och Kantaraborg städer, och Flensborg och Helsingborg är städernas namn
BYGGNAD = re.compile(r"(kirke|kirkja|kirkju|kyrkje|kyrka|kyrckia|kirckia|kirken|kloster|klaustr|slott|hus|husi|liusi|gård|gaard)$")


def annan_niva(a: str, b: str) -> bool:
    """
    Sant när platsen a avser något på eller i b, inte b självt: fler ord ("Haderslev
    slott", "Haderslev"), b:s namn med en byggnad efter ("Tunsbergshúsí", "Tunsberg"),
    eller ett tillfälle på en ort. "X i Y" jämförs som X.
    """
    # "Börje socken" och "Börje" är samma socken
    fa, fb = (re.sub(r"\s+socken$", "", _skrivform(I_STALLET.sub("", n))) for n in (a, b))
    if tillfalle(a) != tillfalle(b):
        return tillfalle(a)
    ord_a, ord_b = fa.split(), fb.split()
    if ord_a != ord_b and set(ord_b) < set(ord_a):
        return True
    ha, hb = fa.replace(" ", ""), fb.replace(" ", "")
    return len(ha) > len(hb) and ha.startswith(hb[:max(3, len(hb) - 2)]) \
        and bool(BYGGNAD.search(ha)) and not NIVA.search(hb)


def tillfalle(namn: str) -> bool:
    """Ett ting, ett möte eller en marknad, också i Islandicums OCR-läsningar av alþingi."""
    return bool(TILLFALLE.search(namn) or ISLANDSKT_TING.search(_skrivform(namn)))


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
    platser, tillfallen = {}, {}
    for r in _rader(f"""SELECT e.id, e.namn, e.wikidata_id, u.nutida_namn, u.socken_id, u.latitud, u.longitud, u.slag
                         FROM {p}entitet e LEFT JOIN {p}plats_uppgift u ON u.entitet_id = e.id
                         WHERE e.typ IN ('plats', 'indelning') ORDER BY e.id"""):
        if r["id"] in ersatta or r["id"] in beslut:
            continue
        (tillfallen if tillfalle(r["namn"]) else platser)[r["id"]] = r
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

    per_nutida: dict[tuple[str, str], list[dict]] = {}
    for r in platser.values():
        prefix = next((d for d in DIPLOMATARIUM if r["id"].startswith(d)), None)
        if prefix and not r["socken_id"] and r["nutida_namn"] and r["latitud"] is not None \
                and not ISLANDSKT_TING.search(_skrivform(r["namn"])):
            # Det nutida namnet har ibland kommunen i parentes: "Norderhov (Ringerike)"
            per_nutida.setdefault((prefix, grundnamn(r["id"], r["nutida_namn"])), []).append(r)
    for (_, nutida), lista in per_nutida.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                na, nb = grundnamn(a["id"], a["namn"]), grundnamn(b["id"], b["namn"])
                km = _km((a["latitud"], a["longitud"]), (b["latitud"], b["longitud"]))
                # Nivån bedöms på namnet som det skrivs: normaliseringen gör "Tunsberghus" till "tunsbergus"
                if km <= DIPLOMATARIUM_KM and _samma_niva(_skrivform(a["namn"]), _skrivform(b["namn"])) \
                        and SequenceMatcher(None, na, nb).ratio() >= 0.5:
                    par.setdefault(frozenset((a["id"], b["id"])), f"samma nutida namn och läge ({nutida}), olika stavning")

    per_wikidata: dict[str, list[dict]] = {}
    for r in list(platser.values()) + list(tillfallen.values()):
        # Rundatas fyndplatser hålls isär av källan själv och tas inte med här
        if r["wikidata_id"] and not r["id"].startswith(NUTIDA_ENHET + ("plats:runa:",)):
            per_wikidata.setdefault(r["wikidata_id"], []).append(r)
    for q, lista in per_wikidata.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                if annan_niva(a["namn"], b["namn"]) or annan_niva(b["namn"], a["namn"]) \
                        or (a["slag"] and b["slag"] and a["slag"] != b["slag"]):
                    continue
                par.setdefault(frozenset((a["id"], b["id"])), f"samma Wikidata-objekt ({q})")
    platser.update(tillfallen)

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

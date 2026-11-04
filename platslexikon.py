"""
Bestämmer brevorter med hjälp av historiska platsregister och brevets sammanhang.

Källorna är Riksarkivets: TORA, ett register över historiska bebyggelseenheter med
koordinater, de äldre geometriska kartorna 1630-1655 (CC BY 4.0) och Rosenbergs
geografiska lexikon (Public Domain Mark), med församling, härad och län. Ur TORA
används bara det som bygger på Riksarkivets egna verk: kartorna och Det medeltida
Sverige. Enheter från andras verk, som Svenska herrgårdar och Suecia, tas inte med.
Filerna hämtas till data/raw/platslexikon.

Samma namn finns på många håll, och det finns fler Malmö än det i Skåne. Ett namn
räcker därför aldrig: en kandidat godtas bara om dess överordnade enhet stämmer med
vad brevet själv säger, och ortnamnet räknas inte som bekräftelse. Prövningen sker
brev för brev: brevet ska nämna kandidatens härad, och bara en kandidat får ligga där.

Socken och landskap räcker inte ensamma. I prov på små orter med känt läge gav häradet
94 % rätt, socknen 75 % och landskapet än mindre, eftersom ett brev ofta nämner gods på
annat håll medan domaren och tinget hör hemma i häradet. Reglerna prövas med --utvardera på orter
vars läge redan är känt.

Användning:
    python platslexikon.py hamta
    python platslexikon.py --utvardera
    python platslexikon.py --skriv
"""

import argparse
import csv
import gzip
import json
import logging
import math
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import db
from fragor import _rader
from normalisering import ordform

log = logging.getLogger("platslexikon")

KATALOG = Path(__file__).parent / "data" / "raw" / "platslexikon"
LITEN_ORT = 20
ISOF_KATALOG = Path(__file__).parent / "data" / "raw" / "isof"
BESLUTSFIL = Path(__file__).parent / "data" / "platser" / "lexikon_beslut.tsv"
GRANSKNINGSFIL = Path(__file__).parent / "data" / "platser" / "brevgranskning.tsv"
FILER = {
    "kartor.csv": "https://zenodo.org/records/15121019/files/Basic_settlement_unit_v1.0.csv?download=1",
    "kartnamn.csv": "https://zenodo.org/records/13305098/files/Place_and_personal_names_v1.1.csv?download=1",
    "rosenberg.csv": "https://filer.riksarkivet.se/registerdata/Rosenberg/Rosenberg_bearbetad/csv/Rosenberg_bearbetad.csv",
}
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"

TORA_SPARQL = "https://tora.entryscape.net/store/sparql"
TORA_KALLOR = {"agk", "ygk", "dms"}
_TORA_PREFIX = """
PREFIX t: <https://data.riksarkivet.se/tora/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
"""
# Tjänsten orkar inte en enda stor fråga, så uppgifterna hämtas var för sig
TORA_ENHETER = """SELECT DISTINCT ?s ?namn ?lat ?lon ?kalla ?socken WHERE {
  ?s a t:HistoricalSettlementUnit ; skos:prefLabel ?namn ; dct:creator ?kalla .
  OPTIONAL { ?s geo:lat ?lat ; geo:long ?lon } OPTIONAL { ?s t:modernParish ?socken } }"""
TORA_NAMN = "SELECT DISTINCT ?s ?alt WHERE { ?s a t:HistoricalSettlementUnit ; skos:altLabel ?alt }"
TORA_HARAD = "SELECT DISTINCT ?s ?harad WHERE { ?s a t:HistoricalSettlementUnit ; t:earlyModernDistrict ?harad }"
TORA_SOCKNAR = "SELECT DISTINCT ?s ?namn ?landskap WHERE { ?s a t:ModernParish ; skos:prefLabel ?namn . OPTIONAL { ?s t:province_name ?landskap } }"
TORA_HARADER = "SELECT DISTINCT ?s ?namn WHERE { ?s a t:EarlyModernDistrict ; skos:prefLabel ?namn }"


# Länen i Rosenberg, 1880-talets indelning, och landskapen de omfattar
LAN_LANDSKAP = {
    "Stockholms län": {"Uppland", "Södermanland"}, "Stockholms stad": {"Uppland", "Södermanland"},
    "Uppsala län": {"Uppland"}, "Södermanlands län": {"Södermanland"}, "Östergötlands län": {"Östergötland"},
    "Jönköpings län": {"Småland"}, "Kronobergs län": {"Småland"}, "Kalmar län": {"Småland", "Öland"},
    "Gotlands län": {"Gotland"}, "Blekinge län": {"Blekinge"}, "Kristianstads län": {"Skåne"}, "Malmöhus län": {"Skåne"},
    "Hallands län": {"Halland"}, "Göteborgs och Bohus län": {"Bohuslän", "Västergötland"},
    "Älvsborgs län": {"Västergötland", "Dalsland"}, "Skaraborgs län": {"Västergötland"}, "Värmlands län": {"Värmland"},
    "Örebro län": {"Närke", "Västmanland", "Värmland"}, "Västmanlands län": {"Västmanland"},
    "Kopparbergs län": {"Dalarna"}, "Gävleborgs län": {"Gästrikland", "Hälsingland"},
    "Västernorrlands län": {"Medelpad", "Ångermanland"}, "Jämtlands län": {"Jämtland", "Härjedalen"},
    "Västerbottens län": {"Västerbotten", "Lappland"}, "Norrbottens län": {"Norrbotten", "Lappland"},
}
LANDSKAP = sorted({l for v in LAN_LANDSKAP.values() for l in v}, key=len, reverse=True)
# Stavning och andra namn på landskapen i regesterna
LANDSKAP_FORMER = {"Dalarna": ("Dalarna", "Dalarne"), "Skåne": ("Skåne",), "Öland": ("Öland",), "Gotland": ("Gotland",)}

SOCKEN_I_TEXT = re.compile(r"\b([A-ZÅÄÖ][\w-]+(?:[ -][A-ZÅÄÖ][\w-]+)?) (?:socken|sn)\b")
HARAD_I_TEXT = re.compile(r"\b((?:Norra |Södra |Västra |Östra |N\. |S\. |V\. |Ö\. )?[A-ZÅÄÖ][\w-]+) ?(?:härad|hd|h:d|hundare|tingslag|skeppslag|fjärding)\b")
AVGRANSNING = re.compile(r"\s+(?:h:d|hd|härad|hundare|tingslag|skeppslag|skplg|fjärding)$")
SUFFIX = re.compile(r"\s+(?:kyrka|sockenkyrka|kyrkby|gård|prästgård|slott|by)$")


def hamta() -> None:
    KATALOG.mkdir(parents=True, exist_ok=True)
    for namn, url in FILER.items():
        fraga = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(fraga, timeout=180) as svar:
            (KATALOG / namn).write_bytes(svar.read())
        log.info("Hämtade %s", namn)
    hamta_tora()


def _sparql(fraga: str) -> list[dict]:
    """Alla rader, sida för sida."""
    rader: list[dict] = []
    for start in range(0, 500000, 5000):
        data = urllib.parse.urlencode({"query": f"{_TORA_PREFIX}{fraga} ORDER BY ?s LIMIT 5000 OFFSET {start}"}).encode()
        begaran = urllib.request.Request(TORA_SPARQL, data=data, headers={
            "User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
        with urllib.request.urlopen(begaran, timeout=240) as svar:
            sida = json.load(svar)["results"]["bindings"]
        rader += [{k: v["value"] for k, v in rad.items()} for rad in sida]
        if len(sida) < 5000:
            return rader
    return rader


def _id(uri: str) -> str:
    return uri.rsplit("/", 1)[1]


def hamta_tora() -> None:
    socknar = {r["s"]: r for r in _sparql(TORA_SOCKNAR)}
    harader = {r["s"]: r["namn"] for r in _sparql(TORA_HARADER)}
    enheter: dict[str, dict] = {}
    for r in _sparql(TORA_ENHETER):
        if _id(r["kalla"]) not in TORA_KALLOR:
            continue
        post = enheter.setdefault(_id(r["s"]), {"namn": r["namn"], "alt": [], "kalla": _id(r["kalla"])})
        post.update({k: r[k] for k in ("lat", "lon") if r.get(k)})
        if (socken := socknar.get(r.get("socken"))):
            post["socken"], post["landskap"] = socken["namn"], socken.get("landskap")
    for r in _sparql(TORA_NAMN):
        if (post := enheter.get(_id(r["s"]))):
            post["alt"].append(r["alt"])
    for r in _sparql(TORA_HARAD):
        if (post := enheter.get(_id(r["s"]))) and r["harad"] in harader:
            post["harad"] = harader[r["harad"]]
    (KATALOG / "tora.json").write_text(json.dumps(enheter, ensure_ascii=False), encoding="utf-8")
    log.info("TORA: %d enheter", len(enheter))


def _las(namn: str) -> list[dict]:
    data = (KATALOG / namn).read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    prov = text[:2000]
    avgransare = max(";\t,", key=prov.count)
    csv.field_size_limit(10 ** 8)
    return list(csv.DictReader(text.splitlines(), delimiter=avgransare))


def _tal(text: str) -> float | None:
    try:
        return float((text or "").replace(",", "."))
    except ValueError:
        return None


def _enhet(namn: str | None) -> str:
    """Socknens eller häradets namn utan ändelse och utan genitiv, för jämförelse."""
    kort = AVGRANSNING.sub("", (namn or "").strip())
    kort = re.sub(r"\s+(?:socken|sn|församling)$", "", kort)
    form = ordform(kort)
    return form[:-1] if form.endswith("s") and len(form) > 4 else form


# Isofs lokaltyper som kan vara en brevort; terräng, ägomark och vatten är det sällan
ISOF_TYPER = {"bebyggelse", "bebyggelsenamn", "anläggning"}


def _isof(lagg_till) -> None:
    """Isofs ortnamn ur data/raw/isof (hamta_isof.py). Socknens koordinater räknas inte som platsens egna."""
    sedda = set()
    for fil in sorted(ISOF_KATALOG.glob("*.jsonl.gz")):
        with gzip.open(fil, "rt", encoding="utf-8") as f:
            for rad in f:
                r = json.loads(rad)
                if r["id"] in sedda or r.get("place_type") not in ISOF_TYPER or not r.get("parish_name"):
                    continue
                sedda.add(r["id"])
                eget = r.get("geometry_source") != "Socken"
                lagg_till(r["place_name"], "isof", f"isof:{r['id']}", r["parish_name"], r.get("district_name") or "",
                          {r["province_name"]} if r.get("province_name") else set(),
                          r.get("latitude") if eget else None, r.get("longitude") if eget else None)


def las_kandidater() -> dict[str, list[dict]]:
    """Registrens platser per namnform. Samma plats ur flera källor slås ihop på socken och landskap."""
    per_namn: dict[str, dict[tuple, dict]] = defaultdict(dict)

    def lagg_till(namn: str, kalla: str, ref: str, socken: str, harad: str, landskap: set[str],
                  lat: float | None, lon: float | None) -> None:
        if not namn:
            return
        nyckel = (_enhet(socken), tuple(sorted(landskap)))
        post = per_namn[ordform(namn)].setdefault(nyckel, {
            "namn": namn, "kalla": kalla, "ref": ref, "socken": socken, "harad": harad, "landskap": set(landskap),
            "lat": lat, "lon": lon,
        })
        # Kartorna har egna koordinater och går före lexikonet
        if post["lat"] is None and lat is not None:
            post.update(lat=lat, lon=lon, kalla=kalla, ref=ref)
        post["harad"] = post["harad"] or harad

    for nr, e in json.loads((KATALOG / "tora.json").read_text(encoding="utf-8")).items():
        lat, lon = _tal(e.get("lat")), _tal(e.get("lon"))
        for namn in [e["namn"], *e["alt"]]:
            lagg_till(namn.strip(), "tora", f"tora:{nr}", e.get("socken") or "", e.get("harad") or "",
                      {e["landskap"]} if e.get("landskap") else set(), lat, lon)
    for r in _las("kartor.csv"):
        lat, lon = _tal(r["tora_wgs84_lat"]), _tal(r["tora_wgs84_long"])
        for namn in [r["tora_prefLabel"], *re.split(r"[;,/]", r["tora_altLabel"] or "")]:
            lagg_till(namn.strip(), "kartor", f"tora:{r['toraid']}", r["parish"], r["hundred"], {r["tora_province"]}, lat, lon)
    for r in _las("kartnamn.csv"):
        if r["kategori"] == "bebyggelsenamn":
            lagg_till(r["namn"].strip(), "kartor", f"tora:{r['toraid']}", r["socken"], r["härad"], {r["landskap"]},
                      _tal(r["tora_wgs84_lat"]), _tal(r["tora_wgs84_long"]))
    if ISOF_KATALOG.exists():
        _isof(lagg_till)
    # Rosenberg säger vilket härad en församling hör till, vilket TORA ofta saknar
    harad_per_socken: dict[str, Counter] = defaultdict(Counter)
    for r in _las("rosenberg.csv"):
        harad = r["Harad"] or r["Tingslag"]
        lagg_till(r["Plats"].strip(), "rosenberg", f"rosenberg:{r['PostID']}", r["Forsamling"], harad,
                  LAN_LANDSKAP.get(r["Lan"], set()), None, None)
        if harad and r["Forsamling"]:
            for landskap in LAN_LANDSKAP.get(r["Lan"], ()):
                harad_per_socken[f"{landskap}|{_enhet(r['Forsamling'])}"][harad] += 1
    for poster in per_namn.values():
        for post in poster.values():
            if post["harad"]:
                continue
            for landskap in post["landskap"]:
                if (funna := harad_per_socken.get(f"{landskap}|{_enhet(post['socken'])}")):
                    post["harad"] = funna.most_common(1)[0][0]
                    break
    return {namn: list(poster.values()) for namn, poster in per_namn.items()}


def bevis_i_brev(text: str, namn: str) -> dict[str, set[str]]:
    """Socknar, härader och landskap som brevet nämner. Ortnamnet självt tas bort, så att det inte bekräftar sig självt."""
    rest = re.sub(rf"\b{re.escape(namn)}s?\b", " ", text)
    landskap = set()
    for ls in LANDSKAP:
        if any(re.search(rf"\b{f}\b", rest) for f in LANDSKAP_FORMER.get(ls, (ls,))):
            landskap.add(ls)
    return {
        "socken": {_enhet(m) for m in SOCKEN_I_TEXT.findall(rest)},
        "harad": {_enhet(m) for m in HARAD_I_TEXT.findall(rest)},
        "landskap": landskap,
    }


def avgor(kandidater: list[dict], bevis: dict[str, set[str]]) -> tuple[str, dict] | None:
    """(nivå, kandidat) när häradet pekar ut en enda kandidat, med socknen som förstärkning. Annars inget."""
    traffar = [k for k in kandidater if k["harad"] and _enhet(k["harad"]) in bevis["harad"]]
    # Samma plats kan komma ur flera källor med olika stavning av häradet
    per_socken = {}
    for k in sorted(traffar, key=lambda k: k["lat"] is None, reverse=True):
        per_socken[_enhet(k["socken"]) or k["ref"]] = k
    if len(per_socken) != 1:
        return None
    kandidat = next(iter(per_socken.values()))
    return ("socken+harad" if kandidat["socken"] and _enhet(kandidat["socken"]) in bevis["socken"] else "harad"), kandidat


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _socknar() -> dict[tuple[str, str], dict]:
    p = db._prefix()
    return {(r["landskap"], _enhet(r["nutida_namn"])): r for r in _rader(
        f"""SELECT u.entitet_id, u.nutida_namn, u.latitud, u.longitud, l.namn AS landskap FROM {p}plats_uppgift u
            JOIN {p}entitet l ON l.id = u.landskap_id WHERE u.slag = 'socken'
            ORDER BY u.metod = 'auktoritet', u.entitet_id""")}


def lage(kandidat: dict, socknar: dict) -> tuple[float | None, float | None, str | None]:
    """Kandidatens läge: dess eget, annars socknens som närmevärde."""
    if kandidat["lat"] is not None:
        return kandidat["lat"], kandidat["lon"], "eget"
    for landskap in kandidat["landskap"]:
        socken = socknar.get((landskap, _enhet(kandidat["socken"])))
        if socken and socken["latitud"] is not None:
            return socken["latitud"], socken["longitud"], "socken"
    return None, None, None


def _brev() -> list[dict]:
    p = db._prefix()
    return _rader(f"""SELECT vp.verk_id, e.id AS plats_id, e.namn, b.ort, b.utfardare, b.regest,
                             u.latitud, u.longitud, u.slag, u.anm, u.metod
                      FROM {p}verk_plats vp JOIN {p}entitet e ON e.id = vp.plats_id
                      JOIN {p}sdhk_brev b ON 'sdhk:' || b.sdhk_nr = vp.verk_id
                      LEFT JOIN {p}plats_uppgift u ON u.entitet_id = e.id
                      WHERE vp.roll = 'utfardandeort'""")


def _sokform(namn: str) -> str:
    return SUFFIX.sub("", re.sub(r"\s*\(.*$", "", namn)).strip()


def utvardera(gans_km: float = 15, liten_ort: int = LITEN_ORT) -> None:
    """Prövar reglerna på svenska orter vars läge är känt och inte är ett närmevärde.

    De stora städerna redovisas för sig. Ett brev från Stockholm handlar ofta om något
    annat håll, medan reglerna är tänkta för små orter där brevet rör trakten.
    """
    kandidater, socknar = las_kandidater(), _socknar()
    rader = [r for r in _brev() if r["latitud"] is not None and "närmevärde" not in (r["anm"] or "")
             and 55 < r["latitud"] < 70 and 10 < r["longitud"] < 25]
    antal = Counter(r["plats_id"] for r in rader)
    utfall: dict[str, Counter] = {"små orter": Counter(), "stora orter": Counter()}
    fel: list[tuple] = []
    orter: dict[str, set] = defaultdict(set)
    for rad in rader:
        grupp = "små orter" if antal[rad["plats_id"]] <= liten_ort else "stora orter"
        namn = _sokform(rad["namn"])
        egna = kandidater.get(ordform(namn))
        if not egna:
            utfall[grupp]["ingen kandidat"] += 1
            continue
        utfall[grupp]["har kandidat"] += 1
        text = " | ".join(filter(None, (rad["ort"], rad["utfardare"], rad["regest"])))
        beslut = avgor(egna, bevis_i_brev(text, namn))
        if not beslut:
            utfall[grupp]["inget avgjort"] += 1
            continue
        niva, kandidat = beslut
        lat, lon, _ = lage(kandidat, socknar)
        if lat is None:
            utfall[grupp][f"{niva}: utan läge"] += 1
            continue
        avstand = _km(rad["latitud"], rad["longitud"], lat, lon)
        ratt = avstand <= gans_km
        utfall[grupp][f"{niva}: {'rätt' if ratt else 'fel'}"] += 1
        orter[grupp].add(rad["plats_id"])
        if not ratt and grupp == "små orter":
            fel.append((round(avstand), namn, niva, kandidat["socken"], sorted(kandidat["landskap"]), rad["verk_id"]))
    for grupp, rakning in utfall.items():
        print(grupp, "orter med beslut:", len(orter[grupp]))
        for nyckel, n in sorted(rakning.items()):
            print(f"   {nyckel:24}{n:7}")
    for f_ in sorted(fel, reverse=True)[:30]:
        print(f_)


def skriv_beslut() -> None:
    """Lägger till beslut brev för brev för orter utan läge. Filen läses av platser.py.

    Fattade beslut står kvar. Databasen visar inte längre vilka orter de gäller, eftersom
    de orterna redan har läge, och en ny körning får inte tappa dem. Orter som granskarna
    har läst tas inte heller upp igen: det som inte placerades där lämnades medvetet.
    """
    kolumner = ["verk_id", "ort", "kandidat", "niva", "kalla", "ref", "socken", "harad", "landskap", "lat", "lon", "lage"]
    befintliga: list[dict] = []
    if BESLUTSFIL.exists():
        with BESLUTSFIL.open(encoding="utf-8", newline="") as f:
            befintliga = list(csv.DictReader(f, delimiter="\t"))
    avgjorda = {r["ort"] for r in befintliga}
    if GRANSKNINGSFIL.exists():
        with GRANSKNINGSFIL.open(encoding="utf-8", newline="") as f:
            avgjorda |= {r["ort"] for r in csv.DictReader(f, delimiter="\t")}

    kandidater, socknar = las_kandidater(), _socknar()
    nya = []
    alla = _brev()
    antal = Counter(r["plats_id"] for r in alla)
    for rad in alla:
        # Regeln håller på små orter; stora orters brev handlar ofta om annat håll
        if (rad["latitud"] is not None or rad["slag"] == "ej_plats" or rad["namn"] in avgjorda
                or antal[rad["plats_id"]] > LITEN_ORT):
            continue
        namn = _sokform(rad["namn"])
        egna = kandidater.get(ordform(namn))
        if not egna:
            continue
        text = " | ".join(filter(None, (rad["ort"], rad["utfardare"], rad["regest"])))
        beslut = avgor(egna, bevis_i_brev(text, namn))
        if not beslut:
            continue
        niva, k = beslut
        lat, lon, slag = lage(k, socknar)
        nya.append(dict(zip(kolumner, (rad["verk_id"], rad["namn"], k["namn"], niva, k["kalla"], k["ref"], k["socken"], k["harad"],
                                       ",".join(sorted(k["landskap"])), lat or "", lon or "", slag or ""))))
    rader = sorted(befintliga + nya, key=lambda r: (r["ort"], r["verk_id"]))
    with BESLUTSFIL.open("w", encoding="utf-8", newline="") as f:
        skrivare = csv.DictWriter(f, fieldnames=kolumner, delimiter="\t", lineterminator="\n")
        skrivare.writeheader()
        skrivare.writerows(rader)
    log.info("%d befintliga beslut, %d nya brev på %d nya orter", len(befintliga), len(nya), len({r["ort"] for r in nya}))


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("steg", nargs="?", choices=["hamta"])
    tolk.add_argument("--utvardera", action="store_true")
    tolk.add_argument("--skriv", action="store_true", help="skriv besluten till data/platser/lexikon_beslut.tsv")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if argument.steg == "hamta":
        hamta()
    elif argument.utvardera:
        utvardera()
    elif argument.skriv:
        skriv_beslut()


if __name__ == "__main__":
    main()

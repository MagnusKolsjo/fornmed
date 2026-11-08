"""
Bygger data/auktoriteter/personer.json: medeltida personer med levnadsår ur Svenskt
biografiskt lexikon (SBL) och Wikidata.

Listan används av pastaenden_sdhk.py för brevens personer som inte är regenter, påvar
eller biskopar: riksråd, lagmän, fogdar, frälsemän och präster. Levnadsåren gör att en
förekomst efter dödsåret aldrig förs till personen, och att två grupper som klustringen
höll isär blir samma person när de båda passar en och samma post (drotsen Bo Jonsson).

Källor:

- SBL, Riksarkivets nedladdningsbara datamängd (CC0):
  https://sok.riksarkivet.se/data-api/nedladdningsbara-datamangder/svenskt-biografiskt-lexikon/
  Filen SBL_2023.csv läggs i data/raw/sbl/. SBL täcker A–S. Bara personartiklar med
  dödsår eller födelseår före UTAN_FORE tas med.
- Wikidata (CC0): personer döda 1100–1600 med SBL-id eller medborgarskap i de nordiska
  rikena eller Kalmarunionen. Svaret sparas i data/raw/wikidata_personer.json.

Samma person i båda källorna (Wikidata-egenskapen P3217, SBL-id) blir en post. SBL:s år
går före Wikidatas, eftersom de är granskade mot källorna. SBL anger hur säkert ett år
är ("senast 1302", "omkring 1340", "levde på 1300-talet"); bara exakta år och "senast"
är en bortre gräns, "omkring" och "troligen" vidgas med fem år, och "tidigast", "levde"
och "efter" ger ingen gräns.

Personer som redan finns i regenter.json eller biskopar.json (samma Wikidata-id, eller
samma namn och dödsår) tas inte med här, så att en person har ett id. Ett id som en gång
delats ut behålls när listan byggs om, med Wikidata-id eller SBL-id som nyckel. Har en
post här senare visat sig vara en person i längderna, står den kvar med bara id, namn och
'ersatt_av', längdens id, så att det gamla id:t hänvisar dit.

Användning:
    python bygg_personlista.py --hamta   # hämta Wikidata på nytt
    python bygg_personlista.py           # bygg listan ur de sparade källorna
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path

from normalisering import ordform

log = logging.getLogger("bygg_personlista")

ROT = Path(__file__).parent
AUKTORITETER = ROT / "data" / "auktoriteter"
UT = AUKTORITETER / "personer.json"
SBL_FIL = ROT / "data" / "raw" / "sbl" / "SBL_2023.csv"
WIKIDATA_FIL = ROT / "data" / "raw" / "wikidata_personer.json"
SPARQL = "https://query.wikidata.org/sparql"
ANVANDARAGENT = "fornmed/1.0 (icke-kommersiell forskningsdatabas)"
SBL_URL = "https://sok.riksarkivet.se/sbl/Presentation.aspx?id={}"
# Personer som dog senare kan inte ha utfärdat ett medeltidsbrev
DOD_SENAST = 1600
UTAN_FORE = 1540
# Nordiska riken och Kalmarunionen: Sverige, Danmark, Norge, Finland, Island, Kalmarunionen
LANDER = ["Q34", "Q35", "Q20", "Q33", "Q189", "Q62623"]
# SBL-titlar som hör hemma i regent- och biskopslistorna. Wikidatas poster sorteras ut på
# Wikidata-id, så att norska och danska biskopar och riksföreståndare som inte finns i
# listorna står kvar här.
EGEN_LISTA = re.compile(r"\b(?:kung|drottning|påve|biskop|ärkebiskop|riksföreståndare|hertig)\b", re.I)

FRAGA = """
SELECT ?p ?namn ?enamn ?fodd ?fp ?dod ?dp ?sbl WHERE {
  { ?p wdt:P3217 [] } UNION { ?p wdt:P27 ?land . VALUES ?land { %s } }
  ?p wdt:P31 wd:Q5 ; p:P570/psv:P570 [ wikibase:timeValue ?dod ; wikibase:timePrecision ?dp ] .
  FILTER(YEAR(?dod) >= 1100 && YEAR(?dod) <= %d)
  OPTIONAL { ?p p:P569/psv:P569 [ wikibase:timeValue ?fodd ; wikibase:timePrecision ?fp ] . }
  OPTIONAL { ?p wdt:P3217 ?sbl . }
  OPTIONAL { ?p rdfs:label ?namn . FILTER(LANG(?namn) = "sv") }
  OPTIONAL { ?p rdfs:label ?enamn . FILTER(LANG(?enamn) = "en") }
}
"""
# Yrke (P106), befattning (P39), ätt (P53) och adelstitel (P97) på svenska, annars engelska
EGENSKAPER = """
SELECT ?p ?egenskap ?etikett WHERE {
  VALUES ?p { %s }
  VALUES ?egenskap { wdt:P106 wdt:P39 wdt:P53 wdt:P97 }
  ?p ?egenskap ?v .
  OPTIONAL { ?v rdfs:label ?sv . FILTER(LANG(?sv) = "sv") }
  OPTIONAL { ?v rdfs:label ?en . FILTER(LANG(?en) = "en") }
  BIND(COALESCE(?sv, ?en) AS ?etikett)
}
"""
ETT = {"P106": "yrke", "P39": "befattning", "P53": "att", "P97": "yrke"}
# Alias hämtas för sig, eftersom en fråga med båda överskrider Wikidatas tidsgräns
ALIAS = """
SELECT ?p ?alias WHERE {
  VALUES ?p { %s }
  ?p skos:altLabel ?alias . FILTER(LANG(?alias) IN ("sv", "da", "nb", "fi"))
}
"""


def _slug(s: str) -> str:
    s = ordform(s).replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _sparql(fraga: str) -> list[dict]:
    data = urllib.parse.urlencode({"query": fraga, "format": "json"}).encode()
    begaran = urllib.request.Request(SPARQL, data=data, headers={"User-Agent": ANVANDARAGENT,
                                                                  "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(begaran, timeout=300) as svar:
        return json.loads(svar.read())["results"]["bindings"]


def hamta_wikidata() -> None:
    rader = _sparql(FRAGA % (" ".join(f"wd:{q}" for q in LANDER), DOD_SENAST))
    q_id = sorted({r["p"]["value"].rsplit("/", 1)[1] for r in rader})
    alias: dict[str, set] = {}
    for i in range(0, len(q_id), 300):
        for r in _sparql(ALIAS % " ".join(f"wd:{q}" for q in q_id[i:i + 300])):
            alias.setdefault(r["p"]["value"].rsplit("/", 1)[1], set()).add(r["alias"]["value"])
    egenskaper: dict[str, dict[str, set]] = {}
    for i in range(0, len(q_id), 300):
        for r in _sparql(EGENSKAPER % " ".join(f"wd:{q}" for q in q_id[i:i + 300])):
            if r.get("etikett"):
                falt = ETT[r["egenskap"]["value"].rsplit("/", 1)[1]]
                egenskaper.setdefault(r["p"]["value"].rsplit("/", 1)[1], {}).setdefault(falt, set()).add(r["etikett"]["value"])
    for r in rader:
        q = r["p"]["value"].rsplit("/", 1)[1]
        r["alias"] = {"value": "|".join(sorted(alias.get(q, ())))}
        r["egenskaper"] = {k: sorted(v) for k, v in egenskaper.get(q, {}).items()}
    WIKIDATA_FIL.parent.mkdir(parents=True, exist_ok=True)
    WIKIDATA_FIL.write_text(json.dumps(rader, ensure_ascii=False), encoding="utf-8")
    log.info("Wikidata: %d rader, %d personer", len(rader), len(q_id))


def _ar(varde: str | None) -> int | None:
    try:
        return int(varde) if varde and int(varde) > 0 else None
    except ValueError:
        return None


def _grans(prefix: str, ar: int | None, bortre: bool) -> tuple[int | None, str]:
    """Ett år ur SBL som gräns: (år, typ). bortre=True för dödsår, False för födelseår."""
    if ar is None:
        return None, "saknas"
    p = (prefix or "").strip().lower()
    if not p:
        return ar, "exakt"
    if p.startswith("senast"):
        # "senast 1302" är en bortre gräns för dödsåret men ingen gräns för födelseåret
        return (ar, "senast") if bortre else (None, p)
    if p.startswith(("omkring", "troligen", "ca", "omkr")):
        return (ar + 5 if bortre else ar - 5), "omkring"
    if p.startswith("tidigast") and not bortre:
        return ar, "tidigast"
    return None, p


def las_sbl() -> list[dict]:
    if not SBL_FIL.exists():
        raise SystemExit(f"{SBL_FIL} saknas; hämta SBL_2023.csv från Riksarkivet (se dokumentationen)")
    poster = []
    with SBL_FIL.open(encoding="latin-1", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["Type of article"] != "Person article":
                continue
            # Medeltida personer står med hela namnet i efternamnsfältet ("Abraham Brodersson"),
            # senare med släktnamnet där och förnamnen för sig ("And", "Israel Andersson")
            fornamn, efter = r["Given name"].strip(), r["Surname"].strip()
            namn = f"{fornamn} {efter}".strip() if fornamn else efter
            dod, dod_typ = _grans(r["Prefix to year of death"], _ar(r["Year of death"]), True)
            fodd, fodd_typ = _grans(r["Prefix to year of birth"], _ar(r["Year of birth"]), False)
            if not (dod and dod <= DOD_SENAST + 5) and not (fodd and fodd <= UTAN_FORE):
                continue
            poster.append({"namn": namn, "fodd": fodd, "fodd_typ": fodd_typ, "dod": dod, "dod_typ": dod_typ,
                           "titel": None if r["Occupation, royal title, rank"] == "NULL" else r["Occupation, royal title, rank"],
                           "sbl": r["Article id"], "wikidata": None, "kalla": "SBL"})
    return poster


def _att(etiketter: list[str]) -> str | None:
    """Ättens namn som breven skriver det: 'Läma', 'Ulvåsaätten' → 'Ulvåsa', 'Färla, Martin Bengtssons ätt' → 'Färla'."""
    for e in etiketter:
        namn = re.sub(r"(?:ätten|ätt|släkten|släkt)$", "", e.split(",")[0].strip()).strip(" -")
        if namn and " " not in namn and not re.fullmatch(r"Q\d+", namn):
            return namn
    return None


def _wd_ar(tid: str) -> int:
    """Året ur Wikidatas tidsvärde: '1360-01-01T00:00:00Z' eller '+1360-…'."""
    return int(re.match(r"[+-]?(\d+)-", tid).group(1))


def las_wikidata() -> list[dict]:
    if not WIKIDATA_FIL.exists():
        raise SystemExit(f"{WIKIDATA_FIL} saknas; kör med --hamta")
    poster: dict[str, dict] = {}
    for r in json.loads(WIKIDATA_FIL.read_text(encoding="utf-8")):
        q = r["p"]["value"].rsplit("/", 1)[1]
        namn = (r.get("namn") or r.get("enamn") or {}).get("value")
        if not namn or re.fullmatch(r"Q\d+", namn):
            continue
        # Dag eller månad (precision 10–11) och år (9) ger ett exakt år; årtionde och sämre ingen gräns
        dp, fp = int(r["dp"]["value"]), int(r["fp"]["value"]) if r.get("fp") else 0
        dod = _wd_ar(r["dod"]["value"]) if dp >= 9 else None
        fodd = _wd_ar(r["fodd"]["value"]) if r.get("fodd") and fp >= 9 else None
        eg = r.get("egenskaper", {})
        yrken = [y for y in eg.get("befattning", []) + eg.get("yrke", []) if not re.fullmatch(r"Q\d+", y)]
        post = poster.setdefault(q, {"namn": namn, "fodd": fodd, "fodd_typ": "exakt" if fodd else "saknas",
                                     "dod": dod, "dod_typ": "exakt" if dod else "saknas",
                                     "titel": ", ".join(dict.fromkeys(yrken)) or None, "att": _att(eg.get("att", [])),
                                     "sbl": r.get("sbl", {}).get("value"), "wikidata": q, "kalla": "Wikidata",
                                     "alias": set()})
        post["alias"] |= {a for a in r.get("alias", {}).get("value", "").split("|") if a}
    for post in poster.values():
        post["alias"] = sorted(post["alias"])
    return list(poster.values())


def bygg() -> list[dict]:
    sbl = {p["sbl"]: p for p in las_sbl()}
    personer: list[dict] = []
    for w in las_wikidata():
        if w["sbl"] and w["sbl"] in sbl:
            s = sbl.pop(w["sbl"])
            # SBL:s år och namn går före; Wikidata ger id och alias
            personer.append({**s, "wikidata": w["wikidata"], "alias": w["alias"], "kalla": "SBL, Wikidata",
                             "wd_titel": w["titel"], "att": w["att"],
                             "fodd": s["fodd"] or w["fodd"], "fodd_typ": s["fodd_typ"] if s["fodd"] else w["fodd_typ"],
                             "dod": s["dod"] or w["dod"], "dod_typ": s["dod_typ"] if s["dod"] else w["dod_typ"]})
        else:
            personer.append({**w, "wd_titel": w["titel"], "titel": None})
    personer += [{**s, "alias": [], "wd_titel": None, "att": None} for s in sbl.values()]
    # Ätten blir en namnform: "Erik Kettilsson" med ätten Puke kan också stå som "Erik Kettilsson (Puke)"
    for p in personer:
        if p["att"] and ordform(p["att"]) not in ordform(p["namn"]):
            p["alias"] = sorted({*p["alias"], f"{p['namn']} ({p['att']})"})

    # Regenter, påvar och biskopar har egna listor
    egna_q: dict[str, str] = {}
    egna_namn: dict[tuple, str] = {}
    for fil in ("regenter.json", "biskopar.json"):
        for p in json.loads((AUKTORITETER / fil).read_text(encoding="utf-8"))["personer"]:
            if p.get("wikidata"):
                egna_q.setdefault(p["wikidata"], p["id"])
            egna_namn.setdefault((ordform(p["namn"]), p.get("dod")), p["id"])
    personer = [p for p in personer if p["wikidata"] not in egna_q and (ordform(p["namn"]), p["dod"]) not in egna_namn
                and not (p["titel"] and EGEN_LISTA.search(p["titel"]))
]

    # Stabila id:n: samma Wikidata- eller SBL-id ger samma id som förra gången
    tidigare = json.loads(UT.read_text(encoding="utf-8"))["personer"] if UT.exists() else []
    per_nyckel = {}
    for p in tidigare:
        for nyckel in (p.get("wikidata"), f"sbl:{p['sbl']}" if p.get("sbl") else None):
            if nyckel:
                per_nyckel[nyckel] = p["id"]
    utdelade = {p["id"] for p in tidigare}
    tagna: set[str] = set()
    for p in sorted(personer, key=lambda p: (p["wikidata"] is None, p["wikidata"] or "", p["sbl"] or "")):
        pid = per_nyckel.get(p["wikidata"]) or per_nyckel.get(f"sbl:{p['sbl']}" if p["sbl"] else None)
        if pid is None or pid in tagna:
            bas = f"person:{_slug(p['namn'])}_{p['dod'] or p['fodd'] or 'x'}"
            pid, n = bas, 2
            while pid in utdelade or pid in tagna:
                pid, n = f"{bas}_{n}", n + 1
        tagna.add(pid)
        p["id"] = pid
        if p["sbl"]:
            p["sbl_url"] = SBL_URL.format(p["sbl"])
    # Ett id som en gång delats ut försvinner aldrig: en post som inte längre finns i
    # källorna står kvar som den var
    for gammal in tidigare:
        if gammal["id"] in tagna:
            continue
        ersatt_av = gammal.get("ersatt_av") or egna_q.get(gammal.get("wikidata")) \
            or egna_namn.get((ordform(gammal["namn"]), gammal.get("dod")))
        if ersatt_av:
            personer.append({"id": gammal["id"], "namn": gammal["namn"], "ersatt_av": ersatt_av})
        else:
            log.warning("%s (%s) finns inte längre i källorna och står kvar", gammal["id"], gammal["namn"])
            personer.append({**gammal, "kvar_fran_tidigare": True})
    personer.sort(key=lambda p: p["id"])
    return personer


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--hamta", action="store_true", help="hämta Wikidata på nytt")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if argument.hamta or not WIKIDATA_FIL.exists():
        hamta_wikidata()
    personer = bygg()
    UT.write_text(json.dumps({
        "beskrivning": "Medeltida personer med levnadsår ur Svenskt biografiskt lexikon (Riksarkivet, CC0) och "
                       "Wikidata (CC0). Byggs av bygg_personlista.py. dod_typ 'exakt' och 'senast' är en bortre "
                       "gräns; 'omkring' är vidgad med fem år.",
        "personer": personer}, ensure_ascii=False, indent=1), encoding="utf-8")
    aktuella = [p for p in personer if not p.get("ersatt_av")]
    log.info("%d personer, varav %d med dödsår (%d ur SBL, %d ur båda källorna); %d ersatta av längderna",
             len(aktuella), sum(1 for p in aktuella if p["dod"]), sum(1 for p in aktuella if "SBL" in p["kalla"]),
             sum(1 for p in aktuella if p["kalla"] == "SBL, Wikidata"), len(personer) - len(aktuella))


if __name__ == "__main__":
    main()

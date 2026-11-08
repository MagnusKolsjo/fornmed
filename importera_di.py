"""
Importerar Diplomatarium Islandicum (band 1–16) ur OCR-texten i data/raw/diplomatarium_islandicum.

Brevens nummer, datering, rubrik och sida kommer från bandens innehållsförteckning ("Röð og
efni bréfanna"), som en språkmodell har skrivit av från sidbilderna (data/di_forteckning/svar),
eftersom OCR:n läser numren dåligt. Numren rättas efter ordningen. Brevtexten tas ur OCR-texten:
på den sida förteckningen anger söks brevets rubrikrad ("22.	[Juni 1096].	á alþingi."), och
texten fram till nästa brevs rubrik hör till brevet. Hittas ingen rubrikrad får brevet ingen
egen text (grans_osaker); texten står då kvar hos föregående brev, vars uppgifter anger vilka
brev den också omfattar (texten_omfattar_aven).

Sidhuvuden tas bort och fotnoterna blir noter. Ord som är avstavade vid radslut sätts ihop.
Bildlänken går till sidan på bækur.is: band och sida i skanningens ordning.

Användning:
    python importera_di.py --prov        # räkna brev och rubrikträffar utan att skriva
    python importera_di.py
"""

import argparse
import glob
import json
import logging
import re
import unicodedata
import zipfile
from collections import Counter
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path

import db
from importera_dn import MANADER, datum, las_sprak

log = logging.getLogger("importera_di")

KATALOG = Path(__file__).parent / "data" / "raw" / "diplomatarium_islandicum"
FORTECKNING = Path(__file__).parent / "data" / "di_forteckning" / "svar"
# Brevtextens språk: sprakklassning.py och, där den är osäker, språkmodellens bedömning (sprak_samla.py)
SPRAKFIL = Path(__file__).parent / "data" / "sprak" / "di_sprak.tsv"
MODELLFIL = Path(__file__).parent / "data" / "sprak" / "di_sprak_modell.tsv"
BILD = "https://baekur.is/bok/676591e5-5556-493c-83b6-f8ffce008ea4/{band}/{sida}"
KALLA_URL = "https://baekur.is/bok/676591e5-5556-493c-83b6-f8ffce008ea4"
MANADER_DI = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "maí": 5, "mai": 5, "jún": 6, "jun": 6, "júl": 7, "jul": 7,
              "ágú": 8, "aug": 8, "agú": 8, "sep": 9, "okt": 10, "oct": 10, "nóv": 11, "nov": 11, "des": 12, "dec": 12}
FOTNOT = re.compile(r"^\s*\d{1,2}\s*\)\s")
UTANFOR = re.compile(r"REGIST|NAFNA|EFNI|LEIÐRÉTT|LEIDRÉTT|FORMÁL|INNGANG|SKAMMSTAF", re.I)
# Siffror som OCR förväxlar: 353 läses "358", 347 "847"
FORVAXLING = {"8": "3", "3": "8", "6": "5", "5": "6", "7": "1", "1": "74", "0": "8", "9": "0", "4": "1"}


def _band(fil: Path) -> int:
    return int(re.search(r"_(\d+)\.zip$", fil.name)[1])


def _sidhuvud(rader: list[str]) -> int:
    """Antal rader i sidhuvudet: sidnummer, årtal och rubrik i versaler, högst tre rader."""
    n = 0
    for rad in rader[:3]:
        r = rad.strip()
        bokstaver = [c for c in r if c.isalpha()]
        if (not r or re.fullmatch(r"[\dIVXLCivxlc]{1,5}\.?|\[?1?\d{3}\.?\]?\.?|\d{3,4}\s*[—-]\s*\d{3,4}\.?", r)
                or (bokstaver and sum(c.isupper() for c in bokstaver) / len(bokstaver) > 0.7 and len(r) < 70)):
            n += 1
        else:
            break
    return n


def _sida(text: str) -> tuple[list[str], list[str], bool]:
    """Sidans brödtext, fotnoter och om sidan hör till breven (inte förteckning eller register)."""
    rader = text.lstrip("﻿").splitlines()
    huvud = rader[:_sidhuvud(rader)]
    brevsida = not (any(UTANFOR.search(h) for h in huvud)
                    or sum(bool(re.search(r"\.{4,}|(?:\.\s){4,}|…", r)) for r in rader) >= 3)
    rader = rader[len(huvud):]
    for i, rad in enumerate(rader):
        # Fotnoterna står sist: en rad som börjar "1)" där resten av sidan är noter
        if (FOTNOT.match(rad) and i > len(rader) * 0.4
                and sum(bool(re.search(r"\d\)", r)) for r in rader[i:]) >= (len(rader) - i) * 0.5):
            return rader[:i], rader[i:], brevsida
    return rader, [], brevsida


def _tryckt_sida(text: str) -> int | None:
    huvud = text.lstrip("﻿").splitlines()[:3]
    return next((int(h.strip()) for h in huvud if re.fullmatch(r"\d{1,4}", h.strip())), None)


def _sammanfoga(rader: list[str]) -> str:
    text = ""
    for rad in rader:
        rad = rad.strip()
        if not rad:
            continue
        if text.endswith("-") and rad[:1].islower():
            text = text[:-1] + rad
        else:
            text = f"{text} {rad}" if text else rad
    return re.sub(r"\s+", " ", text).strip()


def _varianter(nr: int) -> set[str]:
    """Numret och de former OCR:ns sifferförväxlingar kan ge det."""
    former = {str(nr)}
    for k, siffra in enumerate(str(nr)):
        for ersattning in FORVAXLING.get(siffra, ""):
            former |= {f[:k] + ersattning + f[k + 1:] for f in list(former)}
    return former


def las_forteckning(band: int) -> list[dict]:
    """Förteckningens poster för bandet, i ordning, med nummer rättade efter ordningen.

    En post med två nummer ("142—143") gäller brev som utgåvan trycker tillsammans; den får det
    första numret och det sista i nr_till. Avskriftens nummer gäller, så luckor står kvar; ett
    nummer bakåt eller långt fram ersätts med det väntade.
    """
    def las(monster: str) -> list[dict]:
        rader = []
        for fil in sorted(glob.glob(str(FORTECKNING / monster))):
            rader += [r for rad in open(fil, encoding="utf-8") if rad.strip()
                      and (r := json.loads(rad))["bild"].startswith(f"band{band:02}_")]
        return rader

    # Sidor med luckor är avskrivna en gång till (om_*.jsonl); den avskriften gäller för sidan
    om = las("om_*.jsonl")
    omskrivna = {r["bild"] for r in om}
    poster = sorted([r for r in las("del_*.jsonl") if r["bild"] not in omskrivna] + om,
                    key=lambda r: r["bild"])
    def forsta_tal(r: dict) -> int | None:
        tal = re.findall(r"\d+", r.get("nr") or "")
        return int(tal[0]) if tal else None

    resultat, forvantat = [], None
    for k, r in enumerate(poster):
        tal = [int(t) for t in re.findall(r"\d+", r.get("nr") or "")]
        nr = tal[0] if tal else None
        nasta = forsta_tal(poster[k + 1]) if k + 1 < len(poster) else None
        # Avskriftens nummer gäller, och en lucka är poster som saknas, men bara om nästa post fortsätter
        # därifrån. Annars är numret ett läsfel och får det väntade. Ett lågt nummer efter en lång följd
        # är ett tillägg med egen numrering.
        upprepat = nr is not None and resultat and nr == resultat[-1]["nr"]
        if forvantat is not None and nr != forvantat and not upprepat and not (nr is not None and nr < 10 < forvantat):
            spann = tal[-1] if len(tal) > 1 else nr
            fortsatter = nr is not None and nasta is not None and nr < nasta <= (spann or nr) + 3
            if nr is None or nr < forvantat or nr > forvantat + 30 or not fortsatter:
                nr = forvantat
        if nr is None:
            continue
        sidor = [int(t) for t in re.findall(r"\d+", r.get("sidor") or "")]
        # "142—143" är brev som trycks tillsammans; ett större spann är ett avskriftsfel (nummer och sida)
        # Ett större spann godtas när nästa post fortsätter efter det ("154—165", sedan 166)
        till = tal[-1] if len(tal) > 1 and tal[-1] > nr else None
        if till and till > nr + 3 and not (nasta is not None and till < nasta <= till + 3):
            till = None
        resultat.append({"nr": nr, "nr_till": till,
                         "datering": (r.get("datering") or "").strip(" ."), "rubrik": (r.get("rubrik") or "").strip(),
                         "sida": sidor[0] if sidor else None, "nr_tryckt": r.get("nr")})
        forvantat = (resultat[-1]["nr_till"] or nr) + 1
    # Samma nummer igen: tillägg med egen numrering eller "64 a, 64 b"; skiljs med en bokstav
    sedda: Counter = Counter()
    for p in resultat:
        sedda[p["nr"]] += 1
        p["suffix"] = "" if sedda[p["nr"]] == 1 else chr(ord("a") + sedda[p["nr"]] - 1)
    return resultat


def las_text(fil: Path) -> tuple[list[tuple[int, str]], dict[int, list[str]], int]:
    """Bandets brödrader (fil, rad), fotnoter per fil och skillnaden mellan fil och tryckt sida."""
    rader, noter, skillnad = [], {}, Counter()
    with zipfile.ZipFile(fil) as z:
        for namn in sorted(z.namelist()):
            filnr = int(re.match(r"\d+", namn)[0])
            text = z.read(namn).decode("utf-8", "replace")
            if (s := _tryckt_sida(text)) is not None:
                skillnad[filnr - s] += 1
            kropp, fot, brevsida = _sida(text)
            if not brevsida:
                continue
            noter[filnr] = fot
            rader += [(filnr, r) for r in kropp]
    return rader, noter, skillnad.most_common(1)[0][0] if skillnad else 0


def _ar(text: str) -> set[str]:
    """Årtalen i texten, med de former OCR:ns sifferförväxlingar ger (1340 läst som 1840)."""
    ar = set(re.findall(r"1[0-8]\d\d|\b\d{3}\b", text))
    return {v for a in ar for v in _varianter(int(a))}


def _forenkla(text: str) -> str:
    """Ortnamn för jämförelse: gemener, utan accenter och med OCR:ns vanliga förväxlingar utjämnade."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    for a, b in (("þ", "th"), ("ð", "d"), ("æ", "ae"), ("ö", "o"), ("w", "v"), ("y", "i"), ("ll", "l"), ("hh", "h")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z]", "", text)


def _ortnyckel(rubrik: str) -> str | None:
    """Ortnamnet i en máldagerubrik: "Máldagi Hróarsholtskirkju í Flóa" → hróarsholt,
    "Bólstaðahlíðarmáldagi" → bólstaðahlíðar."""
    m = re.match(r"(?:Máldag[ia]r?\s+)?(\S+?)(?:s?kirkju|s?kirkna|s?kirkja|máldagi|máldagar)\b", rubrik, re.I)
    return _forenkla(m[1]) if m and len(_forenkla(m[1])) >= 3 else None


def _ortrad(rad: str, nyckel: str | None) -> bool:
    """En underrubrik i en máldagesamling: romersk siffra och ortnamn ("LXXXIX. Hroarshollt.") eller en
    kort rad som börjar med ortnamnet."""
    if not nyckel:
        return False
    m = re.match(r"\s*(?:[IVXLCivxlc]{1,8}\s*[.,]\s*)?([^\s.,(]{3,})", rad)
    if not m or len(rad.strip()) > 60:
        return False
    ord_ = _forenkla(m[1])
    return SequenceMatcher(None, ord_[:len(nyckel) + 2], nyckel).ratio() >= 0.75


def _dag_manad(text: str) -> tuple[int, int] | None:
    """Dag och månad i en datering: "27. júní", "18- Januar", "4. Oktohcr"."""
    m = re.search(r"\b(\d{1,2})\s*[.,-]?\s*([A-Za-zÁÉÍÓÚáéíóúý]{3})", text)
    if not m:
        return None
    for namn, nr in MANADER_DI.items():
        if m[2].lower().startswith(namn[:3]) or m[2].lower()[:3] == namn[:3]:
            return int(m[1]), nr
    return None


def _rubrikrad(rad: str, post: dict) -> int:
    """Hur väl en rad (med eventuell följande rad) liknar postens rubrikrad i texten.

    Numret (med OCR:ns sifferförväxlingar), dateringens år, dag och månad, och tabbarna räknas.
    Ett tydligt läst annat nummer eller en annan dag talar emot.
    """
    poang = 0
    forsta = rad.strip().split()[0].rstrip(".,") if rad.strip() else ""
    if forsta in _varianter(post["nr"]):
        poang += 2
    elif forsta.isdigit() and len(forsta) == len(str(post["nr"])):
        # Ett tydligt läst nummer som inte är postens: rubriken för ett annat brev med samma årtal
        poang -= 3
    if _ar(rad) & _ar(post["datering"]):
        poang += 2
    i_rad, i_post = _dag_manad(rad), _dag_manad(post["datering"])
    if i_rad and i_post:
        poang += 2 if i_rad == i_post else (1 if i_rad[1] == i_post[1] else -1)
    if "\t" in rad:
        poang += 1
    if _ortrad(rad, _ortnyckel(post["rubrik"])):
        poang += 4
    if len(rad) > 110:
        poang -= 2
    return poang


def _nummer_stammer(rad: str, post: dict) -> bool:
    forsta = rad.strip().split()[0].rstrip(".,") if rad.strip() else ""
    return forsta in _varianter(post["nr"])


def dela_band(fil: Path) -> list[dict]:
    """Bandets brev med förteckningens uppgifter och texten ur OCR."""
    band = _band(fil)
    poster = las_forteckning(band)
    rader, noter, forskjutning = las_text(fil)
    per_fil: dict[int, list[int]] = {}
    for i, (f, _) in enumerate(rader):
        per_fil.setdefault(f, []).append(i)
    # En rubrik kan stå på två rader: numret ensamt och dateringen på nästa ("436." / "21. November 1429.")
    jamfor = [r if not (re.fullmatch(r"\s*\S{1,4}\s*[.,]\s*", r) and i + 1 < len(rader))
              else f"{r.strip()}\t{rader[i + 1][1].strip()}" for i, (_, r) in enumerate(rader)]
    def godtagbar(i: int, p: dict, nasta_sida: bool) -> bool:
        """En rad kan vara postens rubrik: årtalet, ortnamnet eller exakt nummer med rätt dag och månad
        stämmer, poängen räcker, och på nästa sida krävs att numret eller ortnamnet stämmer."""
        rad, nyckel = jamfor[i], _ortnyckel(p["rubrik"])
        forsta = rad.strip().split()[0].rstrip(".,") if rad.strip() else ""
        dag = _dag_manad(rad)
        stod = (_ar(rad) & _ar(p["datering"]) or _ortrad(rad, nyckel)
                or (forsta == str(p["nr"]) and dag is not None and dag == _dag_manad(p["datering"])))
        return bool(stod) and _rubrikrad(rad, p) >= 3 and (not nasta_sida or _nummer_stammer(rad, p) or _ortrad(rad, nyckel))

    borjan, senast = [], -1
    for p in poster:
        if p["sida"] is None:
            borjan.append(None)
            p["grans_osaker"] = True
            continue
        fil_nr = p["sida"] + forskjutning
        basta = None
        # Rubrikraden ska ha förteckningens årtal. Den angivna sidan går före nästa, och på nästa
        # sida godtas bara en rad där numret stämmer, så att sökningen inte hoppar förbi senare brev
        for f in (fil_nr, fil_nr + 1):
            kandidater = [i for i in per_fil.get(f, []) if i > senast and godtagbar(i, p, f != fil_nr)]
            if kandidater:
                basta = max(kandidater, key=lambda i: (_rubrikrad(jamfor[i], p), -i))
                break
        # Utan rubrikrad dras ingen gräns: texten stannar hos föregående brev, som då får flera brev
        p["grans_osaker"] = basta is None
        borjan.append(basta)
        if basta is not None:
            senast = basta
    # En rad som exakt bär ett annat brevs nummer hör till det brevet (655 tog inte 654:s plats)
    nummer_till_post = {str(p["nr"]): k for k, p in enumerate(poster) if not p["suffix"]}
    for k, i in enumerate(borjan):
        if i is None:
            continue
        forsta = jamfor[i].strip().split()[0].rstrip(".,") if jamfor[i].strip() else ""
        agare = nummer_till_post.get(forsta)
        if agare is not None and agare != k and borjan[agare] is None and godtagbar(i, poster[agare], False):
            borjan[k], borjan[agare] = None, i
    # Andra genomgången: brev utan rubrikrad söks mellan grannarnas rubriker
    for k, p in enumerate(poster):
        if borjan[k] is not None or p["sida"] is None:
            continue
        fore = max((b for b in borjan[:k] if b is not None), default=-1)
        efter = min((b for b in borjan[k + 1:] if b is not None), default=len(rader))
        fil_nr = p["sida"] + forskjutning
        kandidater = [i for f in (fil_nr, fil_nr + 1) for i in per_fil.get(f, [])
                      if fore < i < efter and godtagbar(i, p, f != fil_nr)]
        if kandidater:
            borjan[k] = max(kandidater, key=lambda i: (_rubrikrad(jamfor[i], p), -i))
    for p, b in zip(poster, borjan):
        p["grans_osaker"] = b is None
    brev = []
    for k, (p, start) in enumerate(zip(poster, borjan)):
        foljande = next((j for j in range(k + 1, len(borjan)) if borjan[j] is not None), len(borjan))
        slut = borjan[foljande] if foljande < len(borjan) else len(rader)
        p["omfattar"] = [f"{q['nr']}{q['suffix']}" for q in poster[k + 1:foljande]] if start is not None else []
        del_ = rader[start:slut] if start is not None else []
        filer = sorted({f for f, _ in del_})
        # Tabbarna skiljer nummer, datering och ort och får stå kvar
        brev.append({**p, "band": band, "rubrikrad": re.sub(r"[ \r]+", " ", del_[0][1]).strip() if del_ and start is not None else "",
                     "text": _sammanfoga([r for _, r in del_[1:]]),
                     "noter": _sammanfoga([n for f in filer for n in noter.get(f, [])]),
                     "fil": filer[0] if filer else (p["sida"] + forskjutning if p["sida"] else None)})
    return brev


def tolka_datum(text: str) -> tuple:
    """Isländska och äldre danska månadsnamn som importera_dn.datum förstår."""
    ut = text
    for namn, nr in MANADER_DI.items():
        ut = re.sub(rf"\b{namn}\w*\.?", next(k for k, v in MANADER.items() if v == nr).capitalize() + ".", ut, flags=re.I)
    # "1467, 13. Janúar" → "13. Jan. 1467". I ett intervall över årsskiftet hör
    # det inledande året till början: "1538, 26. Sept.—2. Marts 1540" →
    # "26. Sept. 1538—2. Marts 1540"
    if (m := re.match(r"\[?(\d{3,4})\]?,\s*(.+)$", ut)):
        ar, rest = m[1], m[2]
        delar = re.split(r"\s*[—–-]\s*", rest, maxsplit=1)
        if len(delar) == 2 and delar[0] and re.search(r"\b\d{3,4}\b", delar[1]) \
                and not re.search(r"\b\d{3,4}\b", delar[0]):
            ut = f"{delar[0]} {ar}—{delar[1]}"
        else:
            ut = f"{rest} {ar}"
    edtf, fran, till, anm = datum(ut)
    # Två år som inte bildar ett intervall framåt ("872 [868?]", "1394, 1399 og
    # 1406") blir ett intervall som omfattar båda, så att början aldrig ligger
    # efter slutet
    if fran is not None and till is not None and fran > till:
        forst, sist = till // 10000, fran // 10000
        osaker = "?" if edtf and edtf.endswith("?") else ""
        edtf, fran, till = f"{forst:04d}/{sist:04d}{osaker}", forst * 10000 + 101, sist * 10000 + 1231
    return edtf, fran, till, anm


def _ort(rubrikrad: str) -> str | None:
    """Orten i rubrikraden: den sista delen efter dateringen, inledd med á, í eller liknande
    ("22.	[Juni 1096].	á alþingi.", "9- Mai 1421. á Vatni enu syðra.", "1436 Westminster.")."""
    rad = rubrikrad.strip(" .,;[]")
    if (m := re.search(r"(?:^|[\s\t.,\]])((?:á|í|i|ú|a|at|að)\s+[^\t\[\]]{2,60})$", rad)):
        ort = m[1]
    else:
        delar = [d.strip(" .,[]") for d in re.split(r"\t|\s—\s|\.\s+(?=[A-ZÁÉÍÓÚÞÆÖ])", rad) if d.strip(" .,[]")]
        ort = delar[-1] if len(delar) >= 2 else None
    if not ort or re.search(r"\d{3}", ort) or not re.search(r"[a-záéíóúýþæöð]{3}", ort, re.I):
        return None
    return re.sub(r"[\s.,;:\-*'\]\[]+$", "", ort).strip() or None


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--prov", action="store_true")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    alla = []
    for fil in sorted(KATALOG.glob("*.zip"), key=_band):
        brev = dela_band(fil)
        log.info("band %2d: %4d brev, rubrikrad hittad för %d, %d utan text", _band(fil), len(brev),
                 sum(not b.get("grans_osaker", True) for b in brev), sum(not b["text"] for b in brev))
        alla += brev
    if argument.prov:
        return
    db.initiera_schema()
    sprakbedomningar = las_sprak(SPRAKFIL, MODELLFIL)
    verk, passager = [], []
    for b in alla:
        nr = f"{b['nr']}{b['suffix']}"
        verk_id = f"di:{b['band']}:{nr}"
        adress = f"DI {b['band']} nr {nr}" + (f"–{b['nr_till']}" if b["nr_till"] else "")
        edtf, fran, till, anm = tolka_datum(b["datering"])
        # Ett läsbart nummer i rubrikraden som inte är förteckningens (och inte en sifferförväxling)
        # tyder på att texten hör till ett annat brev; den gränsen räknas då som osäker
        forsta = (b["rubrikrad"].split() or [""])[0].rstrip(".,")
        avviker = forsta.isdigit() and forsta not in _varianter(b["nr"])
        if avviker:
            b["grans_osaker"] = True
        bedomning = sprakbedomningar.get(verk_id)
        brevsprak_lista = bedomning["sprak"].split("-") if bedomning and bedomning["sprak"] else []
        brevsprak = brevsprak_lista[0] if len(brevsprak_lista) == 1 else None
        verk.append((verk_id, "di", adress, None, "diplom", db.sprakvarde(brevsprak_lista), _ort(b["rubrikrad"]), edtf, fran, till,
                     anm or (b["datering"] if not edtf else None),
                     BILD.format(band=b["band"], sida=b["fil"]) if b["fil"] is not None else KALLA_URL,
                     json.dumps({"band": b["band"], "nr": b["nr"], "nr_till": b["nr_till"], "sida": b["sida"],
                                 "fil": b["fil"], "datering": b["datering"], "rubrikrad": b["rubrikrad"],
                                 "grans_osaker": b.get("grans_osaker", True),
                                 "nr_i_texten": forsta if avviker else None,
                                 "texten_omfattar_aven": b.get("omfattar") or None,
                                 "sprakbedomning": bedomning}, ensure_ascii=False)))
        if b["rubrik"]:
            passager.append((f"{verk_id}:regest", verk_id, None, "regest", adress, 0, "isl", b["rubrik"]))
        if b["text"]:
            passager.append((f"{verk_id}:originaltext", verk_id, None, "originaltext", adress, 1, brevsprak, b["text"]))
        if b["noter"]:
            passager.append((f"{verk_id}:anmarkning", verk_id, None, "anmarkning", f"{adress}, noter", 20, "isl", b["noter"]))
    conn = db._hamta_db()
    try:
        db.upsert(conn, "kallsamling", ["id", "namn", "utgivare", "url", "licens", "version", "importerad"], ["id"],
                  [("di", "Diplomatarium Islandicum", "Hið íslenzka bókmenntafélag; digitalt: Landsbókasafn Íslands (bækur.is)",
                    KALLA_URL, "Inga förbehåll angivna vid materialet", "OCR-text och avskriven innehållsförteckning",
                    datetime.now(timezone.utc).isoformat(timespec="seconds"))])
        db.upsert(conn, "verk", ["id", "kallsamling_id", "titel", "upphov", "genre", "sprak", "utfardandeort", "datering_edtf",
                                 "datering_fran", "datering_till", "datering_anm", "extern_url", "extra"], ["id"], verk)
        db.upsert(conn, "passage", ["id", "verk_id", "utgava_id", "typ", "adress", "ordning", "sprak", "text"], ["id"], passager)
    finally:
        conn.close()
    log.info("%d brev, %d passager", len(verk), len(passager))


if __name__ == "__main__":
    main()

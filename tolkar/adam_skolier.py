"""
Tolk för skolierna till Adam av Bremens Gesta Hammaburgensis ecclesiae
pontificum.

openMGH-texten av Schmeidlers utgåva (1917) innehåller bara huvudtexten.
Skolierna står i utgåvan under huvudtexten och hämtas här ur Internet
Archives OCR av samma utgåva (adamvonbremenham00adam). Ett skolion inleds
'Schol. 138 (134).' med Schmeidlers nummer och Lappenbergs inom parentes
och slutar där variantapparaten börjar. Ankaret i huvudtextens marginal
('… civitate Schol. 138.') visar vilket kapitel skoliet hör till.

Skolierna läggs som egna passager under Adams befintliga verk, med typen
'skolion', så att de kan bedömas för sig: en del är Adams egna tillägg,
andra senare avskrivares.

Användning:
    python -m tolkar.adam_skolier
    python -m tolkar.adam_skolier --torr
"""

import argparse
import difflib
import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, ladda

log = logging.getLogger("tolkar.adam_skolier")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "adam_skolier"
OCR_URL = "https://archive.org/download/adamvonbremenham00adam/adamvonbremenham00adam_djvu.txt"
VERK_ID = "verk:adam_av_bremen"
UTGAVA_ID = "utgava:adam_av_bremen:schmeidler1917_skolier"
UTGAVA_TRANSKRIPTION = "utgava:adam_av_bremen:schmeidler1917_skolier_transkription"
# Transkriptioner från sidbild av skolier som är ofullständiga eller saknas i OCR:en
TRANSKRIPTIONER = Path(__file__).parent.parent / "data" / "transkriptioner" / "adam_skolier_schmeidler.json"

# Schmeidler numrerar skolierna 1–158; högre nummer i OCR:en är felläsningar
STORSTA_NR = 158

# Bokgränser i utgåvan (MGH-sidor), samma som i openMGH-texten
BOCKER = [("I", 5, 60), ("II", 61, 141), ("III", 142, 226), ("IV", 227, 280)]

# Enstaka OCR-fel som inte går att rätta med regler, per skolion: (fel, rätt)
OCR_RATTELSER = {152: [("remotisjsima", "remotis]sima")]}

# Rubriker som anger flera Lappenbergnummer ('Schol. 137 (132/33).'); i
# numret som tolkas ut står bara det första
LAPPENBERG_RUBRIK = {137: "132–133"}

# Textkritiska upplysningar ur apparaten som påverkar hur skoliet ska läsas
TEXTKRITIK = {145: "i B 3a.a' och C 2 inleds skoliet med 'Eadem — altissimas nives' ur huvudtexten"}

ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}

# Ett skolion börjar med 'Schol. N (M).'; Lappenbergs nummer saknas för de
# skolier Schmeidler lagt till. OCR:en läser ibland Schol som Schol, eller SchoL,
# och sätter tecken före punkten ('108 (107)^.')
START = re.compile(
    r"S\s?c?h[o0][lI1L]\s?[.,]?\s+(\d{1,3}|[QO]{2})\s*\.?\s*(?:[(\[{]\s*(\d{1,3})(?:/\d{1,3})?\s*[)\]}])?"
    r"\s*[\^*'\"]*\s*(?:\.|,(?=\s+[A-ZÆ\[(«]))\s+(\S.*)$")
# Ankaret står sist på en rad i huvudtexten; radens text används för att hitta kapitlet
ANKARE = re.compile(r"(\S.*?)\s*\bS\s?c?h[o0][lI1L]\s?[.,]?\s*(\d{1,3})\s*\.\s*$")
APPARAT = re.compile(r"^\s*(?:\d{1,2}\s+)?(?:[a-z]{1,2}\)|\*{1,2}\)|\d{1,2}\)|S\s?c?hol\.?\s*\d+\s*:|\d{1,3}\s*:\s*[a-z]\))")
# Apparatens tyska termer; en rad med dem hör aldrig till ett skolion
APPARATORD = re.compile(r"\b(?:fehlt|folgt|steht|getilgt|nachgetragen|Hand|Hs\.|Zeile)\b"
                        r"|(?:^|\s)[a-z]\)\s")   # apparatets markörer a) b) c) mitt i en rad
SIDHUVUD = re.compile(r"^\s*(\d{1,3})\s+[A-Z][A-Z .,]{6,}$|^\s*[A-Z][A-Z .,]{6,}\s+(\d{1,3})\s*$")
KAPITEL = re.compile(r"^\s*(?:\d{1,2}\s+)?([IVXLC]+)[\s*^°'\"]{0,3}\.\s+\S")


@dataclass
class Skolion:
    nr: int
    lappenberg: int | None
    sida: int | None
    bok: str | None
    kapitel: int | None
    text: str
    avbrutet: bool


def romersk(tal: str) -> int:
    varden = [ROMERSKA[t] for t in tal]
    return sum(-v if i + 1 < len(varden) and v < varden[i + 1] else v for i, v in enumerate(varden))


def hamta() -> Path:
    fil = KATALOG / "schmeidler1917_djvu.txt"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        log.info("Hämtar %s", OCR_URL)
        urllib.request.urlretrieve(OCR_URL, fil)
    return fil


def rensa(rader: list[str]) -> str:
    """
    Skoliets rader som löptext: radnummer i marginalen, utgåvans
    hänvisningstecken till apparaten (* ^ ° ®) och avstavningar tas bort.
    """
    text = "\n".join(re.sub(r"\s{2,}\d{1,2}\s*$", "", re.sub(r"^\s*\d{1,2}\s{2,}", "", r)) for r in rader)
    text = re.sub(r"(\w)-\n(?=\w)", r"\1", text)
    text = re.sub(r"[*^°®%]+", "", text)
    text = re.sub(r"(?<=\w)['\"]+(?=[\s;,.:])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _utan_sigelsvans(text)


def _utan_sigelsvans(text: str) -> str:
    """
    Tar bort handskriftssigler som OCR:en läst in efter sista meningen
    ('votum populi« M 2. 3. 5 3-'. 4. 0 2 .'): minst tre korta grupper av
    siffror och enstaka versaler i slutet. En avslutande parentes med
    sigler ('(A2. B. C2)') anger vilka handskrifter som har skoliet och behålls.
    """
    # Skräp efter en avslutande sigelparentes ('Rodulphus (B--'A). i5')
    if m := re.match(r"^(.*\([^()]{1,25}\))\W*\w{0,3}\W*$", text):
        return m.group(1)
    if re.search(r"\([^()]*\)\W*$", text):
        return text
    delar = text.split()

    def sigel(d: str) -> bool:
        tecken = [c for c in d if not c.isspace()]
        return bool(re.fullmatch(r"[A-Z]\d?\.?|[«»]", d)) or (
            bool(tecken) and sum(c.isalpha() for c in tecken) / len(tecken) <= 0.5)

    antal = 0
    while antal < len(delar) and sigel(delar[-1 - antal]):
        antal += 1
    if antal >= 3:
        text = " ".join(delar[:-antal]).rstrip("«» ")
    return text


def bok_for_sida(sida: int | None) -> str | None:
    return next((b for b, fran, till in BOCKER if sida and fran <= sida <= till), None)


def _kapitelrubrik(rad: str) -> bool:
    """Huvudtextens kapitelrubrik, också när OCR:en tappat punkten ('XXX Adalwardus igitur')."""
    return bool(KAPITEL.match(rad) or re.match(r"^\s*(?:\d{1,2}\s+)?[IVXLC]{2,}[\s.*^]+[A-Z]", rad))


def _lopande_text(rad: str) -> bool:
    """True för en rad latinsk löptext; apparatens tyska termer och siglerader är det inte."""
    s = rad.strip()
    if re.search(r"\b(?:fehlt|folgt|steht|Hs\.|vgl\.|Vgl\.)", s):
        return False
    tecken = [c for c in s if not c.isspace()]
    return bool(tecken) and sum(c.isalpha() for c in tecken) / len(tecken) > 0.85


def _avslutat(text: str) -> bool:
    # En sigelparentes i slutet avslutar skoliet, också när OCR:en tappat
    # slutparentesen ('… theatri (A2. S. B. C')
    return re.search(r"[.!?»)\]]\s*$|\((?:[A-Z]\d?[\s.,;'\-^]*)+\w?\s*$|\([^()]{1,25}\)\W*\w{0,3}\W*$",
                     text) is not None


def _sidor(rader: list[str]) -> list[tuple[int | None, list[str]]]:
    """
    Texten uppdelad i (sidnummer, rader) vid utgåvans sidhuvuden. Där OCR:en
    missat ett sidhuvud fylls numret i från närmaste kända sidor, eftersom
    utgåvan är paginerad utan luckor.
    """
    sidor: list[tuple[int | None, list[str]]] = [(None, [])]
    for rad in rader:
        if m := SIDHUVUD.match(rad):
            sidor.append((int(m.group(1) or m.group(2)), []))
        else:
            sidor[-1][1].append(rad)
    kanda = [(i, nr) for i, (nr, _) in enumerate(sidor) if nr]
    for (i, a), (j, b) in zip(kanda, kanda[1:]):
        if b - a == j - i:
            for k in range(i + 1, j):
                sidor[k] = (a + (k - i), sidor[k][1])
    return sidor


def _block(rader: list[str]) -> list[list[str]]:
    """Raderna i block, åtskilda av tomma rader."""
    block, aktuellt = [], []
    for rad in rader:
        if rad.strip():
            aktuellt.append(rad)
        elif aktuellt:
            block.append(aktuellt)
            aktuellt = []
    if aktuellt:
        block.append(aktuellt)
    return block


def _huvudtextandel(text: str, sida: int | None) -> float:
    """Andel av textens ord (minst fem bokstäver) som finns i openMGH:s huvudtext kring sidan."""
    ord_ = {w.lower() for w in re.findall(r"[A-Za-z]{5,}", text)}
    if not ord_ or sida is None:
        return 0.0
    huvudtext = set().union(*(k[4] for k in _adams_kapitel() if k[2] - 1 <= sida <= k[3] + 1))
    return len(ord_ & huvudtext) / len(ord_)


def _kandidatpoang(text: str, sida: int | None) -> float:
    """
    Lägre är bättre. En kandidat ska vara latinsk skolietext: noter och
    sidhänvisningar ('2) Auch dies Statut …', 'S. 162.') delar inga ord med
    huvudtexten men är inte heller skolier och rangordnas därför sist.
    """
    tyska = re.findall(r"\b(?:und|die|der|das|des|ist|im|auch|vgl|bei|von|mit|nur|wie)\b", text, re.I)
    ar_not = re.match(r"^\s*(?:\d{1,2}\)|S\.\s*\d)", text) or len(tyska) >= 2 or APPARATORD.search(text)
    if len(text) < 25 or ar_not:
        return 2.0
    return _huvudtextandel(text, sida)


def _ar_huvudtext(block: list[str], sida: int | None) -> bool:
    """
    True om blocket är huvudtext: en kapitelrubrik, ett ankare eller ord som
    till största delen återfinns i openMGH-texten för samma sida. Skolierna
    står inte i openMGH-texten, så ett skolieblock har låg överlappning.
    """
    if any(_kapitelrubrik(r) or ANKARE.match(r) for r in block):
        return True
    ord_ = {w.lower() for r in block for w in re.findall(r"[A-Za-z]{5,}", r)}
    if not ord_ or sida is None:
        return False
    huvudtext = set().union(*(k[4] for k in _adams_kapitel() if k[2] - 1 <= sida <= k[3] + 1))
    return len(ord_ & huvudtext) / len(ord_) > 0.6


def tolka(text: str) -> list[Skolion]:
    """
    Skolierna sida för sida. Ett skolion löper från sin rubrik till nästa
    skolion, apparaten, huvudtextens nästa kapitelrubrik eller en tom rad
    efter avslutad mening som följs av något annat än löptext. Ett skolion
    som inte slutar med skiljetecken fortsätter på nästa sida: fortsättningen
    är det sista blocket före nästa skolion eller apparaten som inte är
    huvudtext enligt jämförelsen med openMGH.
    """
    rader = text.split("\n")
    # Inledningen hänvisar till skolierna ('Schol. 120, S. 240'); texten börjar vid prefatio
    borjan = next(i for i, r in enumerate(rader) if "PRAEFATIO" in r and "M." not in r[:3])

    ankare: dict[int, tuple[int | None, str]] = {}   # nr → (sida, radens text)
    skolier: dict[int, dict] = {}
    oppet: dict | None = None

    for sida, sidrader in _sidor(rader[borjan:]):
        starter: list[tuple[int, int, re.Match]] = []
        apparat = len(sidrader)
        for i, rad in enumerate(sidrader):
            if APPARAT.match(rad):
                apparat = min(apparat, i)
            if m := START.search(rad):
                nr = 66 if m.group(1) in ("QQ", "OO") else int(m.group(1))
                # Radnummer i marginalen före rubriken räknas inte som text; en start
                # mitt på en rad godtas bara med Lappenbergs nummer, så att
                # marginalens ankare inte förväxlas med rubriker
                fore = re.sub(r"^\d{1,2}$", "", rad[:m.start()].strip())
                if nr <= STORSTA_NR and (not fore or m.group(2)):
                    starter.append((i, nr, m))
        slut_huvudtext = min([apparat] + [i for i, _, _ in starter])

        for rad in sidrader[:slut_huvudtext]:
            if m := ANKARE.match(rad):
                ankare.setdefault(int(m.group(2)), (sida, m.group(1)))

        if oppet:
            for kandidat in reversed(_block(sidrader[:slut_huvudtext])[1:]):
                if (len(kandidat) <= 20 and not _ar_huvudtext(kandidat, sida)
                        and not any(APPARATORD.search(r) for r in kandidat)):
                    oppet["rader"] += kandidat
                    oppet["fortsatt"] = True
                    break
            oppet = None

        senaste = None
        for k, (i, nr, m) in enumerate(starter):
            slut = min([apparat if apparat > i else len(sidrader)] + [j for j, _, _ in starter[k + 1:]])
            innehall = [m.group(3)]
            tom_rad = False
            for rad in sidrader[i + 1:slut]:
                if _kapitelrubrik(rad) or APPARATORD.search(rad):
                    break
                if not rad.strip():
                    tom_rad = True
                    continue
                if tom_rad and _avslutat(rensa(innehall)) and not _lopande_text(rad):
                    break
                tom_rad = False
                innehall.append(rad)
            # Ankaret i marginalen hamnar ibland först på raden i OCR:en och ser
            # då ut som en rubrik; alla kandidater sparas och den som inte är
            # huvudtext väljs till sist
            senaste = {"nr": nr, "lappenberg": int(m.group(2)) if m.group(2) else None, "sida": sida,
                       "rader": innehall, "fortsatt": False}
            skolier.setdefault(nr, []).append(senaste)
        if senaste and not _avslutat(rensa(senaste["rader"])):
            oppet = senaste

    ut = []
    for nr in sorted(skolier):
        s = min(skolier[nr], key=lambda k: _kandidatpoang(rensa(k["rader"]), k["sida"]))
        # En kandidat som är huvudtext är ankaret i vänstermarginalen ('Schol. 147. quidam
        # Iohannes …') och visar vilket kapitel skoliet hör till
        for k in skolier[nr]:
            if nr not in ankare and _huvudtextandel(rensa(k["rader"]), k["sida"]) > 0.6:
                ankare[nr] = (k["sida"], k["rader"][0])
        t = rensa(s["rader"])
        for fel, ratt in OCR_RATTELSER.get(nr, []):
            t = t.replace(fel, ratt)
        b, kap = kapitel_for(ankare.get(nr), s["sida"])
        # Ett skolion vars fortsättning hittats på nästa sida är komplett, även
        # om slutpunkten försvunnit med siglerna efter den
        ut.append(Skolion(nr, s["lappenberg"], s["sida"], b, kap, t, not _avslutat(t) and not s["fortsatt"]))
    return ut


_KAPITEL_CACHE: list[tuple[str, int, int, int, set[str]]] | None = None


def _adams_kapitel() -> list[tuple[str, int, int, int, set[str]]]:
    """Adams kapitel ur openMGH-texten som (bok, kapitel, första sida, sista sida, ord)."""
    global _KAPITEL_CACHE
    if _KAPITEL_CACHE is None:
        from tolkar.openmgh import VERK, tolka_verk
        konf = next(k for k in VERK if k.verk_id == VERK_ID)
        _, _, passager = tolka_verk(konf)
        _KAPITEL_CACHE = []
        for p in passager:
            m = re.match(r"bok (\w+), kap\. (\d+) \(MGH s\. (\d+)(?:–(\d+))?\)", p.adress)
            if m:
                ord_ = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", p.text)}
                _KAPITEL_CACHE.append((m.group(1), int(m.group(2)), int(m.group(3)),
                                       int(m.group(4) or m.group(3)), ord_))
    return _KAPITEL_CACHE


def kapitel_for(ankare: tuple[int | None, str] | None, sida: int | None) -> tuple[str | None, int | None]:
    """
    Kapitlet ett skolion hör till. Med ankare: det kapitel nära ankarets
    sida som innehåller flest av ankarradens ord. Utan ankare: kapitlet
    som täcker skoliets sida (det första, om flera gör det).
    """
    kapitel = _adams_kapitel()
    if ankare:
        a_sida, rad = ankare
        ord_ = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", rad)}
        nara = [k for k in kapitel if a_sida is None or k[2] - 2 <= a_sida <= k[3] + 2]
        if ord_ and nara:
            basta = max(nara, key=lambda k: (len(ord_ & k[4]), -abs((a_sida or k[2]) - k[2])))
            if ord_ & basta[4]:
                return basta[0], basta[1]
    if sida:
        tackande = [k for k in kapitel if k[2] <= sida <= k[3]]
        if tackande:
            return tackande[0][0], tackande[0][1]
    return bok_for_sida(sida), None


def _jamforform(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower().replace("j", "i").replace("v", "u"))


def las_transkriptioner(ocr: dict[int, Skolion]) -> dict[int, dict]:
    """
    Godkända transkriptioner från sidbild, per skolienummer.

    En transkription godtas om dess början stämmer med OCR-textens början
    (likhet minst 0,5 efter normalisering av stavning och skiljetecken), så
    att en transkription av fel skolion eller en tillskriven text fångas.
    En transkription godtas också när OCR-texten själv är huvudtext (ankaret
    i marginalen togs för skoliets rubrik) och transkriptionen inte är det.
    Skolier som saknas i OCR:en har inget att jämföra med och godtas.
    """
    if not TRANSKRIPTIONER.exists():
        return {}
    godkanda: dict[int, dict] = {}
    for post in json.loads(TRANSKRIPTIONER.read_text(encoding="utf-8")):
        nr, text = post["nr"], (post.get("text") or "").strip()
        if not text:
            continue
        o = ocr.get(nr)
        if o:
            a, b = _jamforform(text)[:80], _jamforform(o.text)[:80]
            likhet = difflib.SequenceMatcher(None, a, b).ratio()
            # OCR-texten kan själv vara fel: huvudtext vid ankaret i stället för skoliet.
            # Då godtas en transkription som inte är huvudtext.
            # OCR-text som innehåller ett annat skolions rubrik är också felfångad
            annan_rubrik = any(int(m.group(1)) != nr for m in re.finditer(r"Schol\.\s*(\d{1,3})\s*\(", o.text))
            ocr_ar_huvudtext = _huvudtextandel(o.text, o.sida) > 0.6 or annan_rubrik
            transkription_ar_huvudtext = _huvudtextandel(text, o.sida) > 0.6
            if likhet < 0.5 and not (ocr_ar_huvudtext and not transkription_ar_huvudtext):
                log.warning("Transkriptionen av skolion %d underkänd: början stämmer inte med OCR (%.2f)",
                            nr, likhet)
                continue
        godkanda[nr] = post
    return godkanda


def bygg_paket() -> Kallpaket:
    skolier = tolka(hamta().read_text(encoding="utf-8"))
    ocr = {s.nr: s for s in skolier}
    transkriptioner = las_transkriptioner(ocr)
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="adam_skolier", namn="Adam av Bremen, skolierna (Schmeidler 1917, OCR ur Internet Archive)",
            utgivare="Internet Archive (skanning: University of Toronto)",
            url="https://archive.org/details/adamvonbremenham00adam",
            licens="Public domain", version="djvu.txt"),
        verk=[],
        befintliga_verk=[VERK_ID],
        utgavor=[(VERK_ID, Utgava(
            UTGAVA_ID, "Bernhard Schmeidler (utg.), Adam von Bremen, Hamburgische Kirchengeschichte, "
                       "3 uppl., Hannover/Leipzig 1917 (MGH SS rer. Germ. 2): skolierna. "
                       "OCR ur Internet Archive (adamvonbremenham00adam).", "Public domain"))],
    )
    if transkriptioner:
        paket.utgavor.append((VERK_ID, Utgava(
            UTGAVA_TRANSKRIPTION,
            "Bernhard Schmeidler (utg.), Adam von Bremen, Hamburgische Kirchengeschichte, 3 uppl., "
            "Hannover/Leipzig 1917 (MGH SS rer. Germ. 2): skolierna, transkriberade från sidbilder "
            "(Internet Archive, adamvonbremenham00adam) av språkmodell. Ogranskade.", "Public domain")))

    # Skolier som saknas i OCR men har transkriberats får sin plats ur transkriptionens sida
    for nr, post in transkriptioner.items():
        if nr not in ocr:
            sida = (post.get("sidor") or [None])[0]
            bok, kap = kapitel_for(None, sida)
            ocr[nr] = Skolion(nr, post.get("lappenberg_i_rubrik"), sida, bok, kap, "", False)

    lappenbergnr = {nr: s.lappenberg or (transkriptioner.get(nr) or {}).get("lappenberg_i_rubrik")
                    for nr, s in ocr.items()}
    for nr in sorted(ocr):
        s = ocr[nr]
        post = transkriptioner.get(nr)
        text, utgava, avbrutet = s.text, UTGAVA_ID, s.avbrutet
        anmarkning = "ofullständigt i OCR" if avbrutet else None
        if post:
            text, utgava = post["text"], UTGAVA_TRANSKRIPTION
            avbrutet = not post.get("fullstandig", False)
            anmarkning = "transkriberat från sidbild, ogranskat" + ("; ofullständigt" if avbrutet else "")
        lappenberg = LAPPENBERG_RUBRIK.get(nr) or lappenbergnr.get(nr)
        # Schmeidler delar ibland upp ett av Lappenbergs skolier i två (141 = 145 + 146)
        delat = [n for n, l in lappenbergnr.items() if l == lappenbergnr.get(nr) and n != nr]
        delar = [f"skolion {nr}" + (f" ({lappenberg} hos Lappenberg"
                                    + (f", där samma skolion som {delat[0]}" if delat else "") + ")"
                                    if lappenberg else "")]
        till = ", ".join(x for x in (f"bok {s.bok}" if s.bok else None,
                                     f"kap. {s.kapitel}" if s.kapitel else None) if x)
        sidor = (post or {}).get("sidor") or ([s.sida] if s.sida else [])
        sidtext = ("MGH s. " + "–".join(str(x) for x in (sidor[0], sidor[-1]) if x)
                   if len(sidor) > 1 and sidor[0] != sidor[-1] else (f"MGH s. {sidor[0]}" if sidor else None))
        delar.append("(" + "; ".join(x for x in (f"till {till}" if till else None, sidtext, anmarkning,
                                                 TEXTKRITIK.get(nr))
                                     if x) + ")")
        paket.passager.append((VERK_ID, Passage(
            id=f"adam_av_bremen:skolion:{nr}", typ="skolion", adress=" ".join(delar), sprak="lat",
            text=text, ordning=10000 + nr, utgava_id=utgava,
            # Sidbilden i dMGH (samma band, Schmeidler 1917) för kontroll av texten
            url=f"https://www.dmgh.de/mgh_ss_rer_germ_2/index.htm#page/({sidor[0]})/mode/1up" if sidor else None)))
    avbrutna = [s.nr for s in skolier if s.avbrutet and s.nr not in transkriptioner]
    log.info("%d skolier ur OCR, %d transkriptioner godkända; %d fortfarande ofullständiga: %s",
             len(skolier), len(transkriptioner), len(avbrutna), avbrutna)
    saknas = sorted(set(range(1, STORSTA_NR + 1)) - set(ocr))
    if saknas:
        log.warning("Skolier som inte hittades: %s", saknas)
    paket.lagg_till_maskinoversattningar(Path(__file__).parent.parent / "data" / "oversattningar" / "adam_skolier_sv.json", "latinet")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

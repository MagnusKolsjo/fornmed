"""
Tolk för landskapslagarna och de yngre lagarna ur Språkbankens
"Fornsvenska textbankens material" (Korp, CC BY 4.0).

Korpusen innehåller texten i meningar och stycken men inte lagarnas
indelning i balkar och flockar. Indelningen tas fram ur texten:
- en balk inleds av en kort rubrik med ordet balk ("Kirkiu balker") eller
  av en rubrik "Hær byrias …",
- en flock inleds av sitt nummer: ensamt (".XX.II."), före texten ("XIII.
  Ær grauit …", "13. kirkiu gard …", "(2.) Af barnum."), sist i en rubrik
  ("Vm kununx leþung..X.") eller i utgivarens hänvisning ("[KgB 1 §1.]");
  numreringen ska stiga, så att tal i löptexten inte tas för flocknummer,
- innehållsförteckningar, numrerade rader i följd efter en balkrubrik,
  samlas för sig.
Upplandslagen B saknar flocknummer och delas efter Upplandslagen A genom
att styckena paras mot A:s flockar på ordlikhet.

Adressen inleds med en hänvisning i formen "UL Äb 10" (lagens och balkens
förkortning och flocken) och anger sedan balken och flocken som de står i
handskriften. Balkförkortningarna är enhetliga inom databasen men följer
inte en enskild tryckt förteckning.

Svenska översättningar av språkmodell ligger per lag i
data/oversattningar/lagar/ (se RIKTLINJER.md där) och laddas som egna
utgåvor. Också lagar vars text finns i en annan lag eller handskrift
(Kristoffers landslags flockar ur Magnus Erikssons landslag, Upplandslagen B)
är översatta för sig, så att varje lag kan läsas och sökas som egen text.

Användning:
    python -m tolkar.fornsvenska_lagar
    python -m tolkar.fornsvenska_lagar --torr
"""

import argparse
import bz2
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import db
from normalisering import ordform
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, Vittne, ladda

log = logging.getLogger("tolkar.fornsvenska_lagar")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "sprakbanken"
OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "lagar"
KORPUSAR = {
    "fsv-aldrelagar": "https://spraakbanken.gu.se/resurser/meningsmangder/fsv-aldrelagar.xml.bz2",
    "fsv-yngrelagar": "https://spraakbanken.gu.se/resurser/meningsmangder/fsv-yngrelagar.xml.bz2",
}

# Utan ordgräns före: balken skrivs ofta ihop med sitt förled (Konungxbalker)
BALK = re.compile(r"(?:balk|bolk|kalk|bokl)\w*", re.IGNORECASE)
# Drap- och såramålsbalkarna finns i två delar, "meþ vilia" och "meþ vaþa"
BALKNAMN = re.compile(r"([\wæöþðåä]+)\s*((?:balk|bolk|kalk)\w*)(?:\s+(meþ (?:vilia|vaþa)))?", re.IGNORECASE)
# "Hær byrias tabula af köp mala balkenum": namnet är allt mellan inledningen och balk
BALKRUBRIK = re.compile(r"(?:byri\w*|begyn\w*)\s+(?:tabula\s+af\s+)?(\w+(?:\s\w+)?\s*(?:balk|bolk|bokl)\w*"
                        r"(?:\s+meþ\s+(?:vilia|vaþa))?)", re.IGNORECASE)
# Balkrubrik i löptext: "Hær byriæs kununx balkær. ok tæliæs. i hanum flokkær tolff."
BALKINLEDNING = re.compile(r"^(?:hær|her|här|hēr)\s+(?:byr+i|begyn)", re.IGNORECASE)
# Textbankens anteckningar om saknad text: "[--- Köpmålabalken ær ænnu inte inskriven ---]"
ANTECKNING = re.compile(r"^[#\s]*\[?-{2,}.*-{2,}\]?\s*$")
INNEHALLSRAD = re.compile(r"^\{?\s*\.?[IVXL]+\.?\s+(?:vm|um|af|of|æn|ok)\b", re.IGNORECASE)
# J står för I i slutet av ett tal ("..J.", "XIJ")
ROMERSKT_NR = re.compile(r"^[({\[]?\s*\.?\s*([IVXL]*[IJ]|[IVXL]+)\s*\.?\s*[)}\]]?\.?$")
ARABISKT_NR = re.compile(r"^(\d{1,3})\s*\.\s+\S")
ARABISKT_ENSAMT = re.compile(r"^(\d{1,3})\s*\.?$")
# Flocken inleds med sitt romerska nummer: "XIII. Ær grauit undir syl …" (Yngre Västgötalagen)
ROMERSKT_MED_TEXT = re.compile(r"^\.?([IVXL]+)\s*[.,]\s*\S")
# Numret inom parentes: "(2.) Af barnum." (Gutalagen)
PARENTES_NR = re.compile(r"^(?:\d{1,3}\s+)?\((\d{1,3})\.?\)\s*\S")
# Utgivarens hänvisning först i stycket: "[KgB 1 §1.]", "[2]" (Kristoffers landslag)
HANVISNING = re.compile(r"^\[(?:([A-ZÄÖÅ][A-Za-zäöåÄÖ]{0,5})\s+)?(\d{1,3})(?:\s*§\s*\d+)?\.?\]")
# Rad i en innehållsförteckning: ett nummer och en rubrik ("X Huru længi man scal sarum warþæ")
FORTECKNINGSRAD = re.compile(r"^[{\[(]?\.?([IVXL]+|\d{1,3})[.,:]?[)}\]]?\s+\S")
# Rader som inleder en förteckning: "Hær byrias tabula af …", "ok tæliæs i hanum flokkær …"
FORTECKNINGSORD = re.compile(r"tabula|flokk|flokum|flokom|tæli|tali", re.IGNORECASE)
# Flockrubrik med numret sist: "Vm kununx leþung..X." (Södermannalagen), "[Vm kyrkiu Bygning. I.]"
RUBRIK_MED_NR = re.compile(r"^(.{3,80}?)[\s.]+([IVXL]*[IJ]|[IVXL]+)\.?$")
SPARRAD = re.compile(r"^(?:\w ){3,}\w\.?$")
ROMERSKA = {"I": 1, "J": 1, "V": 5, "X": 10, "L": 50}
# Längsta språng i flocknumreringen som godtas; ett större språng är ett tal i löptexten
MAX_SPRANG = 3


def romersk(tal: str) -> int:
    varden = [ROMERSKA[t] for t in tal.upper()]
    return sum(-v if i + 1 < len(varden) and v < varden[i + 1] else v for i, v in enumerate(varden))


def _slug(text: str) -> str:
    t = text.lower()
    for a, b in (("å", "a"), ("ä", "a"), ("ö", "o"), ("æ", "ae"), ("þ", "th"), ("ð", "d")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:60]


def hamta(korpus: str) -> Path:
    fil = KATALOG / f"{korpus}.xml.bz2"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        log.info("Hämtar %s", KORPUSAR[korpus])
        urllib.request.urlretrieve(KORPUSAR[korpus], fil)
    return fil


def stycketext(stycke) -> str:
    """Styckets ord som löptext; skiljetecken sätts ihop med föregående ord."""
    ord_ = [w.text or "" for s in stycke.findall("sentence") for w in s.findall("w")]
    text = " ".join(o for o in ord_ if o)
    return re.sub(r"\s+([.,;:!?)\]}])", r"\1", re.sub(r"([(\[{])\s+", r"\1", text)).strip()


def _datering(text: str | None) -> tuple[str | None, int | None, int | None]:
    """'1280–1290' → ('1280/1290', 12800101, 12901231); ett ensamt årtal ger ett år."""
    ar = [int(a) for a in re.findall(r"\d{4}", text or "")]
    if not ar:
        return None, None, None
    forsta, sista = min(ar), max(ar)
    edtf = f"{forsta}/{sista}" if forsta != sista else str(forsta)
    return edtf, forsta * 10000 + 101, sista * 10000 + 1231


def rubrikform(text: str) -> str:
    """
    Texten utan textbankens utgivartecken: {…} är handskriftens felaktiga
    läsning och tas bort, [ ] och ( ) markerar utgivarens tillägg och
    rättelser, vars innehåll behålls.
    """
    text = re.sub(r"\{[^{}]*\}", "", text)
    text = re.sub(r"[\[\]()#]", "", text)
    return re.sub(r"\s+", " ", text).strip(" .")


def _flocknummer(text: str) -> tuple[int, bool] | None:
    """(nummer, rubriken står kvar som text) om stycket inleder en flock."""
    if re.fullmatch(r"[\s.(\[{]*[IVXLJ][IVXLJ\s.]*[)\]}]?\.?", text):
        # Ett ensamt tal med punkter eller mellanrum inuti: ".XX.II.", ".X III."
        text = re.sub(r"(?<=[IVXLJ])[\s.]+(?=[IVXLJ])", "", text)
    if m := (ROMERSKT_NR.match(text) or ARABISKT_ENSAMT.match(text)):
        return (int(m.group(1)) if m.group(1).isdigit() else romersk(m.group(1))), False
    if m := ARABISKT_NR.match(text):
        return int(m.group(1)), True
    if m := PARENTES_NR.match(text):
        return int(m.group(1)), True
    if m := ROMERSKT_MED_TEXT.match(text):
        return romersk(m.group(1)), True
    # "Vm drap af Handlösum wadhha. III. Flokker." (Hälsingelagen)
    rubrik = re.sub(r"[\s.]+flo[ck]+\w*$", "", rubrikform(text), flags=re.IGNORECASE)
    if len(rubrik) <= 90 and (m := RUBRIK_MED_NR.match(rubrik)):
        return romersk(m.group(2)), True
    return None


def _innehallsforteckning(stycken: list[str]) -> set[int]:
    """
    Stycken som hör till en innehållsförteckning: minst tre korta numrerade
    rader i följd, med numret först ("X Huru længi …") eller sist ("Vm warþ
    halþ..XII."). En kort onumrerad rad mellan två numrerade är en radbruten
    rubrik. En följd räknas bara om den står direkt efter en balkrubrik eller
    en rad om förteckningen ("tabula af …", "tæliæs flokkær …"), eftersom
    korta flocktexter i följd ("III. Sliku samu æru frælzgiuæ böter …")
    annars kan se ut som en förteckning.
    """
    def nummer(s: str) -> int | None:
        if not s or len(s) >= 160 or ROMERSKT_NR.match(s) or ARABISKT_ENSAMT.match(s) or BALK.search(s):
            return None
        if m := (FORTECKNINGSRAD.match(s) or INNEHALLSRAD.match(s)):
            tal = re.match(r"[{\[(]?\.?([IVXLJ]+|\d+)", s, re.IGNORECASE)
            return (int(tal.group(1)) if tal.group(1).isdigit() else romersk(tal.group(1))) if tal else 0
        if (m := RUBRIK_MED_NR.match(rubrikform(s))) and len(s) <= 90:
            return romersk(m.group(2))
        return None

    nr = [nummer(s) for s in stycken]
    rad = [n is not None for n in nr]
    for i in range(1, len(stycken) - 1):
        if not rad[i] and rad[i - 1] and rad[i + 1] and len(stycken[i]) < 60 \
                and not BALKINLEDNING.match(stycken[i].lstrip("[({ ")):
            rad[i] = True
    ut: set[int] = set()
    i = 0
    while i < len(stycken):
        j = i
        # Förteckningen slutar där numreringen börjar om på 1: där börjar texten
        while j < len(stycken) and rad[j] and not (j > i and nr[j] == 1):
            j += 1
        fore = [k for k in range(max(0, i - 3), i) if stycken[k]][-2:]
        efter_rubrik = i < 5 or any(BALK.search(stycken[k]) or FORTECKNINGSORD.search(stycken[k]) for k in fore)
        if j - i >= 3 and efter_rubrik:
            # Förteckningen fortsätter med korta rader, även onumrerade ("Af scarlaþi")
            while j < len(stycken) and stycken[j] and len(stycken[j]) < 60 \
                    and not BALK.search(stycken[j]) and not ROMERSKT_NR.match(stycken[j]) \
                    and not BALKINLEDNING.match(stycken[j].lstrip("[({ ")) \
                    and not ARABISKT_ENSAMT.match(stycken[j]):
                j += 1
            ut.update(range(i, j))
        i = max(j, i + 1)
    return ut


def segmentera(stycken: list[str]) -> list[tuple[str | None, int | None, str | None, str]]:
    """
    (balk, flock, balkförkortning ur utgivarens hänvisning, text) för en
    lagtext. Stycken utan urskiljbar flock får flock None; innehålls-
    förteckningen samlas för sig med balk 'innehållsförteckning'.
    """
    enheter: list[tuple[str | None, int | None, str | None, str]] = []
    balk: str | None = None
    forkortning: str | None = None
    flock: int | None = None
    flock_fore: int | None = None
    buffert: list[str] = []
    innehall: list[str] = []
    rubrik_utan_text = False

    def toma():
        nonlocal buffert, rubrik_utan_text, flock
        if buffert and rubrik_utan_text:
            # Bara en rubrik utan text: en rad i innehållsförteckningen, som
            # inte räknas i flocknumreringen
            innehall.extend(buffert)
            flock = flock_fore
        elif buffert:
            enheter.append((balk, flock, forkortning, "\n".join(buffert)))
        buffert, rubrik_utan_text = [], False

    def balknamn(text: str) -> str:
        # Rubriken kan stå helt inom {…} ("{her byrias erþa balker}"); då behålls den
        text = rubrikform(text) or re.sub(r"[{}\[\]()]", "", text).strip(" .")
        if m := BALKRUBRIK.search(text):
            namn = m.group(1)
        elif not BALK.search(text) and (m := re.search(r"(?:byr+i\w*|begyn\w*)\s+([^.]+)", text, re.IGNORECASE)):
            namn = m.group(1).strip()
        elif m := BALKNAMN.search(text):
            namn = f"{m.group(1)} {m.group(2)}" + (f" {m.group(3)}" if m.group(3) else "")
        else:
            namn = text
        if re.fullmatch(r"(?:\w{1,2} )+\w{1,3}", namn):
            # Spärrad rubrik som inte skrivits ihop ("Æ r f d e ba l k e r")
            namn = namn.replace(" ", "")
        return re.sub(r"kalk", "balk", namn, flags=re.IGNORECASE).capitalize()

    # Spärrade rubriker ("G i p t a m a l a b a l k e r.") skrivs ihop först;
    # textbankens anteckningar och inledande tecken som "# #" och "[BBB..." tas bort
    stycken = ["" if ANTECKNING.match(s) else re.sub(r"^(?:[#\s]+|\[B{3,}\.+\s*)", "", s) for s in stycken]
    stycken = [s.replace(" ", "") if SPARRAD.match(s) else s for s in stycken]
    forteckning = _innehallsforteckning(stycken)
    # En rad som nämner flera balkar är bokens förteckning över dem, ingen
    # rubrik; en rad som börjar med gemen och har fler än tre ord är en
    # radbruten mening i löptexten ("sighiæs skal i manhælghis balkenom"), om
    # den inte inleds "her byrias"
    ar_balk = [bool(s and BALKINLEDNING.match(s.lstrip("[({ ")) and len(s) <= 80
                    and not re.search(r"lagh ?bok|tabula", s, re.IGNORECASE))
               # "hær byrias uaþa mal ok sara mal" inleder en balk utan att ordet balk står där
               or bool(s and BALK.search(s) and len(BALK.findall(rubrikform(s))) == 1
                    and not s.lower().startswith(("j ", "i "))
                    and (not s[0].islower() or len(s.split()) <= 3 or BALKINLEDNING.match(s.lstrip("[({ ")))
                    and (len(s) <= 60 or (BALKINLEDNING.match(s.lstrip("[({ ")) and len(s) <= 120)))
               for s in stycken]
    balklista: list[str] = []

    for i, text in enumerate(stycken):
        if not text:
            continue
        if i in forteckning or INNEHALLSRAD.match(text):
            innehall.append(text)
            continue
        if m := HANVISNING.match(text):
            # Utgivarens hänvisning är säkrare än allt som tolkas ur texten
            toma()
            if m.group(1):
                forkortning, balk = m.group(1), m.group(1)
            flock = int(m.group(2))
            buffert.append(text)
            continue
        if ar_balk[i]:
            toma()
            # En rubrik som "Hær byriæs kyrkiu balker" inleder alltid en balk
            inledning = bool(BALKINLEDNING.match(text.lstrip("[({ ")))
            foregaende = i > 0 and ar_balk[i - 1] and not BALKINLEDNING.match(stycken[i - 1])
            foljande = i + 1 < len(stycken) and ar_balk[i + 1] and not BALKINLEDNING.match(stycken[i + 1])
            if not inledning and (foregaende or foljande):
                # Flera balkrader i följd är bokens förteckning över balkarna;
                # texten fortsätter med den första balken i förteckningen
                # Förteckningens inledning ("Attæ balkær æru i bok þæssi.") är ingen balk
                if not re.search(r"\b(?:æru|ær|tæliæs)\b|\bi bok", text, re.IGNORECASE):
                    balklista.append(balknamn(text))
                innehall.append(text)
                if not foljande:
                    balk, flock, balklista = (balklista or [balk])[0], None, []
                continue
            balk, flock, flock_fore = balknamn(text), None, None
            continue
        nr = _flocknummer(text)
        # En radbruten mening som slutar med ett tal ("… bötæ præster.II. marker
        # biskupi. ok.I.") liknar en rubrik med numret sist; den börjar med gemen
        if nr and nr[1] and text[:1].islower() and flock is not None and RUBRIK_MED_NR.match(
                re.sub(r"[\s.]+flo[ck]+\w*$", "", rubrikform(text), flags=re.IGNORECASE)) \
                and not (ARABISKT_NR.match(text) or PARENTES_NR.match(text) or ROMERSKT_MED_TEXT.match(text)):
            nr = None
        if nr:
            n, behall = nr
            ny_balk = n == 1 and flock is not None and flock > 1
            if flock is None and n <= MAX_SPRANG or ny_balk or (flock is not None and flock < n <= flock + MAX_SPRANG):
                toma()
                sista = enheter[-1][3].split("\n")[-1] if enheter else ""
                if ny_balk and enheter[-1][1] == flock and len(sista) <= 40 and not re.search(r"\d", sista) \
                        and not RUBRIK_MED_NR.match(rubrikform(sista)) and not FORTECKNINGSRAD.match(sista):
                    # Numreringen börjar om utan balkrubrik: en kort sista rad i
                    # föregående flock ("orbotæ mal.") är den nya balkens namn
                    *rader, namn = enheter[-1][3].split("\n")
                    if rader:
                        enheter[-1] = (*enheter[-1][:3], "\n".join(rader))
                    else:
                        enheter.pop()
                    balk = balknamn(namn)
                flock_fore, flock = flock, n
                if behall:
                    buffert.append(text)
                    rubrik_utan_text = text == stycken[i] and len(text) <= 90 and \
                        RUBRIK_MED_NR.match(rubrikform(text)) is not None and not ARABISKT_NR.match(text) \
                        and not ROMERSKT_MED_TEXT.match(text) and not PARENTES_NR.match(text)
                continue
        if flock is None:
            # Utan urskiljbar flock blir varje stycke en egen passage
            toma()
            enheter.append((balk, None, forkortning, text))
            continue
        buffert.append(text)
        rubrik_utan_text = False
    toma()
    enheter, rubriker = _forteckningsflockar(enheter)
    innehall.extend(rubriker)
    enheter = _forsta_flocken(enheter)
    if innehall:
        enheter.insert(0, ("innehållsförteckning", None, None, "\n".join(innehall)))
    return enheter


def _forteckningsflockar(enheter):
    """
    En förteckning som inte känts igen blir korta flockar, och balkens
    numrering börjar sedan om på 1 när texten kommer. Flockar före en sådan
    omstart i samma balk tas ut som förteckning om de nästan bara består av
    rubriker (medianen högst 160 tecken).
    """
    ut, rubriker = list(enheter), []
    i = 0
    while i < len(ut):
        balk = ut[i][0]
        j = i
        while j + 1 < len(ut) and ut[j + 1][0] == balk:
            j += 1
        flockar = [k for k in range(i, j + 1) if ut[k][1] is not None]
        omstart = next((b for a, b in zip(flockar, flockar[1:]) if ut[b][1] == 1 and ut[a][1] >= 1
                        and ut[b][1] <= ut[a][1]), None)
        if omstart is not None:
            fore = [k for k in flockar if k < omstart]
            if fore and sorted(len(ut[k][3]) for k in fore)[len(fore) // 2] <= 160:
                rubriker += [ut[k][3] for k in fore]
                ut = [e for k, e in enumerate(ut) if k not in set(fore)]
                continue
        i = j + 1
    return ut, rubriker


def _forsta_flocken(enheter):
    """
    Balkens första flock har ofta ingen rubrik eller inget nummer: text som
    står i balken före en flock 2 är flock 1.
    """
    ut = []
    for i, (balk, flock, fk, text) in enumerate(enheter):
        if flock is None and balk:
            nasta = next((e for e in enheter[i + 1:] if e[0] != balk or e[1] is not None), None)
            if nasta and nasta[0] == balk and nasta[1] == 2:
                if ut and ut[-1][0] == balk and ut[-1][1] == 1:
                    ut[-1] = (balk, 1, fk, ut[-1][3] + "\n" + text)
                else:
                    ut.append((balk, 1, fk, text))
                continue
        ut.append((balk, flock, fk, text))
    return ut


# Gängse förkortningar för lagarna; additament, tillägg och fragment får lagens
# förkortning med tillägg. Texter som saknas här hänvisas med titeln.
LAGFORKORTNING = {
    "Äldre Västgötalagen": "ÄVgL",
    "Yngre Västgötalagen, enligt Holm B 58": "YVgL",
    "Yngre Västgötalagen, tillägg, enligt Holm B 58": "YVgL Add.",
    "Yngre Västgötalagens äldsta fragment, Lydekini excerpter och anteckningar": "Lydek.",
    "Vidhemsprästens anteckningar": "Vidhemspr.",
    "Östgötalagen A, ur Holm B 50": "ÖgL",
    "Upplandslagen enl Schlyters utgåva och Codex Ups C 12, hskr A": "UL",
    "Upplandslagen enligt Codex Holm B 199, Schlyters hskr B": "UL (hskr B)",
    "Tillägg till Upplandslagen, hskr A (Ups B 12)": "UL Add.",
    "Södermannalagen, enligt Codex iuris Sudermannici": "SdmL",
    "Södermannalagens additamenta, efter NKS 2237": "SdmL Add.",
    "Dalalagen (Äldre Västmannalagen)": "DL",
    "Yngre Västmannalagen, enl Holm B 57": "VmL",
    "Hälsingelagen": "HL",
    "Smålandslagens kyrkobalk": "SmL",
    "Skånelagen, enligt Holm B 76": "SkL",
    "Gutalagen enligt Holm B 64": "GL",
    "Gutalagens additamenta enligt AM 54": "GL Add.",
    "Bjärköarätten": "BjR",
    "Magnus Erikssons Landslag": "MEL",
    "Magnus Erikssons Stadslag, exklusiva stadslagsflockar": "MESt",
    "Kristoffers Landslag": "KrL",
    "Kristoffers Landslag, flockar direkt hämtade från MEL": "KrL",
    "Kristoffers Landslag, innehållsligt ändrade flockar i förhållande til MEL": "KrL",
    "Kristoffers Landslag, nyskrivna flockar i förhållande till MEL": "KrL",
}

# Balkarnas förkortningar varierar mellan utgåvor och handböcker. Här bildas de
# enhetligt ur balkens namn, nära gängse bruk (Kkb, Kgb, Äb, Mb, Jb …); den
# fullständiga balkrubriken står kvar i adressen. Ordningen spelar roll: de
# mer specifika mönstren prövas först.
BALKFORKORTNING = [
    (r"dr[æa]+p.*vilia|draapmedvilia", "Dmv"), (r"dr[æa]+p.*va[þd]a|draapmedva", "Dvå"),
    (r"sar.*vilia|saaramaalmedvilia", "Smv"), (r"sar.*va[þd]a|saaramaalmedva", "Svå"),
    (r"va[þd]a ?mal|uaþa ?mal", "Vm"), (r"mandrap", "Md"), (r"dr[æa]+p", "Db"), (r"eghn", "Egb"), (r"va[þd]æ? sar", "Vs"), (r"bardagh", "Bd"), (r"orbot", "Ob"),
    (r"r[æe]tlos", "Rlb"), (r"vinsor|uinsor", "Vsb"), (r"r[æe]fst", "Rb"), (r"vt ?gi[æe]r", "Ub"),
    (r"ez[öo]r|e[þd]z[öo]r|edz[öo]r", "Eb"), (r"h[öø]gh?m[æa]l", "Hb"),
    (r"kirk|kyrk|krist|cristn", "Kkb"), (r"kun[uo]n|kon[uo]n", "Kgb"),
    (r"[æe]rf|aru[æe]|er[þf]a", "Äb"), (r"gip|gift", "Gb"), (r"manh[æa]l", "Mb"),
    (r"i[oø]r[þd]|jor[þd]", "Jb"), (r"bygn|bygda", "Bb"), (r"k[iy]?[öø]p", "Kmb"),
    (r"wi[þd][æe]r|vi[þd][æe]r", "Vb"), (r"[þt]i[uo]f|[þt]iuu|tiuff", "Tjb"), (r"[þt]ing", "Tb"),
    (r"forn", "Fb"), (r"fri[þd]", "Frb"), (r"malum", "Mlb"),
]


# Textbankens hänvisningar till Magnus Erikssons och Kristoffers lagar skriver
# balkarna KgB, ÄB, TgB …; samma form används för de flockar i dessa lagar som
# tolkas ur texten, så att hänvisningarna inom lagfamiljen blir lika
UTGIVARSTIL = {"Kgb": "KgB", "Gb": "GB", "Äb": "ÄB", "Jb": "JB", "Bb": "BB", "Kmb": "KpB",
               "Tb": "TgB", "Eb": "EB", "Hb": "HB", "Tjb": "TjB"}
LAGAR_MED_UTGIVARSTIL = {"MEL", "MESt", "KrL"}


def balkforkortning(balk: str | None, fran_utgivaren: str | None, lag: str | None = None) -> str | None:
    if fran_utgivaren:
        return fran_utgivaren
    if not balk:
        return None
    namn = balk.lower()
    fk = next((fk for monster, fk in BALKFORKORTNING if re.search(monster, namn)), None)
    return UTGIVARSTIL.get(fk, fk) if lag in LAGAR_MED_UTGIVARSTIL else fk


def hanvisning(lag: str | None, balk: str | None, fk: str | None, flock: int | None) -> str | None:
    """'UL Äb 10': lagens förkortning, balkens förkortning och flocken."""
    if not lag or flock is None:
        return None
    b = balkforkortning(balk, fk, lag)
    if balk and not b:
        return None
    return " ".join(x for x in (lag, b, str(flock)) if x)


# Texter utan flocknummer som paras mot en annan handskrift av samma lag
PARAS_MOT = {
    "Upplandslagen enligt Codex Holm B 199, Schlyters hskr B":
        "Upplandslagen enl Schlyters utgåva och Codex Ups C 12, hskr A",
}


def _ordmangd(text: str) -> set[str]:
    return {o for o in ordform(rubrikform(text)).split() if len(o) > 2}


def para_mot(forlaga: list[tuple], stycken: list[str]) -> list[tuple]:
    """
    Delar en text utan flocknummer efter en annan handskrift av samma lag:
    varje stycke hamnar i den flock i förlagan vars ord det delar flest av,
    med villkoret att ordningen bevaras (dynamisk programmering).
    Förteckningen och inledningen före det första stycket som liknar
    förlagan läggs i innehållsförteckningen.
    """
    utanfor = _innehallsforteckning(stycken) | {i for i, s in enumerate(stycken) if INNEHALLSRAD.match(s)}
    flockar = [e for e in forlaga if e[1] is not None]
    if not flockar:
        return segmentera(stycken)
    fl_ord = [_ordmangd(e[3]) for e in flockar]
    st_ord = [set() if i in utanfor else _ordmangd(s) for i, s in enumerate(stycken)]
    n, m = len(stycken), len(flockar)

    def likhet(i: int, j: int) -> float:
        if not st_ord[i]:
            return 0.0
        return len(st_ord[i] & fl_ord[j]) / len(st_ord[i])

    # basta[i][j]: högsta summa när stycke i läggs i flock j och ordningen bevaras
    basta = [[0.0] * m for _ in range(n)]
    fran = [[0] * m for _ in range(n)]
    for i in range(n):
        hittills, arg = float("-inf"), 0
        for j in range(m):
            if i:
                if basta[i - 1][j] > hittills:
                    hittills, arg = basta[i - 1][j], j
                basta[i][j], fran[i][j] = hittills + likhet(i, j), arg
            else:
                basta[i][j] = likhet(i, j)
    j = max(range(m), key=lambda k: basta[n - 1][k])
    val = [0] * n
    for i in range(n - 1, -1, -1):
        val[i] = j
        j = fran[i][j]
    enheter: list[tuple] = []
    forteckning: list[str] = []
    borjan = next((i for i in range(n) if likhet(i, val[i]) >= 0.3), n)
    for i, text in enumerate(stycken):
        if not text:
            continue
        balk, flock, fk, _ = flockar[val[i]]
        if i in utanfor or i < borjan:
            forteckning.append(text)
        elif enheter and enheter[-1][:2] == (balk, flock):
            enheter[-1] = (balk, flock, fk, enheter[-1][3] + "\n" + text)
        else:
            enheter.append((balk, flock, fk, text))
    if forteckning:
        enheter.insert(0, ("innehållsförteckning", None, None, "\n".join(forteckning)))
    return enheter


def adresser(enheter, lag: str | None = None) -> list[tuple[int, str, str]]:
    """
    (ordning, adress, text); adressen inleds med hänvisningen ('UL Äb 10 —
    Ærfþæ balkær, flock 10') när den kan bildas. Stycken utan flock numreras
    i ordning inom texten.
    """
    ut, stycke = [], 0
    for ordning, (balk, flock, fk, text) in enumerate(enheter, start=1):
        if balk == "innehållsförteckning":
            ut.append((ordning, balk, text))
            continue
        if flock is None:
            stycke += 1
        delar = [balk] if balk else []
        delar.append(f"flock {flock}" if flock is not None else f"stycke {stycke}")
        adress = ", ".join(delar)
        if h := hanvisning(lag, balk, fk, flock):
            adress = f"{h} — {adress}"
        ut.append((ordning, adress, text))
    return ut


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="fornsvenska_lagar", namn="Fornsvenska textbankens material: äldre och yngre lagar",
            utgivare="Språkbanken Text, Göteborgs universitet (efter Fornsvenska textbanken, Lunds universitet)",
            url="https://spraakbanken.gu.se/resurser/fsv-aldrelagar", licens="CC BY 4.0",
            version="DOI 10.23695/6bcv-5386"),
        verk=[])
    texter: list[tuple[str, str, str | None, list[str]]] = []
    for korpus in KORPUSAR:
        with bz2.open(hamta(korpus)) as fh:
            for _, el in ET.iterparse(fh, events=("end",)):
                if el.tag != "text":
                    continue
                # Attributen läses före clear(), som tömmer även dem
                texter.append((korpus, el.get("title", "").strip(), el.get("date"),
                               [stycketext(p) for p in el.findall("paragraph")]))
                el.clear()
    indelning = {titel: segmentera(stycken) for _, titel, _, stycken in texter}
    for titel, forlaga in PARAS_MOT.items():
        stycken = next(t[3] for t in texter if t[1] == titel)
        indelning[titel] = para_mot(indelning[forlaga], stycken)
    for korpus, titel, datum, stycken in texter:
        edtf, fran, till = _datering(datum)
        verk_id = f"verk:lag:{_slug(titel)}"
        utgava_id = f"utgava:lag:{_slug(titel)}"
        paket.verk.append(Verk(
            id=verk_id, titel=titel, genre="lag", sprak=["fsv"],
            datering_edtf=edtf, datering_fran=fran, datering_till=till,
            beskrivning="Dateringen avser handskriften enligt Fornsvenska textbanken, inte "
                        "lagens tillkomst.",
            extern_url=f"https://spraakbanken.gu.se/korp/?mode=old_swedish#?corpus={korpus}"))
        paket.utgavor.append((verk_id, Utgava(
            utgava_id, f"Fornsvenska textbanken (Lunds universitet), i Språkbankens korpus "
                       f"{korpus}: {titel}.", "CC BY 4.0")))
        if edtf:
            paket.vittnen.append((verk_id, Vittne(
                f"vittne:lag:{_slug(titel)}", "handskrift", f"Handskrift enligt titeln: {titel}",
                datering_edtf=edtf, datering_fran=fran, datering_till=till)))
        sett: dict[str, int] = {}
        for ordning, adress, text in adresser(indelning[titel], LAGFORKORTNING.get(titel)):
            # Id:t bildas av hänvisningen när den finns ('ul_aeb_10'), annars av adressen
            bas = _slug(adress.split(" — ")[0])
            sett[bas] = sett.get(bas, 0) + 1
            pid = f"{verk_id.split(':', 1)[1]}:{bas}" + (f"_{sett[bas]}" if sett[bas] > 1 else "")
            paket.passager.append((verk_id, Passage(
                id=pid, typ="originaltext", adress=adress, sprak="fsv", text=text,
                ordning=ordning, utgava_id=utgava_id)))
    for fil in sorted(OVERSATTNINGAR.glob("*.json")):
        paket.lagg_till_maskinoversattningar(fil, "fornsvenskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    per_verk: dict[str, list[Passage]] = {}
    for verk_id, p in paket.passager:
        per_verk.setdefault(verk_id, []).append(p)
    for v in paket.verk:
        pp = per_verk.get(v.id, [])
        med_flock = sum("flock" in p.adress for p in pp)
        balkar = len({p.adress.split(" — ")[-1].split(", flock")[0] for p in pp if ", flock" in p.adress})
        log.info("%-62s %4d passager, %4d med flock, %2d balkar", v.titel[:62], len(pp), med_flock, balkar)
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

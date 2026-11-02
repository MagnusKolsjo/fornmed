"""
Tolk för två latinska norska krönikor ur Gustav Storms utgåva Monumenta
historica Norvegiæ (Kristiania 1880, public domain):

- Theodoricus monachus, Historia de antiquitate regum Norwagiensium
  (omkring 1180), Storm s. 3–68.
- Historia Norwegie (anonym, 1100-talets senare del eller början av
  1200-talet), Storm s. 71–124. Texten är ofullständig och slutar mitt i
  Olav den heliges historia.

Texten hämtas ur Internet Archives OCR av två skanningar av samma bok
(monumentahistor01storgoog och monumentahistor00storgoog). OCR:en blandar
löptexten med sidhuvuden, radnummer i marginalen, Storms textkritiska
apparat och hans danska sakkommentarer; tolken behåller bara den latinska
löptexten. Den första skanningen är huvudtext. Den andra används för att
rätta enskilda ord där OCR:erna skiljer sig och huvudtextens läsning inte
förekommer någon annanstans i texterna.

Theodoricus delas i prolog, kapitelförteckning och 34 kapitel. Historia
Norwegie delas efter handskriftens rubriker som Storm återger: prolog,
bokens inledning och åtta avsnitt (De tripartito incolatu Norwegiæ …
De ortu regum). Adressen anger kapitlet eller rubriken och sidorna i
Storms utgåva.

Svenska översättningar gjorda av språkmodell ligger i data/oversattningar/storm_mhn/
(se RIKTLINJER.md där) och laddas som egna utgåvor märkta som maskinöversättning.

Användning:
    python -m tolkar.storm_mhn
    python -m tolkar.storm_mhn --torr
"""

import argparse
import difflib
import logging
import re
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "storm_mhn"

log = logging.getLogger("tolkar.storm_mhn")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "storm_mhn"
OCR_URL = "https://archive.org/download/{id}/{id}_djvu.txt"
# Den första skanningen har färre OCR-fel och saknar inga sidor; den andra
# saknar Theodoricus s. 6–7 men rättar enstaka ord
SKANNINGAR = ["monumentahistor01storgoog", "monumentahistor00storgoog"]

UTGAVA_REFERENS = ("Gustav Storm (utg.), Monumenta historica Norvegiæ. Latinske kildeskrifter til "
                   "Norges historie i middelalderen, Kristiania 1880")
LICENS = "Public domain"

ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}

# Historia Norwegies rubriker i Storms utgåva. OCR:en skriver ibland ihop
# orden ('Deorturegum'), så rubrikerna känns igen på bokstäverna utan mellanrum
HN_RUBRIKER = [
    "Incipit liber primus in historia Norwegiæ.",
    "De tripartito incolatu Norwegiæ.",
    "De montanis Norwegiæ.",
    "De Finnis.",
    "De tributariis insulis.",
    "De Orchadibus insulis.",
    "De insulis ovium.",
    "De glaciali insula.",
    "De ortu regum.",
]

# Storms apparat anger handskrifter och tidigare utgivare med sigler
# (A, K, S för Theodoricus; Cd., M., B., Gj., Cat., Reg. för Historia
# Norwegie) och danska termer. En rad med flera sådana ord hör till apparaten
SIGEL = re.compile(
    r"^(?:A|K|S|B|M|AK|AS|KS|SK|AB|BK|AKS|ABK|ASB|KSB|Cd|Gj|Cat|Reg|Cod|rettet|mgl|mgL|ML|tilf|"
    r"læste|udfyldt|udfjldt|indsat|ikke|saa|som|eller|efter|men|har|Trykfeil|oftest|oftere)$")
STARK_SIGEL = re.compile(r"^(?:AK|AS|KS|SK|AB|BK|AKS|ABK|ASB|KSB|Cd|Gj|Cat|Reg|rettet|mgl|mgL|tilf|læste|"
                         r"udfyldt|udfjldt|indsat|Trykfeil)$")
DANSKA = re.compile(
    r"^(?:og|er|af|til|det|den|som|med|paa|ikke|der|har|hvor|efter|ogsaa|eller|men|hans|hvis|"
    r"sml|cfr|jfr|efr|ofr|Forf|Meningen|Haandskrift|Haandskr|Haandskrifter|nedenfor|ovenfor|"
    r"rimeligvis|hvilket|ved|fra|altsaa|kun|vel|denne|dette|disse|maa|kan|skal|siger|sige|"
    r"Aar|Konge|Kongen|Navn|Feil|Udg|Hskr|Fnm|Flat|Agrip|Ågrip|Landn|Landnåma|Suhm|Kirchmann|"
    r"læses|rettet|Sagaerne|Sagaen|Tilnavn|Afskriver|Afskriverfeil|Sted|Steder|om|nævnes|"
    r"Ann|reg|Odd|Islendingabok|Snorre|Saxo|Adam|Munch|Bugge|Gjessing|ogsaa)$")
# Ord som är vanliga i latinsk löptext men inte i danskan
LATIN = re.compile(
    r"^(?:et|in|est|quod|ad|cum|non|qui|quæ|quam|sed|vero|ut|enim|autem|ejus|eum|eo|de|ab|"
    r"ex|per|post|hoc|hic|hæc|illo|ille|ipse|suis|suo|sua|sunt|esset|erat|fuit|igitur|itaque|"
    r"tamen|nam|atque|ac|nec|nee|rex|regis|regem|filius|filium|anno|annis|inter|super|sibi|se|"
    r"eis|quo|quia|dum|ita|etiam|item|quidem|deinde|tunc|tune)$")


@dataclass
class Rad:
    sida: int
    text: str


@dataclass
class Del:
    """En passage under uppbyggnad: rubrik, sidor och textrader."""
    nyckel: str           # 'prolog', 'capitula', '3', …
    rubrik: str | None
    rader: list[Rad] = field(default_factory=list)


def romersk(tal: str) -> int | None:
    # OCR:en läser II som U och III som m ('XXXUL', 'XXVm')
    tal = tal.replace("U", "II").replace("m", "III").replace("l", "I").upper()
    if not tal or any(t not in ROMERSKA for t in tal):
        return None
    varden = [ROMERSKA[t] for t in tal]
    return sum(-v if i + 1 < len(varden) and v < varden[i + 1] else v for i, v in enumerate(varden))


def hamta(skanning: str) -> Path:
    fil = KATALOG / f"{skanning}_djvu.txt"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        url = OCR_URL.format(id=skanning)
        log.info("Hämtar %s", url)
        urllib.request.urlretrieve(url, fil)
    return fil


# ---------------------------------------------------------------------------
# Sidor
# ---------------------------------------------------------------------------

# Sidhuvudenas titlar med bara versaler, för jämförelse med förvanskade sidhuvuden
TITLAR = ["HISTORIANORWEGIAE", "THEODRICIMONACHI", "HISTORIADEANTIQUITATEREGUMNORWAGIENSIUM",
          "PROLOGUSTHEODRICI"]
_SIDNYCKEL = re.compile(r"histor|theod|monach|prolog|norw|antiq", re.I)


def _ar_sidhuvud(rad: str, foregaende: str) -> bool:
    """
    Utgåvans sidhuvud ('4 PROLOGUS THEODRICI.', 'HISTORIA NORWEGIÆ. 93')
    står efter en tom rad och är kort. OCR:en förvanskar bokstäverna kraftigt,
    så det räcker med ett av titelorden eller en rad med mest versaler och
    ett sidnummer i ena änden.
    """
    s = rad.strip()
    if not s or foregaende.strip() or len(s) > 75 or len(s.split()) > 8 or s.endswith("-"):
        return False
    if re.match(r"^\W*[CGO][a-z*]{1,2}p", s) or re.match(r"^\W*(?:Incipi|Explic|Jncipi|Prologus\s+inc)", s):
        return False
    # Kommentarens lemman kan nämna verkets titel ('3. Historia Normannorum] cfr. …')
    if "]" in s or LEMMA.match(s):
        return False
    bokstaver = [c for c in s if c.isalpha()]
    if len(bokstaver) < 6:
        return False
    versaler = sum(c.isupper() for c in bokstaver) / len(bokstaver)
    if _SIDNYCKEL.search(s) and (versaler >= 0.5 or re.match(r"^\W*historia\s+(?:de\s+antiq|norw)", s, re.I)):
        return True
    delar = s.split()
    if re.fullmatch(r"\d{1,3}", delar[0]) or re.fullmatch(r"\d{1,3}", delar[-1]):
        if versaler >= 0.5 and len(bokstaver) >= 8 and not _ar_apparat(s):
            return True
    # Svårt förvanskade sidhuvuden ('iS HJSTORlA NOBWBGtfA') liknar ändå titeln
    versalt = re.sub(r"[^A-Z]", "", s.upper().replace("Æ", "AE"))
    return versaler >= 0.5 and any(difflib.SequenceMatcher(None, versalt, t).ratio() >= 0.5 for t in TITLAR)


def _sidnummer(rad: str) -> tuple[int | None, int | None]:
    """
    (tolkat sidnummer, paritet) ur ett sidhuvud. Jämna sidor har numret
    först, udda sist; i Theodoricus står dessutom 'THEODRICI MONACHI' på
    jämna och 'HISTORIA DE ANTIQUITATE …' på udda sidor, vilket ger
    pariteten också när numret är oläsligt.
    """
    delar = rad.split()
    forst, sist = delar[0], delar[-1]
    tolkat, paritet = None, None
    # Siffror som OCR:en delat ('1 1 5') står alltid sist
    if m := re.search(r"(?:^|\s)((?:\d\s){1,2}\d)\s*$", rad):
        tolkat, paritet = int(re.sub(r"\s", "", m.group(1))), 1
    elif re.fullmatch(r"\d{1,3}", forst):
        tolkat, paritet = int(forst), 0
    elif re.fullmatch(r"\d{1,3}", sist):
        tolkat, paritet = int(sist), 1
    # Ett oläsligt nummer syns ändå som en kort token i ena änden
    elif len(forst) <= 3 and len(delar) > 1 and not re.fullmatch(r"[A-ZÆ]{2,3}\.?", forst):
        paritet = 0
    elif len(sist) <= 3 and len(delar) > 1 and not re.fullmatch(r"[A-ZÆ]{2,3}\.?", sist):
        paritet = 1
    versal = rad.upper()
    if paritet is None:
        if "ANTIQ" in versal or "QUITAT" in versal:
            paritet = 1
        elif "THEOD" in versal or "PROLOG" in versal or "MONAC" in versal:
            paritet = 0
    return tolkat, paritet


def sidor(rader: list[str], forsta_sida: int) -> list[tuple[int, list[str]]]:
    """
    Raderna uppdelade per sida i utgåvan. Sidnumret räknas fram från
    föregående sida, eftersom OCR:en ofta läser numret fel ('lo', 'fc3') och
    ibland missar ett sidhuvud. Ett tolkat nummer godtas om det ligger nära
    det framräknade; annars väljs nästa sida med rätt paritet.
    """
    ut: list[tuple[int, list[str]]] = [(forsta_sida, [])]
    foregaende = ""
    for rad in rader:
        if _ar_sidhuvud(rad, foregaende):
            tidigare = ut[-1][0]
            tolkat, paritet = _sidnummer(rad.strip())
            if tolkat is not None and tidigare + 1 <= tolkat <= tidigare + 3:
                nr = tolkat
            else:
                nr = tidigare + 1
                if paritet is not None and nr % 2 != paritet:
                    nr += 1
            ut.append((nr, []))
        else:
            ut[-1][1].append(rad)
        foregaende = rad
    return ut


def sidor_med_luckor(rader: list[str], forsta_sida: int) -> list[tuple[int, list[str], bool]]:
    """Som sidor(), med en flagga för sidor där nästa sidas sidhuvud saknas i OCR:en."""
    s = sidor(rader, forsta_sida)
    return [(nr, r, i + 1 < len(s) and s[i + 1][0] > nr + 1) for i, (nr, r) in enumerate(s)]


# ---------------------------------------------------------------------------
# Löptext, apparat och kommentar
# ---------------------------------------------------------------------------

# Kommentarens lemma: '9 — 11. horum memoria-recolunt] Meningen …', '19. Boetius] cfr.'
LEMMA = re.compile(r"^\W{0,3}[\dlI?]{1,3}\s*(?:[—–-]\s*[\dlI]{1,3}\s*)?[.,:]\s*.{0,90}?[\]}]")
# Apparatets not börjar med ett hänvisningstecken: siffra, apostrof, asterisk o.d.
NOTTECKEN = re.compile(r"^\s*(?:\d{1,2}|[*'^°®»«>•■\"`,.]|[*'^°®]{2})\s+\S")
RUBRIK = re.compile(r"^\W{0,2}(?:Incipi|Jncipi|IncipU|Explic|Explid|Expliei|EefpUcU|Prologus\s+incipit)", re.I)
KAPITEL = re.compile(r"^\W{0,2}(?:\d{1,2}\s+)?[CGO][a-z*]{1,2}p?[\s.,*'’]*([IVXLCUlm]{1,8})\s*[.,]?\s+(\S.*)$")


def _ord(rad: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", rad)


def _ar_apparat(rad: str) -> bool:
    """
    En rad i den textkritiska apparaten: hänvisningstecken följt av sigler
    eller danska termer. Sigler som aldrig förekommer i latinsk löptext
    ('AKS', 'Cd.', 'mgl.') räcker i sig; två av dem räcker också när
    OCR:en har tappat hänvisningstecknet.
    """
    tokens = [t.strip(".,;:()!'") for t in rad.split()]
    starka = sum(bool(STARK_SIGEL.match(t)) for t in tokens)
    if starka >= 2:
        return True
    if not NOTTECKEN.match(rad) and not re.match(r"^\s*\d{1,2}\s*[A-Z]", rad):
        return False
    return starka >= 1 or sum(bool(SIGEL.match(t)) for t in tokens) >= 2 or \
        sum(bool(DANSKA.match(t)) for t in tokens) >= 2


def _dansk(block: list[str]) -> bool:
    ord_ = [w for r in block for w in _ord(r)]
    if not ord_:
        return False
    danska = sum(bool(DANSKA.match(w)) for w in ord_)
    latin = sum(bool(LATIN.match(w)) for w in ord_)
    return danska >= 2 and danska > latin * 0.5 or danska >= 4


def _latinsk(block: list[str]) -> bool:
    ord_ = [w for r in block for w in _ord(r)]
    if len(ord_) < 6:
        return False
    latin = sum(bool(LATIN.match(w)) for w in ord_)
    return latin / len(ord_) >= 0.12 and not _dansk(block)


def _brus(block: list[str]) -> bool:
    """Ensamma radnummer, arksignaturer ('5*') och skräptecken mellan blocken."""
    return sum(len(_ord(r)) and max(len(w) for w in _ord(r)) >= 3 for r in block) == 0


def _kort_versalrad(rad: str) -> bool:
    """En kort rad med mest versaler, som ett sidhuvud som OCR:en förvanskat bortom igenkänning."""
    bokstaver = [c for c in rad if c.isalpha()]
    return len(rad.strip()) <= 50 and len(bokstaver) >= 6 and \
        sum(c.isupper() for c in bokstaver) / len(bokstaver) >= 0.4 and "]" not in rad


def _block(rader: list[str]) -> list[list[str]]:
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


def lopande_rader(sidrader: list[str], sammanslagen: bool = False) -> tuple[list[tuple[int, str]], int]:
    """
    Sidans löptext som (sidtillägg, rad) och antalet återupptagna block.

    På varje sida står löptexten först, därefter apparaten och sist
    kommentaren. Löptexten slutar vid det första blocket eller den första
    raden som är apparat eller kommentar. När OCR:en har missat ett
    sidhuvud följer nästa sidas löptext direkt efter kommentaren. Det går
    bara att känna igen säkert när nästa sida börjar med en rubrik
    ('Incipiunt capitula', 'Cap. XVII.'): kommentaren citerar ofta långa
    latinska stycken, så vanlig latinsk text efter kommentaren räknas som
    kommentar. På en sida där sidnumreringen visar att nästa sidhuvud
    saknas (sammanslagen) godtas också ett latinskt block som följer
    direkt på en kort rad som kan vara det förvanskade sidhuvudet. Texten
    efter en sådan rubrik får sidtillägget 1, 2 … så att sidnumret blir
    rätt. Övrig löptext på en sida utan sidhuvud hämtas ur den andra
    skanningen (se ratta).
    """
    ut: list[tuple[int, str]] = []
    tillagg = 0
    i_noter = False
    foregaende: list[str] = []
    for block in _block(sidrader):
        if _brus(block):
            continue
        if i_noter:
            rubrik = KAPITEL.match(block[0]) or RUBRIK.match(block[0])
            sidhuvud = sammanslagen and len(foregaende) == 1 and _kort_versalrad(foregaende[0]) and \
                _latinsk(block) and not LEMMA.match(block[0]) and not _ar_apparat(block[0])
            foregaende = block
            if not (rubrik or sidhuvud):
                continue
            tillagg += 1
            i_noter = False
        if LEMMA.match(block[0]) or _ar_apparat(block[0]) or _dansk(block):
            i_noter = True
            continue
        for rad in block:
            if LEMMA.match(rad) or _ar_apparat(rad):
                i_noter = True
                break
            ut.append((tillagg, rad))
        ut.append((tillagg, ""))
    return ut, tillagg


# ---------------------------------------------------------------------------
# Rensning av löptexten
# ---------------------------------------------------------------------------

# Radnummer i marginalen så som OCR:en läser dem (5, 10, 15, 20, 25)
RADNUMMER = r"(?:\d{1,3}|\$|s|so|s0|2o|ao|lo|l0|io|i0|IO|lO|lö|i5|u|tø|t0|\%|\d[A-Za-z]|[A-Za-z]\d)"

# Felläsningar av vanliga latinska ord där OCR:en har läst c som e och u
# som n; formerna till vänster är inga latinska ord
OCR_ORD = {"nee": "nec", "Nee": "Nec", "tune": "tunc", "Tune": "Tunc", "hie": "hic", "Hie": "Hic",
           "hine": "hinc", "Hine": "Hinc", "ejns": "ejus", "qnod": "quod", "qnam": "quam",
           "qnæ": "quæ", "qni": "qui", "nnde": "unde", "Hue": "Huc"}


def _utan_radnummer(rad: str) -> str:
    rad = re.sub(rf"^\s*{RADNUMMER}\s+(?=\S)", "", rad)
    rad = re.sub(rf"\s+{RADNUMMER}\s*$", "", rad)
    # Isolerade hänvisningstecken och skräptecken i radens ändar
    rad = re.sub(r"^[\s•■▼*'^°»«.,]+(?=[A-Za-zÆæŒœ\[])", "", rad)
    return rad.rstrip(" •■'\"*")


def _siffror_i_ord(token: str) -> str:
    """
    OCR:en läser långt s som 8 och l, I, O som 1 och 0 inne i ord
    ('bla8phemia', '01avus', '11lam'). En siffra före versal är en notsiffra
    ('8Carolo').
    """
    if not re.search(r"\d", token) or len(re.findall(r"[^\W\d_]", token)) < 2:
        return token
    token = re.sub(r"\d+(?=[A-ZÆ])", "", token)
    token = re.sub(r"^1(?=[a-z1])", "I", token)
    token = re.sub(r"^0(?=[a-z1])", "O", token)
    token = re.sub(r"(?<=[^\W\d_])1|1(?=[a-z])", "l", token)
    token = re.sub(r"(?<=[^\W\d_])0(?=[^\W\d_])", "o", token)
    token = re.sub(r"8(?=[^\W\d_])|(?<=[^\W\d_])8", "s", token)
    token = re.sub(r"(?<=[^\W\d_])6(?=[^\W\d_])", "s", token)
    return token


def rensa(rader: list[str]) -> str:
    """
    Löptextens rader som en sammanhängande text: radnummer, Storms
    hänvisningstecken till apparaten (upphöjda siffror och tecken efter
    ord, '[' som markerar början av ett varierande textställe) och
    avstavningar tas bort, och ord som OCR:en skrivit ihop eller
    spärrat isär rättas så långt det går utan ordbok.
    """
    text = "\n".join(_utan_radnummer(r) for r in rader if r.strip())
    text = re.sub(r"[\[\]▼■•®°^]", "", text)
    # Avstavning över radslut; 'pulchre-comatus' skrivs med bindestreck i utgåvan
    text = re.sub(r"(pulchre)\s*-\s*", r"\1-", text)
    # OCR:en läser ibland avstavningstecknet som '>' eller '~'
    text = re.sub(r"(\w)\s*[-~>¬]\s*\n\s*(?=\w)", r"\1", text)
    # Upphöjda notsiffror sitter direkt efter ordet ('Tryggva5', 'enim3', 'injunctum1'')
    text = re.sub(r"(?<=[^\W\d_])\d{1,2}(?=[\s.,;:!?)'’*]|$)", "", text)
    text = re.sub(r"(?<=[^\W\d_.,;:])['’`*»«\"$<>©]+(?=\W|$)", "", text)
    text = re.sub(r"(?<=[.,;:])\d{0,2}['’`*\"]+|(?<=[.,;:])\d{1,2}(?=\s|$)", "", text)
    # Radnummer mitt i raden där OCR:en blandat ihop spalterna ('3ft', '1S')
    text = re.sub(r"(?:(?<=\s)|^)\d[A-Za-z]{1,2}(?=\s|$)", "", text)
    text = re.sub(r"(?<=[a-z])\|(?=[a-z])", "l", text)
    text = re.sub(r"(?:(?<=\s)|^)[<>|~*©£$\\]+(?=\s|$)", "", text)
    text = re.sub(r"(?:(?<=\s)|^)['’`*»«\"]+(?=\w)", "", text)
    text = " ".join(_siffror_i_ord(t) for t in text.split())
    # Ensamma notsiffror och hänvisningstecken; löptexten skriver tal med romerska siffror
    text = re.sub(r"(?:(?<=\s)|^)(?:\d{1,3}[*'’]*|[*'’\"]+)(?=\s|$)", "", text)
    # Spärrad stil blir enstaka bokstäver i OCR:en ('V i c i s t i')
    text = re.sub(r"\b(?:[^\W\d_] ){3,}[^\W\d_]\b", lambda m: m.group(0).replace(" ", ""), text)
    text = re.sub(r"(?<=[a-zæœ][.,;:])(?=[A-Za-zÆæ])", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return " ".join(_ersatt_karna(t, OCR_ORD.get) for t in text.split()).strip()


def _ersatt_karna(token: str, uppslag) -> str:
    """Byter ordet i en token med omgivande skiljetecken ('nee,' → 'nec,') om uppslag ger en ersättning."""
    m = re.fullmatch(r"(\W*)(.*?)(\W*)", token)
    ny = uppslag(m.group(2)) if m.group(2) else None
    return f"{m.group(1)}{ny}{m.group(3)}" if ny else token


# Bokstäver som OCR:en förväxlar i den här utgåvans typsnitt. a/o tas inte med,
# eftersom bytet ger andra böjningsformer av samma ord ('regna'/'regno')
FORVAXLINGAR = [("n", "u"), ("u", "n"), ("e", "c"), ("c", "e"), ("rn", "m"), ("m", "rn"), ("b", "h"),
                ("h", "b"), ("li", "h"), ("ii", "u"), ("y", "v"), ("t", "l"),
                ("f", "s"), ("ø", "o"), ("å", "a")]


def ratta_ordform(token: str, frekvens: Counter) -> str:
    """
    Rättar ett ord som bara förekommer en gång i texterna: en enda
    förväxling av bokstäver (n/u, c/e, rn/m …) som ger ett ord som
    förekommer minst tre gånger, eller en versal inne i ordet där två
    ihopskrivna ord ('filiumTryggva') båda förekommer på annat håll.
    Ordförrådet är texternas eget, så ovanliga men riktiga ord lämnas
    orörda så länge ingen förväxling ger ett vanligt ord.
    """
    def uppslag(ord_: str) -> str | None:
        if len(ord_) < 3 or frekvens[_norm(ord_)] > 1 or not ord_.isalpha():
            return None
        if m := re.fullmatch(r"([a-zæœ]{2,})([A-ZÆ][a-zæœ]{2,})", ord_):
            if frekvens[_norm(m.group(1))] >= 2 and frekvens[_norm(m.group(2))] >= 2:
                return f"{m.group(1)} {m.group(2)}"
        basta, basta_frekvens = None, 2
        for fel, ratt in FORVAXLINGAR:
            for m in re.finditer(re.escape(fel), ord_):
                kandidat = ord_[:m.start()] + ratt + ord_[m.end():]
                if frekvens[_norm(kandidat)] > basta_frekvens:
                    basta, basta_frekvens = kandidat, frekvens[_norm(kandidat)]
        return basta
    return _ersatt_karna(token, uppslag)


# ---------------------------------------------------------------------------
# Indelning i passager
# ---------------------------------------------------------------------------

def _region(rader: list[str], verk: str) -> tuple[int, int]:
    """Radintervallet för ett verk i OCR-texten."""
    theod = next(i for i, r in enumerate(rader) if re.search(r"prologus\s+Theod", r, re.I))
    hn = next(i for i, r in enumerate(rader) if i > theod and re.match(r"^\s*II\.\s*$", r))
    slut = next(i for i, r in enumerate(rader) if i > hn and re.match(r"^\s*III\.\s*$", r))
    if verk == "theodoricus":
        return theod, hn
    return next(i for i, r in enumerate(rader) if i > hn and re.match(r"^\s*Prologus\s+incipit", r)), slut


def _bokstaver(s: str) -> str:
    return re.sub(r"[^a-zæœ]", "", s.lower())


def _skrap(rad: str) -> bool:
    """En rad som mest består av skräptecken och sigler ('» 4* »W* 8B„ %8P* ntfus A+')."""
    tecken = [c for c in rad if not c.isspace()]
    if len(tecken) < 8 or KAPITEL.match(rad) or _hn_rubrik(rad) is not None:
        return False
    return sum(c.isalpha() for c in tecken) / len(tecken) < 0.65


def _hn_rubrik(rad: str) -> int | None:
    """Index i HN_RUBRIKER om raden är en av Historia Norwegies rubriker."""
    s = rad.strip()
    if len(s) > 60 or not s:
        return None
    b = _bokstaver(s)
    for i, rubrik in enumerate(HN_RUBRIKER):
        mal = _bokstaver(rubrik)
        if difflib.SequenceMatcher(None, b[:len(mal) + 4], mal).ratio() >= 0.8:
            return i
    return None


def dela(skanning_rader: list[str], verk: str) -> tuple[list[Del], int]:
    """
    Verkets passager ur en skanning. Returnerar också antalet block som
    återupptogs som löptext efter kommentaren (se lopande_rader).
    """
    start, slut = _region(skanning_rader, verk)
    forsta_sida = 3 if verk == "theodoricus" else 71
    delar: list[Del] = [Del("prolog", None)]
    aterupptagna = 0
    senaste_kapitel = 0
    rubrikrader = 0
    efter_rubrik = False
    slutat = False
    for sida, sidrader, sammanslagen in sidor_med_luckor(skanning_rader[start:slut], forsta_sida):
        if slutat:
            break
        text, ater = lopande_rader(sidrader, sammanslagen)
        aterupptagna += ater
        for tillagg, rad in text:
            sida_ = sida + tillagg
            s = rad.strip()
            if not s:
                continue
            # Rubrikens andra rad ('de antiquitate regum Norwagiensium.') och skräprader
            if efter_rubrik and len(s) < 60 and re.search(r"regum|Norwag|Theod", s, re.I):
                efter_rubrik = False
                continue
            efter_rubrik = bool(RUBRIK.match(s))
            # Verkets slutrubrik ('Explicit historia Theodrici …', 'Explicit.'); därefter följer
            # bara apparaten
            if efter_rubrik and re.match(r"^\W*E", s) and not re.search(r"prolog|capit", s, re.I):
                slutat = True
                break
            if _skrap(s):
                continue
            if verk == "theodoricus":
                if RUBRIK.match(s):
                    # 'Incipiunt capitula' inleder kapitelförteckningen; övriga
                    # rubriker (Incipit/Explicit) hör inte till texten
                    if re.search(r"capi", s, re.I) and re.search(r"cipiunt", s, re.I):
                        delar.append(Del("capitula", None))
                        delar[-1].rader.append(Rad(sida_, ""))
                    continue
                if m := KAPITEL.match(s):
                    nr = romersk(m.group(1))
                    if nr is None or not senaste_kapitel < nr <= senaste_kapitel + 3:
                        nr = senaste_kapitel + 1
                    senaste_kapitel = nr
                    delar.append(Del(str(nr), f"Cap. {_romerskt(nr)}. {rensa([m.group(2)])}"))
                    rubrikrader = 0
                    delar[-1].rader.append(Rad(sida_, ""))
                    continue
                # Rubriken fortsätter på högst två rader ('quendam et alios … verbum' /
                # 'Dei Norwagiensibus.'): en rad som börjar med gemen eller ett kort
                # avslutande stycke, så länge rubriken inte slutat med punkt
                if delar[-1].rubrik and not [r for r in delar[-1].rader if r.text] and rubrikrader < 2 \
                        and not delar[-1].rubrik.endswith(".") \
                        and (s[0].islower() or (len(s.split()) <= 3 and s.endswith("."))):
                    delar[-1].rubrik = re.sub(r"-$", "", delar[-1].rubrik) + \
                        ("" if delar[-1].rubrik.endswith("-") else " ") + rensa([s])
                    rubrikrader += 1
                    continue
            else:
                idx = _hn_rubrik(s)
                if idx is not None:
                    delar.append(Del(str(idx + 1), None if idx == 0 else HN_RUBRIKER[idx]))
                    delar[-1].rader.append(Rad(sida_, ""))
                    continue
                if RUBRIK.match(s):
                    continue
            delar[-1].rader.append(Rad(sida_, rad))
    return [d for d in delar if any(r.text.strip() for r in d.rader)], aterupptagna


def _romerskt(tal: int) -> str:
    ut = ""
    for v, b in ((50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while tal >= v:
            ut += b
            tal -= v
    return ut


# ---------------------------------------------------------------------------
# Rättning mot den andra skanningen
# ---------------------------------------------------------------------------

# Minsta antal ord för att ett stycke som bara finns i den andra skanningen
# ska infogas; kortare skillnader är OCR-brus och ordningsfel
MIN_INFOGNING = 25


def _norm(token: str) -> str:
    return re.sub(r"[^a-zæœ]", "", token.lower().replace("j", "i").replace("v", "u"))


def _med_skiljetecken(huvud: str, andra: str) -> str:
    """Den andra skanningens ord med huvudtextens skiljetecken efter ordet, om den andra saknar dem."""
    andra = re.sub(r"[^\w.,;:!?()]+$", "", andra)
    slut = re.search(r"[.,;:!?]+$", huvud)
    return andra + slut.group(0) if slut and not re.search(r"[.,;:!?]$", andra) else andra


def ratta(huvud: str, andra: str, frekvens: Counter, infogade: list[str],
          hela_verket: str = "") -> tuple[str, int]:
    """
    Rättar huvudtexten ord för ord mot den andra skanningens text av samma
    passage. Ett ord byts bara när orden står på samma plats i båda och
    huvudtextens läsning inte förekommer någon annanstans i texterna medan
    den andra skanningens gör det; det fångar OCR-fel som 'ejusdera' för
    'ejusdem' utan att röra ovanliga namn. Ord som OCR:en har sprängt
    ('b el li ei s') fogas ihop när den andra skanningen har dem hela.
    Längre stycken som bara finns i den andra skanningen infogas och
    läggs till i infogade, utom när de står någon annanstans i huvudtexten
    (hela_verket, normaliserade ord); då har den andra skanningen missat en
    rubrik och stycket hör till en annan passage. Returnerar den rättade
    texten och antalet ändrade ord.
    """
    a, b = huvud.split(), andra.split()
    na, nb = [_norm(t) for t in a], [_norm(t) for t in b]
    ut: list[str] = []
    andringar = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nb, autojunk=False).get_opcodes():
        if op == "equal":
            ut.extend(a[i1:i2])
        elif op == "replace" and i2 - i1 == j2 - j1:
            for x, y in zip(range(i1, i2), range(j1, j2)):
                if na[x] and nb[y] and na[x] != nb[y] and frekvens[na[x]] <= 1 and frekvens[nb[y]] >= 2:
                    ut.append(_med_skiljetecken(a[x], b[y]))
                    andringar += 1
                else:
                    ut.append(a[x])
        elif op == "replace" and j2 - j1 < i2 - i1 and all(len(n) <= 4 for n in na[i1:i2]) \
                and any(len(n) <= 2 for n in na[i1:i2]) and (
                "".join(na[i1:i2]) == "".join(nb[j1:j2])
                or i2 - i1 >= 3 and difflib.SequenceMatcher(
                    None, "".join(na[i1:i2]), "".join(nb[j1:j2])).ratio() >= 0.75):
            # Ord som OCR:en har sprängt ('b el li ei s') står hela i den andra skanningen;
            # huvudtextens skiljetecken efter ordet behålls
            ut.extend(b[j1:j2 - 1] + [_med_skiljetecken(a[i2 - 1], b[j2 - 1])])
            andringar += 1
        elif op == "delete" and not any(len(n) >= 2 for n in na[i1:i2]):
            # Tecken utan bokstäver som bara finns i huvudtexten är radnummer och skräp
            andringar += 1
        elif (j2 - j1) - (i2 - i1) >= MIN_INFOGNING and _latinsk([" ".join(b[j1:j2])]) \
                and " ".join(nb[j1:j1 + 8]) not in hela_verket:
            # En hel sida som saknas i huvudtexten, därför att OCR:en missat
            # sidhuvudet och sidans löptext togs för kommentar
            ut.extend(a[i1:i2] if op == "replace" and i2 - i1 > 3 else [])
            ut.extend(b[j1:j2])
            infogade.append(" ".join(b[j1:j2]))
        else:
            ut.extend(a[i1:i2])
    return " ".join(ut), andringar


# ---------------------------------------------------------------------------
# Paket
# ---------------------------------------------------------------------------

VERK = {
    "theodoricus": dict(
        verk_id="verk:theodoricus",
        titel="Historia de antiquitate regum Norwagiensium",
        upphov="Theodoricus monachus",
        datering=("1177/1188", 11770101, 11881231),
        beskrivning="Kortfattad latinsk historia över de norska kungarna från Harald hårfager till "
                    "Sigurd Jorsalafarares död 1130, tillägnad ärkebiskop Augustinus (Øystein "
                    "Erlendsson) av Nidaros. Författaren säger sig bygga på islänningarnas muntliga "
                    "tradition och kvad och gör lärda utvikningar. Storm s. 3–68.",
        extern_url="https://archive.org/details/monumentahistor01storgoog",
    ),
    "historia_norwegie": dict(
        verk_id="verk:historia_norwegie",
        titel="Historia Norwegie",
        upphov=None,
        datering=("1160/1220", 11600101, 12201231),
        beskrivning="Anonym latinsk beskrivning av Norge och skattländerna (Orkney, Färöarna, "
                    "Island) med finnarna, följd av en kungalängd från ynglingarna. Bevarad i en "
                    "ofullständig handskrift som slutar med Olav den heliges hemkomst. Storm s. 71–124.",
        extern_url="https://archive.org/details/monumentahistor01storgoog",
    ),
}


def _adress(verk: str, d: Del) -> str:
    sidor_ = [r.sida for r in d.rader]
    s = f"{min(sidor_)}" if min(sidor_) == max(sidor_) else f"{min(sidor_)}–{max(sidor_)}"
    if verk == "theodoricus":
        namn = {"prolog": "prolog", "capitula": "kapitelförteckning"}.get(d.nyckel, f"kap. {d.nyckel}")
    else:
        namn = {"prolog": "prolog", "1": "bok I, inledning"}.get(d.nyckel) or \
            f"avsnitt {int(d.nyckel) - 1}, {(d.rubrik or '').rstrip('.')}"
    return f"{namn} (Storm s. {s})"


def tolka_verk(verk: str, skanningar: dict[str, list[str]]) -> tuple[list[Del], dict[str, str]]:
    """Verkets passager ur huvudskanningen, med texten rättad mot den andra."""
    huvud_id, andra_id = SKANNINGAR
    huvud, ater = dela(skanningar[huvud_id], verk)
    andra, ater2 = dela(skanningar[andra_id], verk)
    log.info("%s: %d passager i %s, %d i %s; %d + %d block återupptagna efter kommentaren",
             verk, len(huvud), huvud_id, len(andra), andra_id, ater, ater2)
    andra_text = {d.nyckel: rensa([r.text for r in d.rader]) for d in andra}
    andra_rubrik = {d.nyckel: d.rubrik for d in andra if d.rubrik}
    frekvens = Counter(_norm(t) for text in [rensa([r.text for r in d.rader]) for d in huvud]
                       for t in text.split())
    frekvens.update(_norm(t) for text in andra_text.values() for t in text.split())
    texter: dict[str, str] = {}
    totalt = ordformer = 0
    hela_verket = " ".join(_norm(t) for d in huvud for t in rensa([r.text for r in d.rader]).split())
    for d in huvud:
        text = rensa([r.text for r in d.rader])
        if d.nyckel in andra_text:
            infogade: list[str] = []
            text, n = ratta(text, andra_text[d.nyckel], frekvens, infogade, hela_verket)
            for stycke in infogade:
                log.info("%s:%s: infogat ur %s: %s …", verk, d.nyckel, andra_id, stycke[:80])
            totalt += n
        else:
            log.warning("%s: %s saknas i %s och rättas inte", verk, d.nyckel, andra_id)
        if d.rubrik:
            if d.nyckel in andra_rubrik:
                d.rubrik, n = ratta(d.rubrik, andra_rubrik[d.nyckel], frekvens, [])
                totalt += n
            # OCR:en läser ibland rubrikens slutpunkt som bindestreck ('gestis ejus-')
            d.rubrik = re.sub(r"-$", ".", d.rubrik)
        rattade = [ratta_ordform(t, frekvens) for t in text.split()]
        ordformer += sum(x != y for x, y in zip(text.split(), rattade))
        text = " ".join(rattade)
        texter[d.nyckel] = text
    log.info("%s: %d ord rättade mot %s, %d ordformer rättade efter förväxlade bokstäver",
             verk, totalt, andra_id, ordformer)
    return huvud, texter


def bygg_paket() -> Kallpaket:
    skanningar = {s: hamta(s).read_text(encoding="utf-8").split("\n") for s in SKANNINGAR}
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="storm_mhn", namn="Monumenta historica Norvegiæ (Storm 1880, OCR ur Internet Archive)",
            utgivare="Internet Archive (skanning: Google Books)",
            url="https://archive.org/details/monumentahistor01storgoog",
            licens=LICENS, version="djvu.txt"),
        verk=[])
    for verk, konf in VERK.items():
        edtf, fran, till = konf["datering"]
        paket.verk.append(Verk(
            id=konf["verk_id"], titel=konf["titel"], upphov=konf["upphov"], genre="kronika", sprak=["lat"],
            datering_edtf=edtf, datering_fran=fran, datering_till=till, beskrivning=konf["beskrivning"],
            extern_url=konf["extern_url"]))
        utgava_id = f"utgava:{verk}:storm1880"
        paket.utgavor.append((konf["verk_id"], Utgava(
            utgava_id, f"{UTGAVA_REFERENS}. OCR ur Internet Archive ({', '.join(SKANNINGAR)}), "
                       "rensad från apparat, kommentar och sidhuvuden.", LICENS)))
        delar, texter = tolka_verk(verk, skanningar)
        for ordning, d in enumerate(delar, 1):
            text = texter[d.nyckel]
            if d.rubrik:
                text = f"{d.rubrik}\n{text}"
            paket.passager.append((konf["verk_id"], Passage(
                id=f"{verk}:{d.nyckel}", typ="originaltext", adress=_adress(verk, d), sprak="lat",
                text=text, ordning=ordning, utgava_id=utgava_id)))
        log.info("%-20s %3d passager, %7d tecken", verk, len(delar), sum(len(t) for t in texter.values()))
    for fil in sorted(OVERSATTNINGAR.glob("*.json")):
        paket.lagg_till_maskinoversattningar(fil, "latinet")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    if arg.torr:
        for _, p in paket.passager:
            log.info("%-26s %-60s %6d tecken", p.id, p.adress, len(p.text))
    else:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

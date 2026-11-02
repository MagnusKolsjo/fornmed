"""
Tolk för MGH-utgåvor ur openMGH (TEI-XML, CC BY 4.0).

Utgåvorna är OCR av de tryckta MGH-banden med sid- och radbrytningar men
utan märkt kapitelindelning. Kapitlen tas fram ur radinledande nummer
(romerska eller arabiska); utgåvor utan kapitelnummer i texten delas per
MGH-sida. Passagens adress anger bok, kapitel och MGH-sidor.

Användning:
    python -m tolkar.openmgh            # alla verk i VERK
    python -m tolkar.openmgh --torr     # tolka och visa statistik
"""

import argparse
import difflib
import html
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

log = logging.getLogger("tolkar.openmgh")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "openmgh"
BAS_URL = "https://data.mgh.de/openmgh"
TEI = "{http://www.tei-c.org/ns/1.0}"
ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

# Största godtagna lucka i kapitelnumreringen (se kapitel()). OCR:en tappar
# ibland flera kapitelnummer i rad (Gregorius VIII: 11, 13, 18, 20, 24),
# medan felaktiga radinledande tal ligger långt utanför följden (LVIII efter XIX)
MAX_LUCKA = 8

# Kapitel som OCR:en tappat numret på letas upp med hjälp av en annan utgåva
# med fullständig kapitelindelning: kapitlets första ord söks i texten mellan
# de kapitel som hittats. The Latin Library har Gregorius av Tours.
# Banden i dMGH (MGH:s digitala utgåvor med sidbilder); passagens första
# MGH-sida ger en länk till sidbilden
DMGH = {"verk:adam_av_bremen": "mgh_ss_rer_germ_2", "verk:vita_anskarii": "mgh_ss_rer_germ_55",
        "verk:jordanes_getica": "mgh_auct_ant_5_1", "verk:historia_francorum": "mgh_ss_rer_merov_1_1",
        "verk:liber_historiae_francorum": "mgh_ss_rer_merov_2"}


def dmgh_lank(verk_id: str, sida) -> str | None:
    """Länk till en sida i dMGH:s visning av bandet, t.ex. …/index.htm#page/(73)/mode/1up."""
    if verk_id not in DMGH or not sida:
        return None
    return f"https://www.dmgh.de/{DMGH[verk_id]}/index.htm#page/({sida})/mode/1up"


LATIN_LIBRARY = {"verk:historia_francorum": "https://www.thelatinlibrary.com/gregorytours/gregorytours{bok}.shtml"}
ROMERSKA_BOCKER = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}


@dataclass
class VerkKonfig:
    bsb: str                 # openMGH-filens id
    work: str                # värdet på <div type="work" n="…">
    verk_id: str
    titel: str
    upphov: str | None
    genre: str
    datering: tuple[str, int, int]
    beskrivning: str
    indelning: str           # 'romersk', 'arabisk', 'ar' (annaler), 'monster' eller 'sida'
    delar: list[str | None]  # etikett per <div type="part">, None = hoppa över
    # För indelning 'monster': kapitelrubrikens mönster med kapitelnumret (romerskt
    # eller arabiskt) i grupp 1, t.ex. Helmolds "De civitate Vinneta. Cap. II."
    kapitelmonster: str | None = None
    # Delar som rymmer flera böcker delas vid detta mönster; grupp 1 är bokens etikett
    bokmonster: str | None = None
    # Benämningen av delarna och kapitlen i adressen (Henrik av Lettland: "kap. XXIV, § 2")
    bokord: str = "bok"
    kapitelord: str = "kap."


VERK = [
    VerkKonfig("bsb00000756", "Adami gesta Hamm. eccl. pont.", "verk:adam_av_bremen",
               "Gesta Hammaburgensis ecclesiae pontificum", "Adam av Bremen", "kronika",
               ("1073/1081", 10730101, 10811231),
               "Hamburg-Bremens kyrkohistoria; bok IV (Descriptio insularum aquilonis) beskriver "
               "Norden, bl.a. Uppsala och svearna. Utgåvans skolier återges inte i openMGH-texten.",
               "romersk", ["prolog", "I", "II", "III", "IV", "epilog"]),
    VerkKonfig("bsb00000703", "Vita Anskarii", "verk:vita_anskarii", "Vita Anskarii", "Rimbert",
               "legend", ("0865/0876", 8650101, 8761231),
               "Rimberts levnadsteckning över Ansgar, med skildringen av missionen hos svearna i Birka.",
               "arabisk", [None, "text"]),
    VerkKonfig("bsb00000792", "Iordanis Getica", "verk:jordanes_getica", "De origine actibusque Getarum",
               "Jordanes", "kronika", ("0551", 5510101, 5511231),
               "Goternas historia; kapitel 3 beskriver Scandza och dess folk, bl.a. suehans.",
               "sida", ["text"]),
    VerkKonfig("bsb00000747", "Greg. Tur. hist.", "verk:historia_francorum",
               "Historia Francorum (Decem libri historiarum)", "Gregorius av Tours", "kronika",
               ("0575/0594", 5750101, 5941231),
               "Frankisk krönika, skriven inom ett halvsekel efter Hygelacs räd.",
               "arabisk", ["prefatio", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]),
    VerkKonfig("bsb00000749", "Lib. hist. Franc.", "verk:liber_historiae_francorum",
               "Liber historiae Francorum", None, "kronika", ("0727", 7270101, 7271231),
               "Frankisk krönika som i sina tidiga delar bygger på Gregorius.",
               "arabisk", ["text"]),
    VerkKonfig("bsb00000759", "Ann. reg. Franc.", "verk:annales_regni_francorum", "Annales regni Francorum",
               None, "annal", ("0787/0829", 7870101, 8291231),
               "Frankiska rikets officiella annaler 741–829, förda vid hovet; om danakungarna Godfred och "
               "Horik, Hedeby (Sliesthorp), Danevirke och sändebud från Norden.",
               "ar", ["text"]),
    VerkKonfig("bsb00000758", "Ann. Bert.", "verk:annales_bertiniani", "Annales Bertiniani", None, "annal",
               ("0830/0882", 8300101, 8821231),
               "Västfrankiska annaler 830–882 (del II av Prudentius av Troyes, del III av Hinkmar av Reims). "
               "Under år 839 sändebuden från Rhos som visar sig vara svear (Sueones).",
               "ar", ["I", "II", "III"]),
    VerkKonfig("bsb00000760", "Ann. Fuld.", "verk:annales_fuldenses", "Annales Fuldenses", None, "annal",
               ("0838/0901", 8380101, 9011231),
               "Östfrankiska annaler 714–901 i flera delar och fortsättningar; om nordmännens härjningar "
               "och danska kungar.",
               "ar", ["I", "II", "III", "IV", "V"]),
    VerkKonfig("bsb00000764", "Ann. Xant.", "verk:annales_xantenses", "Annales Xantenses", None, "annal",
               ("0832/0874", 8320101, 8741231),
               "Annaler från Nedre Rhen 790–874, med nordmännens anfall på Dorestad och Hamburg. "
               "Det sena supplementet för åren 640–789 tas inte med.",
               "ar", ["text", None]),
    VerkKonfig("bsb00000764", "Ann. Vedast.", "verk:annales_vedastini", "Annales Vedastini", None, "annal",
               ("0874/0900", 8740101, 9001231),
               "Annaler från S:t Vaast i Arras 874–900, framför allt om nordmännens härjningar i "
               "Västfrankerriket.",
               "ar", ["text"]),
    VerkKonfig("bsb00000728", "Einhardi Vita Karoli", "verk:einhard_vita_karoli", "Vita Karoli Magni",
               "Einhard", "kronika", ("0817/0833", 8170101, 8331231),
               "Karl den stores levnadsteckning; om kriget mot danakungen Godfred.",
               "arabisk", ["prolog", "text"]),
    VerkKonfig("bsb00000712", "Theganus", "verk:thegan_gesta_hludowici", "Gesta Hludowici imperatoris",
               "Thegan", "kronika", ("0836/0837", 8360101, 8371231),
               "Ludvig den frommes historia; om Harald Klaks dop i Ingelheim 826.",
               "monster", [None, None, "text", "fortsattning"],
               kapitelmonster=r"(?m)^(?:\x01[^\x01]*\x01)?\s*\[([IVXLC]+)L?\.\]"),
    VerkKonfig("bsb00000712", "Astronomus", "verk:astronomus_vita_hludowici", "Vita Hludowici imperatoris",
               "Astronomus", "kronika", ("0840/0841", 8400101, 8411231),
               "Ludvig den frommes levnadsteckning av den anonyme 'Astronomus'; om dansk tronstrid och "
               "Harald Klak.",
               "monster", ["text"], kapitelmonster=r"(?m)^(?:\x01[^\x01]*\x01)?\s*\[([IVXLC]+)L?\.\]"),
    VerkKonfig("bsb00000708", "Wid. Rer. gest. Sax.", "verk:widukind", "Res gestae Saxonicae",
               "Widukind av Corvey", "kronika", ("0967/0973", 9670101, 9731231),
               "Sachsarnas historia; bok III berättar om Harald Blåtands dop genom prästen Poppo.",
               "romersk", ["I", "II", "III"]),
    VerkKonfig("bsb00000689", "Chron. Thiet.", "verk:thietmar", "Chronicon", "Thietmar av Merseburg",
               "kronika", ("1012/1018", 10120101, 10181231),
               "Krönika om de ottoniska kungarna; bok I beskriver offren i Lejre, och verket berättar om "
               "danska kungar och Knut den store. Utgåvan trycker Dresdenhandskriften och Corvey"
               "bearbetningen på motstående sidor; passagerna innehåller båda versionerna där de finns.",
               "arabisk", ["text"], bokmonster=r"(?m)^(?:\x01[^\x01]*\x01)?\s*LIBER\s+([IVX]+)\."),
    VerkKonfig("bsb00000735", "Helmoldi Chron. Slav.", "verk:helmold", "Chronica Slavorum",
               "Helmold av Bosau", "kronika", ("1163/1172", 11630101, 11721231),
               "Slavernas krönika; om venderna, Östersjön, Ansgars mission i Sverige och danska kungar. "
               "OCR-texten saknar kapitelrubriker; passagerna följer MGH-sidorna.",
               "sida", ["prolog", "I", "II"]),
    VerkKonfig("bsb00000734", "Chron. Liv.", "verk:henrik_av_lettland", "Chronicon Livoniae",
               "Henrik av Lettland", "kronika", ("1225/1227", 12250101, 12271231),
               "Den livländska krönikan 1180–1227; om svenskarnas tåg till Estland och slaget vid Lihula 1220.",
               "monster", ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
                           "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV",
                           "XXV", "XXVI", "XXVII", "XXVIII", "XXIX", "XXX"],
               kapitelmonster=r"\((\d{1,2})\)", bokord="kap.", kapitelord="§"),
    VerkKonfig("bsb00000858", "Pauli hist. Lang.", "verk:paulus_diaconus", "Historia Langobardorum",
               "Paulus Diaconus", "kronika", ("0787/0796", 7870101, 7961231),
               "Langobardernas historia; bok I om langobardernas ursprung i Scadanan och om skridfinnarna.",
               "arabisk", ["I", "II", "III", "IV", "V", "VI", None]),
]


def romersk(tal: str) -> int:
    varden = [ROMERSKA[t] for t in tal]
    return sum(-v if i + 1 < len(varden) and v < varden[i + 1] else v for i, v in enumerate(varden))


def hamta(bsb: str) -> Path:
    """Laddar ner och packar upp en openMGH-utgåva om den saknas lokalt."""
    xml = KATALOG / bsb / f"{bsb}.xml"
    if not xml.exists():
        zip_ = KATALOG / f"{bsb}.zip"
        zip_.parent.mkdir(parents=True, exist_ok=True)
        if not zip_.exists():
            log.info("Hämtar %s/%s.zip", BAS_URL, bsb)
            urllib.request.urlretrieve(f"{BAS_URL}/{bsb}.zip", zip_)
        with zipfile.ZipFile(zip_) as z:
            z.extractall(KATALOG / bsb)
    return xml


def text_med_sidor(element) -> str:
    """
    Elementets text i dokumentordning med sidbrytningar som markörer
    \\x01sidnr\\x01. Avstavning över radbrytning slås ihop.
    """
    delar: list[str] = []

    def gå(e):
        if e.tag == f"{TEI}pb":
            delar.append(f"\x01{(e.get('n') or '').strip('()')}\x01")
        if e.text:
            delar.append(e.text)
        for barn in e:
            gå(barn)
            if barn.tail:
                delar.append(barn.tail)

    gå(element)
    text = "".join(delar)
    return re.sub(r"(\w)-\n(?=\w)", r"\1", text)


def _rensa(text: str) -> str:
    """Löptext utan sidmarkörer; sidnumren finns i passagens adress."""
    return re.sub(r"\s+", " ", re.sub(r"\x01[^\x01]*\x01", " ", text)).strip()


def _sidor(text: str, sida_fore: str | None) -> tuple[str | None, str | None]:
    """Första och sista sida ett textavsnitt ligger på, givet sidan där det börjar."""
    i_texten = re.findall(r"\x01([^\x01]*)\x01", text)
    forsta = sida_fore if not text.lstrip().startswith("\x01") else (i_texten[0] if i_texten else sida_fore)
    sista = i_texten[-1] if i_texten else forsta
    return forsta, sista


def kapitel(text: str, indelning: str) -> list[tuple[int, int, int]]:
    """
    Kapitlens (nummer, start, slut) i en del. Kapitelnummer står först på
    en rad. Ett nummer godtas om det ligger högst MAX_LUCKA över föregående,
    eftersom OCR:en tappar enstaka kapitelnummer; lägre eller mycket högre
    tal är radinledande tal i texten eller noterna och hoppas över. När
    numreringen börjar om bildas en ny serie; den serie som täcker mest
    text väljs, vilket sållar bort kapitelförteckningar.
    """
    monster = r"(?m)^\s*([IVXLC]+)\.\s" if indelning == "romersk" else r"(?m)^\s*\(?(\d{1,3})\)?\.\s"
    serier: list[list[tuple[int, int]]] = []
    for m in re.finditer(monster, text):
        nr = romersk(m.group(1)) if indelning == "romersk" else int(m.group(1))
        if serier and serier[-1][-1][0] < nr <= serier[-1][-1][0] + MAX_LUCKA:
            serier[-1].append((nr, m.start()))
        elif nr in (1, 2):
            serier.append([(nr, m.start())])
    if not serier:
        return []

    def omfang(s):
        return len(text) - s[0][1] if s is serier[-1] else serier[serier.index(s) + 1][0][1] - s[0][1]

    basta = max(serier, key=omfang)
    slut_ = len(text) if basta is serier[-1] else serier[serier.index(basta) + 1][0][1]
    return [(nr, start, basta[i + 1][1] if i + 1 < len(basta) else slut_)
            for i, (nr, start) in enumerate(basta)]


def langsta_folj(kandidater: list[tuple[int, int]], max_steg: int) -> list[tuple[int, int]]:
    """Den längsta följden av (nummer, position) med stigande nummer, högst max_steg mellan två."""
    langd = [1] * len(kandidater)
    forra = [-1] * len(kandidater)
    for i, (nr, _) in enumerate(kandidater):
        for j in range(i):
            if kandidater[j][0] < nr <= kandidater[j][0] + max_steg and langd[j] + 1 > langd[i]:
                langd[i], forra[i] = langd[j] + 1, j
    ut: list[tuple[int, int]] = []
    i = max(range(len(kandidater)), key=lambda k: langd[k]) if kandidater else -1
    while i >= 0:
        ut.append(kandidater[i])
        i = forra[i]
    return ut[::-1]


def arsindelning(text: str, efter: int | None = None) -> list[tuple[int, int, int]]:
    """
    Annalernas år som (år, start, slut). Utgåvorna sätter årtalet på en egen
    rad ("861.") eller inleder året med "DCCXV.", "Anno DCCCXLVI.", "Anno Domini
    865." eller "Anno dominicae incarnationis DCCXLI." först på raden. Åren tas
    som den längsta följden av stigande årtal med högst 30 år mellan två, så att
    tal i noterna och löptexten inte tas för årtal. En fortsättning börjar
    tidigast fem år före det sista året i föregående del (efter).
    """
    monster = (r"(?mi)^(?:\x01[^\x01]*\x01)?\s*(?:(\d{3,4})\.(?=\s*$|\s+anno)|"
               r"(?:anno\s+(?:domini\s+|ab\s+incarnatione\s+domini\s+|(?:dominicae|dominice)\s+incarnationis\s+|"
               r"incarnationis\s+(?:dominicae|eius)\s+)?)?"
               r"(?:([DCLXVIM]{3,})|(?<=\s)(\d{3,4}))[.,]?(?=\s))")
    kandidater: list[tuple[int, int]] = []
    for m in re.finditer(monster, text):
        ar = int(m.group(1) or m.group(3)) if (m.group(1) or m.group(3)) else romersk(m.group(2).upper())
        if 400 <= ar <= 1400 and (efter is None or ar > efter - 5):
            kandidater.append((ar, m.start()))
    # Ett enstaka felläst årtal ska inte kunna stänga ute de följande åren
    starter = langsta_folj(kandidater, 30)
    return [(ar, start, starter[i + 1][1] if i + 1 < len(starter) else len(text))
            for i, (ar, start) in enumerate(starter)]


def monsterindelning(text: str, monster: str) -> list[tuple[int, int, int]]:
    """
    Kapitel efter ett eget rubrikmönster: den längsta följden av stigande
    kapitelnummer (högst MAX_LUCKA i taget), så att hänvisningar i noterna
    inte bryter följden. Följden får börja på vilket nummer som helst,
    eftersom bok II kan fortsätta bok I:s numrering.
    """
    kandidater: list[tuple[int, int]] = []
    for m in re.finditer(monster, text):
        # OCR:en läser ibland "VIIII." som "VIIIL."
        tal = re.sub(r"(?<=I)L$", "", m.group(1))
        if tal:
            kandidater.append((romersk(tal) if tal.isalpha() else int(tal), m.start()))
    # Fyra eller fler rubriker i följd med mindre än 200 tecken emellan är en
    # kapitelförteckning, inte kapitel med text (enstaka korta kapitel finns)
    tata = [i + 1 < len(kandidater) and kandidater[i + 1][1] - k[1] < 200 for i, k in enumerate(kandidater)]
    i, bort = 0, set()
    while i < len(tata):
        j = i
        while j < len(tata) and tata[j]:
            j += 1
        if j - i >= 4:
            bort.update(range(i, j + 1))
        i = j + 1
    kandidater = [k for i, k in enumerate(kandidater) if i not in bort]
    starter = langsta_folj(kandidater, MAX_LUCKA)
    return [(nr, start, starter[i + 1][1] if i + 1 < len(starter) else len(text))
            for i, (nr, start) in enumerate(starter)]


def bokdelning(etikett: str, text: str, monster: str) -> list[tuple[str, str]]:
    """Delar en del som rymmer flera böcker; text före första boken går till den första boken."""
    traffar = list(re.finditer(monster, text))
    if not traffar:
        return [(etikett, text)]
    ut = []
    for i, m in enumerate(traffar):
        start = 0 if i == 0 else m.start()
        slut_ = traffar[i + 1].start() if i + 1 < len(traffar) else len(text)
        ut.append((m.group(1), text[start:slut_]))
    return ut


def _ord(text: str) -> list[tuple[str, int]]:
    """Textens ord i jämförelseform med sin position: gemener, u för v, i för j."""
    return [(m.group(0).lower().replace("v", "u").replace("j", "i"), m.start())
            for m in re.finditer(r"[A-Za-zÆæŒœ]+", text)]


def kapitelinledningar(verk_id: str, bok: str) -> dict[int, list[str]]:
    """De första orden i varje kapitel enligt jämförelseutgåvan, efter kapitelrubriken."""
    if verk_id not in LATIN_LIBRARY or bok not in ROMERSKA_BOCKER:
        return {}
    fil = KATALOG.parent / "latinlibrary" / f"{verk_id.split(':')[1]}_{ROMERSKA_BOCKER[bok]}.html"
    if not fil.exists():
        fil.parent.mkdir(parents=True, exist_ok=True)
        # Sajten avvisar anrop utan webbläsarlik User-Agent
        req = urllib.request.Request(LATIN_LIBRARY[verk_id].format(bok=ROMERSKA_BOCKER[bok]),
                                     headers={"User-Agent": "Mozilla/5.0 (fornmed-forskningsdatabas)"})
        fil.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    text = html.unescape(re.sub(r"<[^>]+>", " ", fil.read_text(encoding="latin-1")))
    text = re.sub(r"\s+", " ", text)
    delar = re.split(r"\s(\d{1,2})\.\s+(?=[A-Z])", text)
    ut: dict[int, list[str]] = {}
    for nr, stycke in zip(delar[1::2], delar[2::2]):
        # Rubriken slutar med den första punkten; texten börjar efter den
        brodtext = stycke.split(". ", 1)[1] if ". " in stycke else stycke
        ut[int(nr)] = [o for o, _ in _ord(brodtext)[:6]]
    return ut


def fyll_luckor(text: str, kap: list[tuple[int, int, int]],
                inledningar: dict[int, list[str]]) -> list[tuple[int, int, int]]:
    """
    Lägger in kapitel som saknas mellan två funna kapitel, där jämförelse-
    utgåvans kapitelinledning finns i texten (ordlikhet minst 0,75 för de
    sex första orden).
    """
    if not kap or not inledningar:
        return kap
    starter = [(nr, start) for nr, start, _ in kap]
    tillagda = []
    for (nr_a, start_a), (nr_b, start_b) in zip(starter, starter[1:] + [(None, len(text))]):
        hi = nr_b if nr_b is not None else max(inledningar) + 1
        ord_ = _ord(text[start_a:start_b])
        sok_fran = 1
        for saknad in range(nr_a + 1, hi):
            mal = inledningar.get(saknad)
            if not mal:
                continue
            basta, pos = 0.0, None
            for i in range(sok_fran, max(sok_fran, len(ord_) - len(mal)) + 1):
                kvot = difflib.SequenceMatcher(None, " ".join(mal), " ".join(o for o, _ in ord_[i:i + len(mal)])).ratio()
                if kvot > basta:
                    basta, pos = kvot, i
            if basta >= 0.75 and pos is not None:
                tillagda.append((saknad, start_a + ord_[pos][1]))
                sok_fran = pos + 1
    if not tillagda:
        return kap
    alla = sorted(starter + tillagda, key=lambda x: x[1])
    slut_ = kap[-1][2]
    return [(nr, start, alla[i + 1][1] if i + 1 < len(alla) else slut_) for i, (nr, start) in enumerate(alla)]


def tolka_verk(konf: VerkKonfig) -> tuple[Verk, Utgava, list[Passage]]:
    rot = ET.parse(hamta(konf.bsb)).getroot()
    rubrik = rot.find(f".//{TEI}titleStmt/{TEI}title")
    redaktorer = [e.text.strip() for e in rot.iter(f"{TEI}editor") if e.text and e.text.strip()]
    ar = next((e.text for e in rot.iter(f"{TEI}date") if e.text), None)
    work = next(w for w in rot.iter(f"{TEI}div") if w.get("type") == "work" and w.get("n") == konf.work)
    delar = work.findall(f"{TEI}div") or [work]

    utgava_id = f"utgava:{konf.verk_id.split(':', 1)[1]}:openmgh"
    referens = (f"{', '.join(dict.fromkeys(redaktorer)) + ' (utg.), ' if redaktorer else ''}"
                f"{rubrik.text.strip() if rubrik is not None else konf.titel}"
                f"{', ' + ar if ar else ''}. openMGH {konf.bsb}.")
    utgava = Utgava(utgava_id, referens, "CC BY 4.0 (MGH/BSB); texten public domain")

    passager: list[Passage] = []
    sida = None
    ordning = 0
    texter: list[tuple[str | None, str]] = []
    for etikett, del_ in zip(konf.delar + [None] * (len(delar) - len(konf.delar)), delar):
        text = text_med_sidor(del_)
        if konf.bokmonster and etikett is not None:
            texter += bokdelning(etikett, text, konf.bokmonster)
        else:
            texter.append((etikett, text))
    sista_ar = None
    for etikett, text in texter:
        if etikett is None:
            sida = _sidor(text, sida)[1]
            continue
        if konf.indelning == "sida":
            # En passage per MGH-sida
            bitar = re.split(r"\x01([^\x01]*)\x01", text)
            for i in range(0, len(bitar), 2):
                innehall = _rensa(bitar[i])
                if innehall:
                    ordning += 1
                    passager.append(Passage(
                        # En sida kan delas mellan två delar (Helmolds prolog och bok I)
                        id=f"{konf.verk_id.split(':', 1)[1]}:" + ("" if etikett == "text" else
                           re.sub(r"[^a-z0-9]+", "_", etikett.lower()) + ":") + f"s{sida}", typ="originaltext",
                        adress=("" if etikett == "text" else "prolog, " if etikett == "prolog"
                                else f"bok {etikett}, ") + f"MGH s. {sida}", sprak="lat", text=innehall, ordning=ordning,
                        utgava_id=utgava_id, url=dmgh_lank(konf.verk_id, sida)))
                if i + 1 < len(bitar):
                    sida = bitar[i + 1]
            continue
        if konf.indelning == "ar":
            kap = arsindelning(text, sista_ar)
            sista_ar = kap[-1][0] if kap else sista_ar
        elif konf.indelning == "monster":
            kap = monsterindelning(text, konf.kapitelmonster)
        else:
            kap = fyll_luckor(text, kapitel(text, konf.indelning), kapitelinledningar(konf.verk_id, etikett))
        bokdel = "" if etikett == "text" else f"del {etikett}, " if konf.indelning == "ar" else f"{konf.bokord} {etikett}, "
        stycken = [(None, 0, kap[0][1])] + kap if kap else [(None, 0, len(text))]
        for nr, start, slut in stycken:
            avsnitt = text[start:slut]
            forsta, sista = _sidor(avsnitt, sida)
            sida = sista
            innehall = _rensa(avsnitt)
            if not innehall or (nr is None and len(innehall) < 40):
                continue
            ordning += 1
            del_id = re.sub(r"[^a-z0-9]+", "_", etikett.lower()).strip("_")
            sidtext = f"MGH s. {forsta}" + (f"–{sista}" if sista and sista != forsta else "")
            if nr is None:
                pid, adress = f"{del_id}:inledning", f"{bokdel}inledning ({sidtext})"
            else:
                enhet = "år" if konf.indelning == "ar" else konf.kapitelord
                pid, adress = f"{del_id}:{nr}", f"{bokdel}{enhet} {nr} ({sidtext})"
            passager.append(Passage(
                id=f"{konf.verk_id.split(':', 1)[1]}:{pid}", typ="originaltext",
                adress=adress.replace("bok prolog, inledning", "prolog").replace(
                    "bok epilog, inledning", "epilog"),
                sprak="lat", text=innehall, ordning=ordning, utgava_id=utgava_id,
                url=dmgh_lank(konf.verk_id, forsta)))

    verk = Verk(id=konf.verk_id, titel=konf.titel, upphov=konf.upphov, genre=konf.genre, sprak=["lat"],
                datering_edtf=konf.datering[0], datering_fran=konf.datering[1],
                datering_till=konf.datering[2], beskrivning=konf.beskrivning,
                extern_url=f"https://data.mgh.de/openmgh/{konf.bsb}.zip")
    return verk, utgava, passager


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="openmgh", namn="Monumenta Germaniae Historica, openMGH",
            utgivare="Monumenta Germaniae Historica; Bayerische Staatsbibliothek",
            url="https://mgh.de/en/digital-mgh/openmgh", licens="CC BY 4.0", version="2016"),
        verk=[])
    for konf in VERK:
        verk, utgava, passager = tolka_verk(konf)
        paket.verk.append(verk)
        paket.utgavor.append((verk.id, utgava))
        paket.passager += [(verk.id, p) for p in passager]
        kap = [p for p in passager if ":inledning" not in p.id]
        log.info("%-36s %4d passager (%s … %s)", verk.titel[:36], len(passager),
                 kap[0].adress if kap else "–", kap[-1].adress if kap else "–")
    for fil in sorted((Path(__file__).parent.parent / "data" / "oversattningar" / "openmgh").glob("*.json")):
        paket.lagg_till_maskinoversattningar(fil, "latinet")
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

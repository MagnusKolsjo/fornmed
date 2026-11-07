"""
Regelbaserade påståenden ur SDHK:s och Diplomatarium Fennicums utfärdarfält och regester.

Utfärdarfältet är arkivets moderna registeruppgift om vem som utfärdade
brevet, t.ex. "Biskop Knut i Linköping" eller "Peter i Skeda,
häradshövding i Hanekinds härad". DF skriver fältet med namnet först ("Gustaf,
kung", "Råd, av Stockholm") och skrivs om till SDHK:s form (df_falt). DF-brev som
redan är kopplade till ett SDHK-brev läses bara ur SDHK. Ur fältet härleds tre
slags påståenden, alla daterade med brevets datum och knutna till brevets regest:

- utfardar: utfärdaren utfärdar brevet (objekt_varde = verkets id)
- innehar_ambete: en titel eller ett ämbete, med orten när den anges
- har_stand: riddare eller väpnare

Ur regesten härleds huvudgärningen (regest_garningar.py) och, för brev utan gärning,
missivets adressat och om brevet svarar på ett tidigare brev:

- skriver_till: utfärdaren skriver till adressaten (objekt_varde = verkets id)
- besvarar: brevet svarar på ett brev från objektet; värdet är det besvarade brevets
  verk-id när det har hittats (se svarskopplingar), annars regestens hänvisning

Vem ett namn avser avgörs i tre nivåer:

1. Regenter och påvar slås upp i data/auktoriteter. "Kung Magnus" blir
   Magnus Ladulås eller Magnus Eriksson beroende på brevets datum. När
   flera regenter passar (t.ex. Erik Menved och Erik Magnusson av Norge
   på 1290-talet) och fältet inte nämner riket lämnas utfärdaren okopplad.
2. Institutioner (stadsråd, kloster, riksråd) blir en entitet per ort.
3. Övriga personer slås ihop när namnet är detsamma efter normalisering,
   de delar ort eller ämbete och förekomsterna ligger inom 40 år från
   varandra. Förekomster utan ort eller ämbete får egna entiteter.
   Sammanslagningen är medvetet försiktig: det är lättare att identifiera
   två entiteter med varandra i efterhand än att dela en felaktigt hopslagen.
   DF:s brev och missivens adressater förs till SDHK:s personer men ändrar
   aldrig hur SDHK:s förekomster slås ihop (se klustra), så att inget SDHK-id
   ändras när en ny källa eller roll läses in.

Orterna slås upp bland de platser som redan finns (Platsuppslag), så att samma
ort inte får en ny entitet för varje källa. Kör platser.py efteråt: den flyttar
påståendena till den ort som avses när ett namn delas av flera platser.

Utfärdarfältet är inte ett citat ur brevet, så citatfältet lämnas tomt.
Alla påståenden registreras med extraktion = 'regel' och granskad = false.

importera_sdhk.py måste ha körts först.

Användning:
    python pastaenden_sdhk.py              # läs in
    python pastaenden_sdhk.py --rapport R  # läs in och skriv en granskningsrapport till katalogen R
    python pastaenden_sdhk.py --torr --rapport R   # bara rapporten, ingen skrivning
"""

import argparse
import json
import logging
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

import db
from normalisering import ordform
from regest_garningar import Brevform, Garning, tolka_brevform, tolka_garning

log = logging.getLogger("pastaenden_sdhk")

EXTRAHERAD_AV = "pastaenden_sdhk.py"
AUKTORITETER = Path(__file__).parent / "data" / "auktoriteter"

# Största avstånd i år mellan två förekomster som slås ihop till en person,
# och största spann för en hel sammanslagen person
MAX_GAP_AR = 40
MAX_SPANN_AR = 60
# Ett ämbete med säte (biskop i Linköping) skrivs det brev i nästan varje år;
# ett längre uppehåll betyder oftast en efterträdare med samma förnamn
MAX_GAP_AMBETE_AR = 15
MAX_SPANN_AMBETE_AR = 50

# -----------------------------------------------------------------------------
# Titlar och ämbeten
# -----------------------------------------------------------------------------
# Ordform i fältet → (kod, typ). Typen 'ambete' ger innehar_ambete, 'stand'
# ger har_stand och 'tilltal' ger inget påstående. Pluralformer fördelar
# titeln på alla namn som följer.

TITLAR: dict[str, tuple[str, str]] = {}
PLURAL: dict[str, str] = {}


def _titel(kod: str, typ: str, *former: str, plural: tuple[str, ...] = ()) -> None:
    for f in former:
        TITLAR[f] = (kod, typ)
    for f in plural:
        PLURAL[f] = kod
        TITLAR[f] = (kod, typ)


_titel("kung", "ambete", "kung", "kungen", "konung", "konungen", plural=("kungar", "kungarna"))
_titel("drottning", "ambete", "drottning", "drottningen")
_titel("hertig", "ambete", "hertig", "hertigen", plural=("hertigarna",))
_titel("hertiginna", "ambete", "hertiginna", "hertiginnan", plural=("hertiginnorna",))
_titel("jarl", "ambete", "jarl", "jarlen")
_titel("kejsare", "ambete", "kejsar", "kejsare", "kejsaren")
_titel("pave", "ambete", "påve", "påven", "påvlige")
_titel("kardinal", "ambete", "kardinal", "kardinalen", "kardinalpräst", "kardinaldiakon", "kardinalbiskop",
       plural=("kardinalerna",))
_titel("arkebiskop", "ambete", "ärkebiskop", "ärkebiskopen", "äbp", "ärkebiskp", plural=("ärkebiskoparna",))
_titel("biskop", "ambete", "biskop", "biskopen", "bp", "biskopar", plural=("biskoparna",))
_titel("riksforestandare", "ambete", "riksföreståndare", "riksföreståndaren")
_titel("marsk", "ambete", "marsk", "marsken")
_titel("drots", "ambete", "drots", "drotsen")
_titel("hovitsman", "ambete", "hövitsman", "hövitsmannen")
_titel("lagman", "ambete", "lagman", "lagmannen", plural=("lagmännen",))
_titel("underlagman", "ambete", "underlagman", "underlagmannen")
_titel("haradshovding", "ambete", "häradshövding", "häradshövdingen")
_titel("underharadshovding", "ambete", "underhäradshövding", "underhäradshövdingen")
_titel("landsdomare", "ambete", "landsdomare", "landsdomaren")
_titel("fogde", "ambete", "fogde", "fogden", plural=("fogdarna",))
_titel("underfogde", "ambete", "underfogde", "underfogden")
_titel("borgmastare", "ambete", "borgmästare", "borgmästaren", "bgm", plural=("borgmästarna",))
_titel("radman", "ambete", "rådman", "rådmannen", plural=("rådmännen",))
_titel("domprost", "ambete", "domprost", "domprosten")
_titel("prost", "ambete", "prost", "prosten")
_titel("dekan", "ambete", "dekan", "dekanen", "domdekan", "domdekanen")
_titel("arkedjakne", "ambete", "ärkedjäkne", "ärkedjäknen")
_titel("kanik", "ambete", "kanik", "kaniken", plural=("kanikerna",))
_titel("kyrkoherde", "ambete", "kyrkoherde", "kyrkoherden", "sockenpräst", "sockenprästen")
_titel("prast", "ambete", "präst", "prästen")
_titel("abbot", "ambete", "abbot", "abboten")
_titel("abbedissa", "ambete", "abbedissa", "abbedissan")
_titel("prior", "ambete", "prior", "priorn")
_titel("priorinna", "ambete", "priorinna", "priorinnan")
_titel("generalkonfessor", "ambete", "generalkonfessor", "generalkonfessorn")
_titel("kungsdomhavande", "ambete", "kungsdomhavande", "kungsdomhavanden", "domhavande")
_titel("haradsdomhavande", "ambete", "häradsdomhavande", "häradshövdingsdomhavande", "häradsdomaren", "häradsdomare")
_titel("lagmansdomhavande", "ambete", "lagmansdomhavande")
_titel("prebendat", "ambete", "prebendat", "prebendaten")
_titel("notarie", "ambete", "notarie", "notarien", "notarius")
_titel("borgare", "ambete", "borgare", "borgaren", plural=("borgarna",))
_titel("official", "ambete", "official", "officialen")
_titel("gardian", "ambete", "gardian", "gardianen")
_titel("riddare", "stand", "riddare", "riddaren", "rd", "rdr", "rid", plural=("riddarna",))
_titel("vapnare", "stand", "väpnare", "väpnaren", "vpn", "väpn", plural=("väpnarna",))
_titel("tilltal", "tilltal", "herr", "herrarna", "fru", "hustru", "jungfru", "broder", "bröderna", "syster",
       "unge", "gamle", "junker", "mäster", "magister", "doktor", "regens", "en", "den", "välborne", "ädle")

# Ämbetskod → (etikett, begreppsentitet). Varje titel och ämbete är en entitet
# med fast id, så att påståenden ur olika källor om samma ämbete går att
# länka; de som saknas i begreppsregistret skapas av skriptet utan termer.
AMBETEN = {
    "kung": ("kung", "begrepp:kung"), "drottning": ("drottning", "begrepp:drottning"), "hertig": ("hertig", "begrepp:hertig"),
    "hertiginna": ("hertiginna", "begrepp:hertiginna"), "jarl": ("jarl", "begrepp:jarl"), "kejsare": ("kejsare", "begrepp:kejsare"),
    "pave": ("påve", "begrepp:pave"), "kardinal": ("kardinal", "begrepp:kardinal"), "arkebiskop": ("ärkebiskop", "begrepp:arkebiskop"),
    "biskop": ("biskop", "begrepp:biskop"), "riksforestandare": ("riksföreståndare", "begrepp:riksforestandare"),
    "marsk": ("marsk", "begrepp:marsk"), "drots": ("drots", "begrepp:drots"),
    "hovitsman": ("hövitsman", "begrepp:hovitsman"), "lagman": ("lagman", "begrepp:lagman"),
    "underlagman": ("underlagman", "begrepp:underlagman"), "haradshovding": ("häradshövding", "begrepp:haradshovding"),
    "fogde": ("fogde", "begrepp:fogde"), "borgmastare": ("borgmästare", "begrepp:borgmastare"), "radman": ("rådman", "begrepp:radman"),
    "domprost": ("domprost", "begrepp:domprost"), "prost": ("prost", "begrepp:prost"), "dekan": ("dekan", "begrepp:dekan"),
    "arkedjakne": ("ärkedjäkne", "begrepp:arkedjakne"), "kanik": ("kanik", "begrepp:kanik"),
    "kyrkoherde": ("kyrkoherde", "begrepp:kyrkoherde"), "prast": ("präst", "begrepp:prast"), "abbot": ("abbot", "begrepp:abbot"),
    "abbedissa": ("abbedissa", "begrepp:abbedissa"), "prior": ("prior", "begrepp:prior"), "priorinna": ("priorinna", "begrepp:priorinna"),
    "generalkonfessor": ("generalkonfessor", "begrepp:generalkonfessor"), "borgare": ("borgare", "begrepp:borgare"),
    "official": ("official", "begrepp:official"), "gardian": ("gardian", "begrepp:gardian"),
    "kungsdomhavande": ("kungens domhavande", "begrepp:kungsdomhavande"), "haradsdomhavande": ("häradsdomhavande", "begrepp:haradsdomhavande"),
    "lagmansdomhavande": ("lagmansdomhavande", "begrepp:lagmansdomhavande"), "prebendat": ("prebendat", "begrepp:prebendat"),
    "notarie": ("notarie", "begrepp:notarie"), "underharadshovding": ("underhäradshövding", "begrepp:underharadshovding"),
    "landsdomare": ("landsdomare", "begrepp:landsdomare"), "underfogde": ("underfogde", "begrepp:underfogde"),
    "riddare": ("riddare", "begrepp:riddare"), "vapnare": ("väpnare", "begrepp:vapnare"),
}

STAND = {kod for kod, typ in TITLAR.values() if typ == "stand"}

# Titlar som slås upp i regentlistan i stället för att klustras
REGENTTITLAR = {"kung", "drottning", "hertig", "hertiginna", "riksforestandare"}

RIKEN = {
    "Sverige": re.compile(r"\b(av Sverige|Sveriges|Svea|svensk)", re.I),
    "Danmark": re.compile(r"\b(av Danmark|Danmarks|dansk)", re.I),
    "Norge": re.compile(r"\b(av Norge|Norges|norsk)", re.I),
}

RIKSNAMN = {"Sverige", "Norge", "Danmark", "Sveriges", "Norges", "Danmarks"}

PREPOSITIONER = {"i", "på", "av", "från", "till", "vid", "uti", "över", "för", "in"}
PARTIKLAR = {"van", "von", "de", "der", "den", "af", "zu", "deme", "dem", "la", "le", "di", "da"}
ROMERSKA = re.compile(r"^\(?([IVXL]+)\)?$")

NAMNORD = r"[A-ZÅÄÖÆØÞÉÜ][\wåäöæøþéüß\-’']*"

# -----------------------------------------------------------------------------
# Tolkning av utfärdarfältet
# -----------------------------------------------------------------------------


@dataclass
class Ambete:
    kod: str
    ort: str | None = None


@dataclass
class Utfardare:
    """En utfärdare som den står i fältet, innan identiteten är avgjord."""
    form: str                       # huvudledet som det står, utan appositioner
    titel: str | None = None        # titelkod i huvudledet
    fornamn: str | None = None
    efternamn: str | None = None    # patronymikon eller släktnamn
    ordningstal: str | None = None
    ort: str | None = None          # "i X" i huvudledet
    ambeten: list[Ambete] = field(default_factory=list)
    institution: str | None = None  # institutionens normaliserade namn
    rike: str | None = None


@dataclass
class Tolkning:
    utfardare: list[Utfardare]
    ofullstandig: bool = False      # "m.fl." eller grupper utan namn
    otolkat: list[str] = field(default_factory=list)


INSTITUTIONER = [
    (re.compile(r"^(?:sveriges|svea|danmarks|norges)\s+(?:rikes\s+)?(?:riks)?råd$", re.I), None),
    (re.compile(r"^(?:rikets|riksens)\s+råd$|^riksrådet$", re.I), None),
    (re.compile(r"^(?:rådet|råd|borgmästare och råd(?:et)?|borgmästarna och rådet|rådmännen|borgmästare, "
                r"rådmän och menighet(?:en)?)\s+i\s+(?:staden\s+)?(?P<ort>" + NAMNORD + r")$", re.I),
     "Rådet i {ort}"),
    (re.compile(r"^(?P<ort>" + NAMNORD + r")\s+(?:stad|råd)$"), "Rådet i {ort}"),
    (re.compile(r"^(?:staden|stadsrådet i)\s+(?P<ort>" + NAMNORD + r")$", re.I), "Rådet i {ort}"),
    (re.compile(r"^(?P<ort>" + NAMNORD + r")\s+kloster$"), "{ort} kloster"),
    (re.compile(r"^(?:konventet|klostret)\s+i\s+(?P<ort>" + NAMNORD + r")$", re.I), "{ort} kloster"),
    (re.compile(r"^(?:domkapitlet|kapitlet|domkapitel)\s+i\s+(?P<ort>" + NAMNORD + r")$", re.I), "Domkapitlet i {ort}"),
    (re.compile(r"^(?P<ort>" + NAMNORD + r")\s+domkapitel$"), "Domkapitlet i {ort}"),
    (re.compile(r"^(?P<ort>svenska|danska|norska)\s+(?:riks)?rådet$", re.I), "{Ort} riksrådet"),
    (re.compile(r"^rådmän(?:nen)?\s+i\s+(?P<ort>" + NAMNORD + r")$", re.I), "Rådet i {ort}"),
    (re.compile(r"^tyska ordens högmästare$", re.I), "Tyska ordens högmästare"),
]

OFULLSTANDIG = re.compile(
    r",?\s*(?:(?:\bm\.\s?fl\.?|\bmfl\b|\bmed flera\b)(?:\s+[a-zåäö]+)?|\bsamt flera\b|\boch (?:\d+|flera|många|alla) andra\b.*$"
    r"|\bsamt (?:\d+|flera) andra\b.*$)", re.I)


def _skala(s: str) -> str:
    """Tar bort citattecken och onödiga blanksteg."""
    s = re.sub(r"[”“\"»«]", "", s)
    s = re.sub(r"\bd\s?([äy])\b\.?", r"d.\1.", s)
    return re.sub(r"\s+", " ", s).strip(" ,.;")


def _dela_utanfor_parentes(s: str, monster: re.Pattern) -> list[str]:
    """Delar s på monster, men inte inuti parenteser eller hakparenteser."""
    delar, djup, start = [], 0, 0
    i = 0
    while i < len(s):
        t = s[i]
        if t in "([":
            djup += 1
        elif t in ")]":
            djup = max(0, djup - 1)
        elif djup == 0:
            m = monster.match(s, i)
            if m:
                delar.append(s[start:i])
                start = i = m.end()
                continue
        i += 1
    delar.append(s[start:])
    return [d.strip() for d in delar if d.strip()]


KOMMA = re.compile(r",\s*")
OCH = re.compile(r"\s+(?:och|samt|ok|&)\s+")


def _ord(s: str) -> list[str]:
    """Delar i ord men håller ihop parenteser."""
    return re.findall(r"\([^)]*\)|\[[^\]]*\]|\S+", s)


def _ar_titel(o: str) -> tuple[str, str] | None:
    return TITLAR.get(o.lower().strip("()[],."))


def _ser_ut_som_huvudled(s: str, fornamn: set[str]) -> bool:
    """
    Avgör om ett led efter kommatecken är en ny utfärdare eller en apposition.
    En ny utfärdare har formen [titlar] Namn [Namn …] [prep ort]; en
    apposition börjar med gemen ("fogde i Stockholm") eller med ett ord
    i genitiv före en gemen ("Sveriges marsk").
    """
    ord_ = _ord(s)
    i = 0
    while i < len(ord_) and _ar_titel(ord_[i]):
        i += 1
    if i == len(ord_):
        return False
    if not re.match(NAMNORD, ord_[i].strip("()[]")):
        return False
    resten = ord_[i + 1:]
    if not resten and i == 0:
        # Ett ensamt ord är en ny utfärdare bara om det är ett känt förnamn
        return ord_[i].strip("()[]") in fornamn
    for o in resten:
        if o.lower() in PREPOSITIONER:
            return True
        if o.startswith("(") or o.startswith("[") or re.match(NAMNORD, o) or o.lower() in PARTIKLAR \
                or ROMERSKA.match(o) or o in ("d.ä.", "d.y.", "d.ä", "d.y"):
            continue
        return False
    return True


def _tolka_ort(s: str) -> str | None:
    """Rensar en ortsfras: 'Linköping(s franciskankloster)' → 'Linköping'."""
    if not s.startswith("("):
        s = s.split("(")[0]
    # "Aska härad på herr Karl Ulfssons vägnar": ställföreträdarens huvudman hör inte till orten
    s = re.sub(r"\s+(?:på|för|å)\s+.*$", "", s) if re.search(r"vägnar|räkning", s) else s
    s = _skala(re.sub(r"\(.*?\)|\[.*?\]", "", s))
    return s or None


def _tolka_apposition(s: str, u: Utfardare) -> bool:
    """Lägger till ämbeten ur en apposition. Svarar True om något kändes igen."""
    funnet = False
    s = _skala(s.strip("()[]"))
    for led in _dela_utanfor_parentes(s, OCH):
        ord_ = _ord(led)
        if not ord_:
            continue
        # "Sveriges marsk", "Svea rikes drots": riket i genitiv först
        rike = None
        # "östgöta lagman", "östgötalagman"
        m = re.fullmatch(r"(öst|väst)(?:er)?göta\s?lagman", " ".join(ord_), re.I)
        if m:
            u.ambeten.append(Ambete("lagman", m.group(1).capitalize() + "ergötland"))
            funnet = True
            continue
        # "Sveriges marsk", "konungens domhavande": ett ord i genitiv före titeln
        if len(ord_) > 1 and ord_[0].endswith("s") and not _ar_titel(ord_[0]):
            for namn, monster in RIKEN.items():
                if monster.match(ord_[0]):
                    rike = namn
            ord_ = ord_[1:]
            if ord_ and ord_[0] == "rikes":
                ord_ = ord_[1:]
        if not ord_:
            continue
        titel = _ar_titel(ord_[0])
        if not titel or titel[1] == "tilltal":
            continue
        ort = rike
        if len(ord_) > 2 and ord_[1].lower() in PREPOSITIONER:
            ort = _tolka_ort(" ".join(ord_[2:]))
        u.ambeten.append(Ambete(titel[0], ort))
        funnet = True
    return funnet


def _ar_okand_titel(o: str, fornamn: set[str]) -> bool:
    """'Slottsfogden', 'Systrarna', 'Magistraten': ett titelord i bestämd form som inte står i titellistan."""
    return o not in fornamn and bool(re.fullmatch(r"[A-ZÅÄÖ][a-zåäö]+(?:en|arna|erna|orna|na)", o))


def _tolka_huvudled(s: str, arvd_titel: str | None, fornamn: set[str] = frozenset()) -> Utfardare | None:
    """Tolkar '[titlar] Förnamn [(Patronymikon)] [Efternamn] [prep ort]'."""
    form = _skala(s)
    ord_ = _ord(form)
    titlar = []
    i = 0
    while i < len(ord_) and (_ar_titel(ord_[i]) or (ord_[i].startswith("(") and i == 0)):
        t = _ar_titel(ord_[i])
        if t:
            titlar.append(t)
        i += 1
    namnord, ort, inskott = [], None, []
    while i < len(ord_):
        o = ord_[i]
        if o.lower() in PREPOSITIONER and i + 1 < len(ord_):
            ort = _tolka_ort(" ".join(ord_[i + 1:]))
            break
        # "Elof Djäken (häradshövding i Aska härad)": en apposition inom parentes
        if o.startswith("(") and namnord and re.match(r"\([a-zåäö]", o):
            inskott.append(o)
        else:
            namnord.append(o)
        i += 1
    # "Påven (Sixtus IV)": hela namnet är utgivarens tillägg
    if namnord and namnord[0].startswith("(") and " " in namnord[0]:
        namnord = namnord[0].strip("()").split() + namnord[1:]
    if namnord and _ar_okand_titel(namnord[0], fornamn):
        return None
    if not namnord:
        return None
    # Ett gement ord i namnledet betyder att ledet inte är ett personnamn
    # ("Cisterciensordens generalkapitel", "Svenske kungens marsk …")
    for o in namnord:
        if not (o.startswith(("(", "[")) or re.match(NAMNORD, o) or o.lower() in PARTIKLAR
                or ROMERSKA.match(o) or o in ("d.ä.", "d.y.", "d.ä", "d.y")):
            return None

    u = Utfardare(form=form)
    ambetstitlar = [t for t in titlar if t[1] != "tilltal"]
    if ambetstitlar:
        u.titel = ambetstitlar[-1][0]
    elif arvd_titel:
        u.titel = arvd_titel

    forsta = namnord[0].strip("[]")
    tillagg = []
    for o in namnord[1:]:
        r = ROMERSKA.match(o)
        if r and u.ordningstal is None:
            u.ordningstal = r.group(1)
        elif o.strip("()").rstrip(".") in ("d.ä", "d.y"):
            continue
        else:
            tillagg.append(o.strip("()[]"))
    # "F (Folke)": en initial följd av utgivarens upplösning
    if re.fullmatch(r"[A-ZÅÄÖ]\.?", forsta) and tillagg:
        forsta, tillagg = tillagg[0], tillagg[1:]
    forsta = forsta.strip("()")
    if not re.match(NAMNORD, forsta):
        return None
    u.fornamn = forsta
    tillagg = [t for t in tillagg if t and not t.endswith("?")]
    u.efternamn = " ".join(tillagg) or None
    u.ort = ort
    for t in titlar:
        if t[1] != "tilltal" and t[0] not in REGENTTITLAR | {"pave"}:
            # För ämbeten är orten ämbetets säte; för riddare och väpnare
            # är den bosättningsorten och hör bara till namnet
            u.ambeten.append(Ambete(t[0], ort if t[1] == "ambete" else None))
    for o in inskott:
        _tolka_apposition(o, u)
    if not u.ambeten and arvd_titel and arvd_titel not in REGENTTITLAR | {"pave"}:
        u.ambeten.append(Ambete(arvd_titel, ort if arvd_titel not in STAND else None))
    return u


def tolka(falt: str, fornamn: set[str]) -> Tolkning:
    """Delar utfärdarfältet i utfärdare och tolkar var och en."""
    s = _skala(falt)
    # Hakparentes eller parentes runt hela fältet: uppgiften är härledd av utgivaren
    if re.fullmatch(r"[\[(][^\[\]()]*[\])]", s):
        s = s[1:-1].strip()
    s = s.replace("?", "")
    ofullstandig = bool(OFULLSTANDIG.search(s))
    s = re.sub(r"\(\s*\)|\[\s*\]", "", OFULLSTANDIG.sub("", s))
    s = re.sub(r"\s+", " ", s).strip(" ,")
    tolkning = Tolkning([], ofullstandig)

    rike = next((namn for namn, mon in RIKEN.items() if mon.search(s)), None)
    # "De svenska hertigarna Erik och Valdemar"
    s = re.sub(r"^(?:de|den|det)\s+(?:svenska|danska|norska)\s+", "", s, flags=re.I)

    # Först kommatecken, sedan och/samt; varje led är en ny utfärdare eller en
    # apposition. Ett helt kommaled som är en institution delas inte på "och"
    # ("Borgmästare och råd i Stockholm").
    led: list[tuple[str, str]] = []   # (avgränsare, text)
    for i, k in enumerate(_dela_utanfor_parentes(s, KOMMA)):
        avgr = "start" if i == 0 else "komma"
        m = re.match(r"^(?:och|samt)\s+", k)
        if m:
            k, avgr = k[m.end():], "och"
        if _institution(k, rike):
            led.append((avgr, k))
            continue
        for j, o in enumerate(_dela_utanfor_parentes(k, OCH)):
            led.append((avgr if j == 0 else "och", o))

    arvd: str | None = None
    # En pluraltitel ('biskoparna') gäller uppräkningen fram till och med
    # dess sista led, det som inleds med och/samt; parterna därefter
    # ('Biskoparna Karl i Linköping och Israel i Västerås, Knut Jonsson')
    # ärver den inte
    for avgr, text in led:
        startar_plural = bool(text.split()) and text.split()[0].lower().strip("()[]") in PLURAL
        try:
            inst = _institution(text, rike)
            if inst:
                if inst != "-":
                    tolkning.utfardare.append(Utfardare(form=text, institution=inst[0], ort=inst[1]))
                else:
                    tolkning.otolkat.append(text)
                continue
            if text in RIKSNAMN:
                continue
            forsta_ordet = text.split()[0].lower().strip("()[]") if text.split() else ""
            if forsta_ordet in PLURAL:
                arvd = PLURAL[forsta_ordet]
                text = text.split(None, 1)[1] if len(text.split()) > 1 else ""
                if not text:
                    continue
            # "och hans hustru Helena": släktrelationen ger inget ämbete
            text = re.sub(r"^(?:hans|hennes|deras)\s+", "", text)
            ny = avgr == "start" or _ser_ut_som_huvudled(text, fornamn)
            if avgr == "och" and not ny and tolkning.utfardare:
                if _tolka_apposition(text, tolkning.utfardare[-1]):
                    continue
            if ny:
                t = _ar_titel(text.split()[0]) if text.split() else None
                if t and t[1] != "tilltal" and forsta_ordet not in PLURAL:
                    arvd_for_led = None
                else:
                    arvd_for_led = arvd
                u = _tolka_huvudled(text, arvd_for_led, fornamn)
                if u is None:
                    tolkning.otolkat.append(text)
                    continue
                # Riket i ledet självt går före riket någon annanstans i fältet
                u.rike = next((namn for namn, mon in RIKEN.items() if mon.search(text)), rike)
                tolkning.utfardare.append(u)
            elif tolkning.utfardare:
                if not _tolka_apposition(text, tolkning.utfardare[-1]):
                    # Pluralappositionen "Magnus och Håkan, kungar av Norge och Sverige"
                    m = re.match(r"^(\w+)\b", text)
                    kod = PLURAL.get(m.group(1).lower()) if m else None
                    if kod:
                        for u in tolkning.utfardare:
                            if u.titel is None:
                                u.titel = kod
                    else:
                        tolkning.otolkat.append(text)
            else:
                tolkning.otolkat.append(text)
        finally:
            if arvd and avgr == "och" and not startar_plural:
                arvd = None

    # Ett ensamt okänt ord utan titel, ort eller ämbete är sällan ett
    # personnamn ("Hansestäderna"); prövas först när appositionerna är lästa
    behall = []
    for u in tolkning.utfardare:
        if u.institution or u.efternamn or u.ambeten or u.ort or u.titel or u.fornamn in fornamn:
            behall.append(u)
        else:
            tolkning.otolkat.append(u.form)
    tolkning.utfardare = behall
    return tolkning


def _institution(text: str, rike: str | None) -> tuple[str, str | None] | str | None:
    """(namn, ort) om texten är en institution, '-' om den är en institution
    som inte går att bestämma, annars None."""
    for monster, mall in INSTITUTIONER:
        m = monster.match(text)
        if m:
            ort = m.groupdict().get("ort")
            if mall is None:
                if rike is None:
                    return "-"
                return f"{ {'Sverige': 'Svenska', 'Danmark': 'Danska', 'Norge': 'Norska'}[rike] } riksrådet", None
            return mall.format(ort=ort or "", Ort=(ort or "").capitalize()), ort
    return None


# -----------------------------------------------------------------------------
# Identitet
# -----------------------------------------------------------------------------


def _slug(s: str) -> str:
    s = ordform(s)
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


# Brevsamlingarna i den ordning de läses. Ett brev identifieras med sitt verk-id
# ('sdhk:10000', 'df:6022'). SDHK-brevens nycklar och id:n har bara numret, som
# innan DF kom till, så att inga tidigare id:n ändras.
KALLOR = {"sdhk": "SDHK", "df": "DF"}
BREVPERSON = tuple(f"person:{k}:" for k in KALLOR)


def ordning(verk: str) -> tuple[int, int]:
    kalla, nr = verk.split(":", 1)
    return list(KALLOR).index(kalla), int(nr)


def kort(verk: str) -> str:
    """Brevet i id-registrets nycklar: '10000' för SDHK, 'df6022' för DF."""
    kalla, nr = verk.split(":", 1)
    return nr if kalla == "sdhk" else f"{kalla}{nr}"


def lokalt_id(verk: str, namn: str) -> str:
    """Föreslaget id för en person som bara är känd ur breven: källa, namn och första brevet."""
    kalla, nr = verk.split(":", 1)
    return f"person:{kalla}:{_slug(namn)}:{nr}"


def pave_id(pave: dict) -> str:
    """Entitets-id för en påve i pavar.json. Motpåvar får tillträdesåret, så att
    en motpåve och en påve med samma namn och nummer hålls isär."""
    id_ = f"person:pave_{_slug(pave['namn'])}_{pave['nr'].lower()}"
    return id_ + (f"_{pave['fran']}" if pave.get("anm") else "")


def _overlappar(a1: int, a2: int, b1: int, b2: int) -> bool:
    return a1 <= b2 and b1 <= a2


# Hur brevets datering förhåller sig till kandidatens titel och liv, från
# den starkaste identifieringen till den svagaste. Brev från åren då en
# avsatt kung fortfarande titulerade sig kung, eller då en utvald tronföljare
# redan kallades kung, pekar ut en levande person; omnämnanden efter döden
# och dateringar före födelsen gör det inte lika säkert.
GRUNDER = ("under_titeln", "fore_titeln", "efter_titeln", "efter_dodsfall", "fore_fodelse")
GRUNDTEXT = {
    "under_titeln": "bar titeln vid brevets datering",
    "fore_titeln": "levde men hade ännu inte titeln",
    "efter_titeln": "levde men hade förlorat eller lämnat titeln",
    "efter_dodsfall": "var död vid brevets datering",
    "fore_fodelse": "var inte född vid brevets datering; dateringen eller identifieringen är fel",
}


@dataclass
class Identitet:
    """Utfallet av en identifiering mot auktoritetslistorna."""
    entitet: str | None
    grund: str                                    # GRUNDER, 'oklar', 'saknas' eller 'odaterad'
    kandidater: list[tuple[str, str]] = field(default_factory=list)   # (id, grund) när oklar
    motivering: str = ""
    titel: str | None = None                      # titelkoden, när den inte är huvudledets


# Namnformer som avser samma namn. Breven skriver oftast svenska former
# (Nils, Kort, Lydeke) medan biskopslistorna blandar svenska och latinska
# (Nicolaus, Conradus, Ludechinus).
NAMNGRUPPER = [
    {"Nils", "Nicolaus", "Niklis", "Nicolas", "Niels", "Nikolaus"},
    {"Lars", "Laurentius", "Laurens", "Laurencius"},
    {"Bengt", "Benedictus", "Bent"},
    {"Johannes", "Johan", "Jöns", "Hans", "Jon", "Jens", "Johann", "Joannes", "Ion"},
    {"Peter", "Petrus", "Peder", "Per"},
    {"Knut", "Canutus"},
    {"Henrik", "Henricus", "Hinricus", "Heinrich"},
    {"Magnus", "Måns"},
    {"Olof", "Olaus", "Olov", "Olavus", "Oluf", "Olav"},
    {"Erik", "Ericus"},
    {"Karl", "Carolus"},
    {"Tord", "Thordo", "Thord"},
    {"Sven", "Sveno", "Swen"},
    {"Mattias", "Mathias", "Mats", "Matthias"},
    {"Hemming", "Hemmingus", "Hemmingius"},
    {"Anders", "Andreas"},
    {"Torsten", "Thorstanus", "Thorsten"},
    {"Brynolf", "Bryniolf", "Brynjolf", "Brynolphus"},
    {"Sigge", "Siggo"},
    {"Kettil", "Catillus", "Ketil"},
    {"Jakob", "Jacobus", "Jacob"},
    {"Tomas", "Thomas"},
    {"Ingemar", "Ingemarus", "Ingmarus", "Ingmar"},
    {"Birger", "Birgerus"},
    {"Gudmund", "Gudmundus"},
    {"Gunnar", "Gunnarus"},
    {"Ragvald", "Ragvaldus", "Ragnvald"},
    {"Folke", "Fulco"},
    {"Jarler", "Jarlerius"},
    {"Kort", "Konrad", "Conrad", "Conradus", "Kurt"},
    {"Lydeke", "Ludechinus", "Ludeke"},
    {"Esger", "Asger", "Ascer"},
    {"Eskil", "Eskillus"},
    {"Vincent", "Vincens", "Vincentius"},
    {"Bo", "Boetius"},
    {"Björn", "Bero"},
    {"Stefan", "Stephanus"},
    {"Gottskalk", "Gottschalcus"},
    {"Didrik", "Theodericus"},
    {"Mikael", "Michael"},
    {"Arvid", "Arvidus"},
    {"Israel", "Israhel"},
]
_NAMNNYCKEL = {ordform(n): ordform(sorted(g)[0]) for g in NAMNGRUPPER for n in g}


def namnnyckel(namn: str) -> str:
    n = ordform(namn)
    return _NAMNNYCKEL.get(n, n)


class Regenter:
    def __init__(self) -> None:
        data = json.loads((AUKTORITETER / "regenter.json").read_text(encoding="utf-8"))
        self.personer = data["personer"]
        pdata = json.loads((AUKTORITETER / "pavar.json").read_text(encoding="utf-8"))
        self.varianter = {ordform(k): v for k, v in pdata["namnvarianter"].items()}
        for p in pdata["pavar"]:
            anm = p.get("anm")
            self.personer.append({
                "id": pave_id(p),
                "namn": f"Påven {p['namn']} {p['nr']}".rstrip() + (f" ({anm})" if anm else ""),
                "fodd": None, "dod": p.get("dod", p["till"]),
                "fornamn": [p["namn"]], "titlar": [["pave", None, p["fran"], p["till"]]],
                "ordningstal": p["nr"],
            })
        self.per_id = {p["id"]: p for p in self.personer}
        # Biskopar; en regent som också var biskop (Bengt Birgersson) får
        # biskopstiteln på sin befintliga post
        bdata = json.loads((AUKTORITETER / "biskopar.json").read_text(encoding="utf-8"))
        for b in bdata["personer"]:
            if b["id"] in self.per_id:
                self.per_id[b["id"]]["titlar"] += b["titlar"]
            else:
                self.personer.append(b)
                self.per_id[b["id"]] = b
        self.saten = {t[1] for b in bdata["personer"] for t in b["titlar"]}
        # Riken och furstendömen i titlarna. En sådan ort i fältet måste stämma
        # med kandidaten ("Hertig Johan av Bayern" är ingen mecklenburgare);
        # förläningar som Finland och Halland avgör bara mellan kandidater
        self.omraden = {self._jamforbar(r) for p in self.personer for _, r, _, _ in p["titlar"] if r}

    def entiteter(self) -> list[tuple]:
        rader = []
        for p in self.personer:
            titlar = "; ".join(
                f"{AMBETEN[t][0].capitalize()}" + (f" ({r})" if r else "") + f" {a}–{b}"
                for t, r, a, b in p["titlar"])
            liv = f"{p['fodd'] or '?'}–{p['dod'] or '?'}"
            rader.append((p["id"], "person", p["namn"], f"{titlar}; levde {liv}", p.get("wikidata")))
        return rader

    @staticmethod
    def _grund(p: dict, titel: str, rike: str | None, ar: tuple[int, int]) -> str:
        perioder = [(a, b) for t, r, a, b in p["titlar"] if t == titel and (not rike or not r or r == rike)]
        if any(_overlappar(ar[0], ar[1], a, b) for a, b in perioder):
            return "under_titeln"
        # Okänt födelseår: ingen bar en titel mer än sextio år före sitt första innehav
        fodd = p["fodd"] or (min(a for _, _, a, _ in p["titlar"]) - 60 if p["titlar"][0][0] != "pave" else None)
        if fodd and ar[1] < fodd:
            return "fore_fodelse"
        # Okänt dödsår: ingen bar en titel mer än fyrtio år efter sitt sista innehav
        dod = p["dod"] or (max(b for _, _, _, b in p["titlar"]) + 40 if p["titlar"][0][0] != "pave" else None)
        if dod and ar[0] > dod:
            return "efter_dodsfall"
        if perioder and all(ar[1] < a for a, _ in perioder):
            return "fore_titeln"
        return "efter_titeln"

    def _motivering(self, pid: str, titel: str, grund: str, ar: tuple[int, int]) -> str:
        p = self.per_id[pid]
        perioder = ", ".join(f"{a}–{b}" + (f" ({r})" if r else "")
                             for t, r, a, b in p["titlar"] if t == titel)
        brevar = str(ar[0]) if ar[0] == ar[1] else f"{ar[0]}–{ar[1]}"
        return (f"{p['namn']} ({p['fodd'] or '?'}–{p['dod'] or '?'}) bar titeln {AMBETEN[titel][0]} "
                f"{perioder}; brevet är daterat {brevar} och personen {GRUNDTEXT[grund]}.")

    @staticmethod
    def _jamforbar(text: str) -> str:
        return ordform(text).replace("ck", "k")

    def _beskrivande(self, p: dict) -> str:
        """Namn, fulla namn och titlarnas riken, för jämförelse med tillnamn och ort."""
        return self._jamforbar(" ".join([p["namn"], *p.get("fulla_namn", []),
                                         *(r for _, r, _, _ in p["titlar"] if r)]))

    @staticmethod
    def _har_ordningstal(p: dict, nr: str) -> bool:
        # Ordningstalen jämförs utan normalisering, som annars gör III till I
        if "ordningstal" in p:
            return p["ordningstal"] == nr.upper()
        text = " ".join([p["namn"], *p.get("fulla_namn", [])])
        return re.search(rf"\b{nr.upper()}\b", text) is not None

    def _rang(self, grund: str, titel: str) -> int:
        # En påve kallas inte påve före valet; ett sådant brev är feldaterat
        # eller avser en annan påve med samma namn
        if titel == "pave" and grund == "fore_titeln":
            return GRUNDER.index("fore_fodelse")
        return {"efter_titeln": 1}.get(grund, GRUNDER.index(grund))

    def identifiera(self, u: Utfardare, ar: tuple[int, int] | None) -> Identitet:
        """
        Kandidaterna är alla som någon gång bar titeln och har förnamnet.
        Ordningstal och ort i fältet måste stämma med kandidaten ("Påven
        Gregorius IX", "Hertig Albrecht av Bayern"); tillnamn avgör mellan
        kandidater som annars passar lika bra ("Kung Magnus Eriksson"). Sedan
        väljs den grupp vars förhållande till dateringen är starkast. En
        ensam kandidat i den gruppen kopplas direkt med sin grund, flera
        lämnas som alternativ.
        """
        namn = re.sub(r"[()]", "", u.fornamn or "")
        if u.titel == "pave":
            namn = self.varianter.get(ordform(namn), namn)
        namn = namnnyckel(namn)
        ortord = [o for o in self._jamforbar(re.sub(r"[()]", " ", u.ort or "")).split()
                  if len(o) > 2 and o not in {"etc", "och", "med"}]
        # Riket kan vara ärvt från en annan part i fältet ("Kungarna Erik av
        # Danmark ... och Birger av Sverige, hertig Kristoffer av Halland");
        # en egen ort väger tyngre
        rike = u.rike if not ortord or self._jamforbar(u.rike or "") in ortord else None
        kandidater = [p for p in self.personer
                      if namn in {namnnyckel(f) for f in p["fornamn"]}
                      and any(t == u.titel and (not rike or not r or r == rike) for t, r, _, _ in p["titlar"])]
        if u.ordningstal:
            kandidater = [p for p in kandidater if self._har_ordningstal(p, u.ordningstal)]
        if any(o in self.omraden for o in ortord):
            kandidater = [p for p in kandidater if any(o in self._beskrivande(p) for o in ortord)]
        for ord_ in (ortord, [o for o in self._jamforbar(re.sub(r"[()]", " ", u.efternamn or "")).split()
                              if len(o) > 2]):
            if len(kandidater) > 1 and ord_:
                smalare = [p for p in kandidater if any(o in self._beskrivande(p) for o in ord_)]
                if smalare:
                    kandidater = smalare
        if not kandidater:
            return Identitet(None, "saknas")
        if ar is None:
            if len(kandidater) == 1:
                return Identitet(kandidater[0]["id"], "odaterad")
            return Identitet(None, "oklar", [(p["id"], "odaterad") for p in kandidater])
        grunder = {p["id"]: self._grund(p, u.titel, rike, ar) for p in kandidater}
        rang = {pid: self._rang(g, u.titel) for pid, g in grunder.items()}
        urval = [pid for pid in grunder if rang[pid] == min(rang.values())]
        if len(urval) == 1:
            pid = urval[0]
            # Utan levande kandidat räcker inte titel och förnamn: ordningstal
            # eller tillnamn måste stödja att det är just den personen
            stod = bool(u.ordningstal) or any(
                o in self._beskrivande(self.per_id[pid])
                for o in self._jamforbar(re.sub(r"[()]", " ", u.efternamn or "")).split() if len(o) > 2)
            if grunder[pid] in ("under_titeln", "fore_titeln", "efter_titeln") or stod:
                return Identitet(pid, grunder[pid], motivering=self._motivering(pid, u.titel, grunder[pid], ar))
        return Identitet(None, "oklar", [(pid, grunder[pid]) for pid in urval])

    def fullt_namn(self, u: Utfardare, ar: tuple[int, int] | None) -> str | None:
        """Riksföreståndare och kungar som utfärdar med fullt namn, t.ex. 'Sten Sture'."""
        if ar is None or not u.efternamn:
            return None
        namn = ordform(f"{u.fornamn} {u.efternamn}")
        traffar = [p["id"] for p in self.personer if "verksam" in p
                   and namn in {ordform(f) for f in p["fulla_namn"]}
                   and _overlappar(ar[0], ar[1], *p["verksam"])]
        return traffar[0] if len(traffar) == 1 else None


@dataclass
class Forekomst:
    """En utfärdare i ett visst brev."""
    verk: str                            # brevets verk-id, 'sdhk:10000' eller 'df:6022'
    passage_id: str
    ar: tuple[int, int] | None
    u: Utfardare
    entitet: str | None = None
    orsak: str = ""
    identitet: Identitet | None = None
    roll: str = "utfardare"              # 'mottagare' i regestens huvudgärning, 'adressat' för ett missiv

    def nycklar(self) -> set[str]:
        """
        Ort och ämbeten som får två förekomster med samma namn att slås ihop.
        Orten i huvudledet räknas som bosättningsort bara när den inte är
        säte för ett ämbete ("Olof i Svista" men inte "Biskop Knut i Linköping").
        """
        k = set()
        ambetsorter = {a.ort for a in self.u.ambeten if a.ort}
        if self.u.ort and self.u.ort not in ambetsorter:
            k.add("ort:" + ordform(self.u.ort))
        for a in self.u.ambeten:
            k.add(f"ambete:{a.kod}:{ordform(a.ort) if a.ort else ''}")
        return k


def _forenliga(a: set[str], b: set[str]) -> str | None:
    """
    'exakt' när nycklarna delar ort eller ämbete med säte, 'ambete' när den
    ena sidan anger ett ämbete utan säte och den andra samma ämbete med
    säte ("Ärkebiskop Jakob" och "Ärkebiskop Jakob i Uppsala"), annars None.
    """
    if a & b:
        return "exakt"
    kod = lambda nycklar, utan_ort: {n.split(":")[1] for n in nycklar
                                     if n.startswith("ambete:") and (n.endswith(":") == utan_ort)}
    if kod(a, True) & kod(b, False) or kod(b, True) & kod(a, False):
        return "ambete"
    return None


def _sateskonflikt(a: set[str], b: set[str]) -> bool:
    """Samma ämbete med olika säte ("biskop i Linköping" och "biskop i Växjö")."""
    saten = defaultdict(set)
    for n in a | b:
        if n.startswith("ambete:") and not n.endswith(":"):
            _, kod, ort = n.split(":", 2)
            saten[kod].add(ort)
    return any(len(o) > 1 for o in saten.values())


def _bara_ambeten(a: set[str], b: set[str]) -> bool:
    """Sant när likheten bara vilar på ämbeten med säte, inte på bosättningsort eller stånd."""
    gemensamt = a & b
    return bool(gemensamt) and all(n.startswith("ambete:") and not n.endswith(":")
                                   and n.split(":")[1] not in STAND for n in gemensamt)


def _biskopsambete(u: Utfardare, saten: set[str]) -> tuple[str, str | None] | None:
    """(biskop|arkebiskop, säte) när utfärdaren är biskop på ett säte i listan eller utan säte."""
    if u.titel in ("biskop", "arkebiskop"):
        ort = u.ort
        kod = u.titel
    else:
        a = next((a for a in u.ambeten if a.kod in ("biskop", "arkebiskop")), None)
        if a is None:
            return None
        kod, ort = a.kod, a.ort
    if ort is None:
        return kod, None
    sate = next((s for s in saten if ordform(s) == ordform(ort) or ordform(ort).startswith(ordform(s))), None)
    return (kod, sate) if sate else None


def klustra(forekomster: list[Forekomst]) -> None:
    """
    Slår ihop förekomster av samma person (nivå 3). Förekomsterna gås igenom
    i tidsordning per förnamn. En förekomst förs till en tidigare person när

    - efternamnen stämmer, eller den ena sidan saknar efternamn,
    - de delar ort eller ämbete (se _forenliga),
    - personen inte redan har samma ämbete med ett annat säte,
    - förekomsten ligger högst MAX_GAP_AR efter personens senaste (högst
      MAX_GAP_AMBETE_AR när likheten bara vilar på ett ämbete) och
      personens hela spann blir högst MAX_SPANN_AR (MAX_SPANN_AMBETE_AR).

    Passar flera personer väljs en exakt ortsträff före en ämbetsträff och
    därefter den närmaste i tid; är det fortfarande oavgjort blir förekomsten
    en egen person. Förekomster utan ort, ämbete eller datum blir alltid egna personer.

    Förekomsterna läses i faser (FASER). SDHK:s utfärdare och mottagare klustras först
    och för sig, precis som innan någon annan källa fanns; DF:s brev och missivens
    adressater kan sedan föras till en person ur SDHK men aldrig slå ihop eller dela
    SDHK:s personer. Så ändras inget tidigare id av att en ny källa eller en ny roll
    läses in, och samma person får inte en ny entitet i den nya källan.
    """
    egna_per_fornamn: dict[str, list[dict]] = defaultdict(list)
    for fas in FASER:
        per_fornamn: dict[str, list[Forekomst]] = defaultdict(list)
        for f in forekomster:
            if _fas(f) == fas:
                per_fornamn[ordform(f.u.fornamn)].append(f)
        for namn, lista in per_fornamn.items():
            _klustra_fornamn(lista, egna_per_fornamn[namn], slaktnamn=fas != FASER[0])
    personer = [p for egna in egna_per_fornamn.values() for p in egna]
    _namnge(personer)


# Klustringens faser: (roll, källa). En senare fas ändrar aldrig en tidigare fas personer.
FASER = [(0, "sdhk"), (0, "df"), (1, "sdhk"), (1, "df")]


def _fas(f: "Forekomst") -> tuple[int, str]:
    return (1 if f.roll == "adressat" else 0, f.verk.split(":", 1)[0])


PATRONYMIKON = re.compile(r"(?:son|sen|sön|dot+er|dottir)$")


def _klustra_fornamn(lista: list[Forekomst], egna: list[dict], slaktnamn: bool = False) -> None:
    """
    För förekomster med samma förnamn till personerna i egna eller till nya personer där.
    Avstånd och spann räknas åt båda hållen, eftersom en senare källas brev kan vara
    äldre än personens förekomster i SDHK.

    Med slaktnamn förs också en förekomst utan ort och ämbete till en person, när den
    har ett släktnamn (inte ett patronymikon) och precis en person med samma förnamn och
    släktnamn finns inom MAX_GAP_AR. DF anger ofta bara namnet ("Arvid Kurck") där SDHK
    har ämbetet, och ett släktnamn är ovanligt nog för att peka ut personen. Ett
    patronymikon ("Nils Larsson") gör det inte.
    """
    lista.sort(key=lambda f: (f.ar or (9999, 9999), ordning(f.verk)))
    for f in lista:
        nyck = f.nycklar()
        efter = ordform(f.u.efternamn) if f.u.efternamn else None
        mal = None
        if nyck and f.ar:
            kandidater = []
            for p in egna:
                if efter and p["efternamn"] and efter != p["efternamn"]:
                    continue
                gap = max(0, f.ar[0] - p["till"], p["fran"] - f.ar[1])
                spann = max(p["till"], f.ar[1]) - min(p["fran"], f.ar[0])
                if gap > MAX_GAP_AR or spann > MAX_SPANN_AR:
                    continue
                if _sateskonflikt(nyck, p["nycklar"]):
                    continue
                grad = _forenliga(nyck, p["nycklar"])
                if grad and grad != "exakt" or _bara_ambeten(nyck, p["nycklar"]):
                    if gap > MAX_GAP_AMBETE_AR or spann > MAX_SPANN_AMBETE_AR:
                        continue
                if grad:
                    kandidater.append((grad != "exakt", gap, p))
            kandidater.sort(key=lambda k: k[:2])
            if len(kandidater) == 1 or (len(kandidater) > 1 and kandidater[0][:2] < kandidater[1][:2]):
                mal = kandidater[0][2]
        elif slaktnamn and efter and f.ar and not PATRONYMIKON.search(efter):
            samma = [p for p in egna if p["efternamn"] == efter and p["till"] and
                     max(0, f.ar[0] - p["till"], p["fran"] - f.ar[1]) <= MAX_GAP_AR and
                     max(p["till"], f.ar[1]) - min(p["fran"], f.ar[0]) <= MAX_SPANN_AR]
            if len(samma) == 1:
                mal = samma[0]
        if mal is None:
            mal = {"efternamn": None, "nycklar": set(), "fran": 9999, "till": 0, "forekomster": []}
            egna.append(mal)
        if efter:
            mal["efternamn"] = efter
        if nyck and f.ar:
            mal["nycklar"] |= nyck
            mal["fran"] = min(mal["fran"], f.ar[0])
            mal["till"] = max(mal["till"], f.ar[1])
        mal["forekomster"].append(f)


def _namnge(personer: list[dict]) -> None:
    """Föreslår ett id per person efter namnet och det första brevet; IdRegister byter det mot registrets."""
    upptagna: set[str] = set()
    personer.sort(key=lambda p: min((ordning(f.verk), f.u.form) for f in p["forekomster"]))
    for p in personer:
        forst = min(p["forekomster"], key=lambda f: ordning(f.verk))
        namnform = Counter(
            f"{f.u.fornamn} {f.u.efternamn}" if f.u.efternamn else f.u.fornamn for f in p["forekomster"]
        ).most_common(1)[0][0]
        # Ett förnamn ensamt namnger personen bara om inget efternamn är känt
        fulla = [f"{f.u.fornamn} {f.u.efternamn}" for f in p["forekomster"] if f.u.efternamn]
        if fulla:
            namnform = Counter(fulla).most_common(1)[0][0]
        eid = lokalt_id(forst.verk, namnform)
        # Två personer med samma namn i samma brev ("Johannes i Huddinge och Johannes i Righiby")
        n = 2
        while eid in upptagna:
            eid, n = f"{lokalt_id(forst.verk, namnform)}-{n}", n + 1
        upptagna.add(eid)
        for f in p["forekomster"]:
            f.entitet, f.orsak = eid, "person"


# -----------------------------------------------------------------------------
# Stabila id:n
# -----------------------------------------------------------------------------


IDREGISTER = Path(__file__).parent / "data" / "sdhk_idregister.tsv"


class IdRegister:
    """
    Minns vilket id varje förekomst (brev och utfärdarform) fick senast, så
    att en person behåller sitt id när klustringen eller SDHK-datat ändras.

    En grupp får det tidigare id som flest av dess förekomster hade; större
    grupper väljer först. Ett id som ingen grupp får tillbaka ersätts av det
    id dit flest av dess förekomster gick, och ersättningen sparas så att
    länkar från andra källor går att följa. Ett id delas aldrig ut på nytt
    till en annan person. Registret ligger i data/ och delas mellan miljöerna.
    """

    def __init__(self, fil: Path = IDREGISTER) -> None:
        self.fil = fil
        self.tidigare: dict[str, str] = {}
        self.ersatta: dict[str, tuple[str, str]] = {}     # gammalt id -> (nytt id, gammalt namn)
        if fil.exists():
            for rad in fil.read_text(encoding="utf-8").splitlines():
                delar = rad.split("\t")
                if delar[0] == "F":
                    self.tidigare[delar[1]] = delar[2]
                elif delar[0] == "E":
                    self.ersatta[delar[1]] = (delar[2], delar[3])
        self.utdelade = set(self.tidigare.values()) | set(self.ersatta)
        self.nu: dict[str, str] = {}

    @staticmethod
    def nycklar(forekomster: list[Forekomst]) -> dict[int, str]:
        """id(förekomst) -> nyckel; samma form två gånger i ett brev får löpnummer."""
        raknare: Counter = Counter()
        ut = {}
        for f in sorted(forekomster, key=lambda f: (ordning(f.verk), f.u.form)):
            bas = f"{kort(f.verk)}:{ordform(f.u.form)}"
            if f.roll == "mottagare":
                bas = "m|" + bas
            elif f.roll == "adressat":
                bas = "a|" + bas
            raknare[bas] += 1
            ut[id(f)] = bas if raknare[bas] == 1 else f"{bas}#{raknare[bas]}"
        return ut

    def tilldela(self, forekomster: list[Forekomst], namn: dict[str, str]) -> None:
        """Byter de föreslagna id:na (person:sdhk:..., person:df:...) mot registrets."""
        nyckel = self.nycklar(forekomster)
        grupper: dict[str, list[Forekomst]] = defaultdict(list)
        for f in forekomster:
            if f.entitet and f.entitet.startswith(BREVPERSON):
                grupper[f.entitet].append(f)
        tagna: set[str] = set()
        byte: dict[str, str] = {}
        for forslag, grupp in sorted(grupper.items(), key=lambda g: (-len(g[1]), g[0])):
            rost = Counter(self.tidigare[nyckel[id(f)]] for f in grupp if nyckel[id(f)] in self.tidigare)
            val = next((pid for pid, _ in rost.most_common() if pid not in tagna and pid.startswith(BREVPERSON)),
                       None)
            if val is None:
                val, n = forslag, 2
                while val in self.utdelade or val in tagna:
                    val, n = f"{forslag}-{n}", n + 1
            tagna.add(val)
            byte[forslag] = val
        for f in forekomster:
            if f.entitet in byte:
                f.entitet = byte[f.entitet]
            self.nu[nyckel[id(f)]] = f.entitet

        # Ett id som används igen är inte längre ersatt
        for t in tagna:
            self.ersatta.pop(t, None)
        # Id:n som försvann: ersätts av det id dit flest av förekomsterna gick
        till: dict[str, Counter] = defaultdict(Counter)
        for k, gammalt in self.tidigare.items():
            if k in self.nu and gammalt not in tagna and gammalt.startswith(BREVPERSON):
                till[gammalt][self.nu[k]] += 1
        for gammalt, mal in till.items():
            if gammalt not in self.ersatta:
                self.ersatta[gammalt] = (mal.most_common(1)[0][0], namn.get(gammalt, gammalt))
        # En ersättning som pekar på ett id som i sin tur ersatts följs till slutet
        for gammalt in list(self.ersatta):
            nytt, gnamn = self.ersatta[gammalt]
            sett = {gammalt}
            while nytt in self.ersatta and nytt not in sett and nytt not in tagna:
                sett.add(nytt)
                nytt = self.ersatta[nytt][0]
            self.ersatta[gammalt] = (nytt, gnamn)

    def spara(self) -> None:
        with open(self.fil, "w", encoding="utf-8") as ut:
            ut.write("# Brevutfärdarnas id-register (SDHK och DF); skrivs av pastaenden_sdhk.py. "
                     "F nyckel id: förekomstens id. E gammalt nytt namn: ersatt id.\n")
            for k in sorted(self.nu):
                ut.write(f"F\t{k}\t{self.nu[k]}\n")
            for gammalt in sorted(self.ersatta):
                nytt, namn = self.ersatta[gammalt]
                ut.write(f"E\t{gammalt}\t{nytt}\t{namn}\n")


# -----------------------------------------------------------------------------
# Inläsning
# -----------------------------------------------------------------------------


DF_MAKTLOS = re.compile(r"^\(ei määritetty\)$|^-+\s*ei antajatietoa\s*-+$")
DF_INSTITUTION = {"råd": "Rådet i {}", "rådmän": "Rådmännen i {}", "borgmästare och råd": "Rådet i {}",
                  "domkapitel": "Domkapitlet i {}", "konvent": "Konventet i {}"}
DF_RIKSRAD = {"Sverige": "Sveriges riksråd", "Danmark": "Danmarks riksråd", "Norge": "Norges riksråd"}
DF_TITEL_EFTER = re.compile(r"^([^,]+), (kung|drottning|påve|hertig|hertiginna|riksföreståndare)\b")


def df_falt(falt: str) -> str:
    """
    DF:s utfärdarfält i SDHK:s form, så att samma tolkning gäller båda.

    DF skriver namnet före titeln och "av" för orten: "Gustaf, kung", "Råd, av
    Stockholm", "Sigfrid, av Linköping". "ja 3 muuta" ("och 3 andra") blir "m.fl.",
    och "(ei määritetty)" ("inte angiven") är en utfärdare utan namn, som inte tolkas.
    """
    f = re.sub(r"\s+", " ", falt).strip()
    f = re.sub(r"\s*\bja \d+ muuta\s*\.?$", " m.fl.", f)
    if DF_MAKTLOS.match(f):
        return ""
    # "(ei määritetty), borgmästare av Åbo": ett ämbete utan namn ger ingen person
    if f.startswith("(ei määritetty)"):
        return ""
    if m := re.match(r"^Riksråd, av (\S+?)(\s+m\.fl\.)?$", f):
        return DF_RIKSRAD.get(m[1], f)
    if (m := re.match(r"^([A-ZÅÄÖ][a-zåäö ]+), av ([A-ZÅÄÖ][\w-]+)(.*)$", f)) and m[1].lower() in DF_INSTITUTION:
        return DF_INSTITUTION[m[1].lower()].format(m[2]) + m[3]
    f = DF_TITEL_EFTER.sub(lambda m: f"{m[2].capitalize()} {m[1]}", f)
    # "Sigfrid, av Linköping", "Sten Sture, av Gripsholm, riddare": orten hör till namnet
    f = re.sub(r"^([A-ZÅÄÖ][^,]*?), (?:av|från) ([A-ZÅÄÖ])", r"\1 i \2", f)
    return f


def hamta_brev(conn) -> list[tuple]:
    """
    (verk, utfärdarfält, datering, passager) för SDHK:s brev och DF:s. DF-brev som
    redan är kopplade till ett SDHK-brev (samma FMU-nummer och datum) är samma brev
    och tas bara med ur SDHK.
    """
    p = db._prefix()
    cur = conn.cursor()
    passager = f"""(SELECT id FROM {p}passage WHERE id = v.id || ':regest'),
               (SELECT id FROM {p}passage WHERE id = v.id || ':originaltext'),
               (SELECT text FROM {p}passage WHERE id = v.id || ':regest')"""
    cur.execute(f"""
        SELECT v.id, b.utfardare, v.datering_edtf, v.datering_fran, v.datering_till, {passager}
        FROM {p}sdhk_brev b JOIN {p}verk v ON v.id = 'sdhk:' || b.sdhk_nr
        WHERE b.utfardare IS NOT NULL
        ORDER BY b.sdhk_nr""")
    brev = cur.fetchall()
    cur.execute(f"""
        SELECT v.id, v.upphov, v.datering_edtf, v.datering_fran, v.datering_till, {passager}, v.extra
        FROM {p}verk v WHERE v.kallsamling_id = 'df' AND v.upphov IS NOT NULL""")
    df = []
    for verk, falt, *resten, extra in cur.fetchall():
        extra = extra if isinstance(extra, dict) else json.loads(extra or "{}")
        if extra.get("sdhk"):
            continue
        if falt := df_falt(falt):
            df.append((verk, falt, *resten))
    return brev + sorted(df, key=lambda b: ordning(b[0]))


def kanda_fornamn(brev: list[tuple]) -> set[str]:
    """Förnamn som inleder minst fem utfärdarfält med två eller fler ord."""
    rakna = Counter()
    for _, falt, *_ in brev:
        ord_ = _skala(falt).split()
        while ord_ and _ar_titel(ord_[0]):
            ord_ = ord_[1:]
        if len(ord_) >= 2 and re.fullmatch(NAMNORD, ord_[0]):
            rakna[ord_[0]] += 1
    return {n for n, k in rakna.items() if k >= 5}


def bygg(conn) -> dict:
    """Tolkar alla utfärdarfält och avgör identiteter. Skriver inget."""
    brev = hamta_brev(conn)
    fornamn = kanda_fornamn(brev)
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {db._prefix()}verk WHERE kallsamling_id IN ('sdhk', 'df')")
    alla_brev = {rad[0] for rad in cur.fetchall()}
    regenter = Regenter()
    stat = Counter()
    otolkade, ofullst = [], []
    forekomster: list[Forekomst] = []
    institutioner: dict[str, str] = {}
    datering: dict[int, tuple] = {}

    garningar: dict[str, Garning] = {}
    brevformer: dict[str, Brevform] = {}
    regesttexter: dict[str, str] = {}

    def koppla(f: Forekomst) -> None:
        """Identifierar en förekomst mot institutioner, regenter, påvar och biskopar."""
        u, verk, ar = f.u, f.verk, f.ar
        suffix = {"utfardare": "", "mottagare": "-m", "adressat": "-a"}[f.roll]
        if u.institution:
            iid = f"institution:sdhk:{_slug(u.institution)}"
            institutioner[iid] = u.institution
            f.entitet, f.orsak = iid, "institution"
        elif u.titel in REGENTTITLAR | {"pave"}:
            ident = regenter.identifiera(u, ar)
            if ident.entitet is None and (eid := regenter.fullt_namn(u, ar)):
                ident = Identitet(eid, "under_titeln")
            f.identitet = ident
            if ident.entitet:
                f.entitet, f.orsak = ident.entitet, "pave" if u.titel == "pave" else "regent"
            else:
                # Egen entitet per förekomst: identiteten är oklar eller
                # personen saknas i listorna, och sammanslagning på bara
                # titel och förnamn vore en gissning
                nr_i_brev = sum(1 for g in forekomster if g.verk == verk and g.roll == f.roll
                                and g.identitet and g.identitet.entitet is None)
                f.entitet = lokalt_id(verk, f"{u.titel} {u.fornamn or u.form}") + suffix + \
                    (f"-{nr_i_brev + 1}" if nr_i_brev else "")
                f.orsak = ident.grund
        elif (biskop := _biskopsambete(u, regenter.saten)):
            # Biskopar slås upp i biskopslistan med sätet i rikets ställe;
            # utan träff klustras de som andra personer
            kod, sate = biskop
            ident = regenter.identifiera(replace(u, titel=kod, rike=sate, ort=None), ar)
            if ident.entitet:
                f.identitet, f.entitet, f.orsak = replace(ident, titel=kod), ident.entitet, "biskop"
            elif ident.grund == "oklar":
                f.identitet = replace(ident, titel=kod)
                f.entitet = lokalt_id(verk, f"{kod} {u.fornamn or u.form}") + suffix
                f.orsak = "oklar"
        else:
            eid = regenter.fullt_namn(u, ar)
            if eid:
                f.entitet, f.orsak = eid, "regent"
                f.identitet = Identitet(eid, "under_titeln")

    for verk, falt, edtf, fran, till, regest, original, regesttext in brev:
        passage = regest or original
        if passage is None:
            stat["brev_utan_passage"] += 1
            continue
        datering[verk] = (edtf, fran, till)
        ar = (fran // 10000, till // 10000) if fran and till else None
        t = tolka(falt, fornamn)
        if t.otolkat:
            otolkade.append((verk, falt, t.otolkat))
        if t.ofullstandig:
            ofullst.append(verk)
        stat["brev"] += 1
        stat["brev_" + verk.split(":")[0]] += 1
        stat["brev_med_utfardare" if t.utfardare else "brev_utan_tolkad_utfardare"] += 1
        for u in t.utfardare:
            f = Forekomst(verk, passage, ar, u)
            koppla(f)
            forekomster.append(f)

        # Regestens huvudgärning; mottagarna tolkas och identifieras som utfärdarna
        g = tolka_garning(regesttext) if regest and regesttext and t.utfardare else None
        if g:
            garningar[verk] = g
            regesttexter[verk] = regesttext
            stat["garning_" + g.predikat] += 1
            if g.mottagare:
                for u in tolka(g.mottagare, fornamn).utfardare:
                    # Uppräknade gårdsnamn ("till Erik Turesson Gålstad, Bankeberg och
                    # Rökinge") tolkas annars som personer: en mottagare ska ha titel,
                    # ämbete, efternamn, ett känt förnamn eller vara en institution
                    if not (u.institution or u.titel or u.ambeten or u.efternamn or u.fornamn in fornamn):
                        stat["mottagare_avvisad"] += 1
                        continue
                    f = Forekomst(verk, regest, ar, u, roll="mottagare")
                    koppla(f)
                    forekomster.append(f)
                    stat["mottagare"] += 1

        # Ett brev utan gärning kan vara ett missiv med en adressat, och ett svar på ett tidigare brev
        b = tolka_brevform(regesttext) if regest and regesttext and t.utfardare and not g else None
        if b:
            brevformer[verk] = b
            regesttexter[verk] = regesttext
            stat["svar"] += b.svar
            stat["svar_med_datum"] += b.datum is not None
            for u in (tolka(b.adressat, fornamn).utfardare if b.adressat else []):
                if not (u.institution or u.titel or u.ambeten or u.efternamn or u.fornamn in fornamn):
                    stat["adressat_avvisad"] += 1
                    continue
                f = Forekomst(verk, regest, ar, u, roll="adressat")
                koppla(f)
                forekomster.append(f)
                stat["adressat"] += 1

    att_klustra = [f for f in forekomster if f.entitet is None]
    klustra(att_klustra)
    for f in forekomster:
        stat[f"{f.roll}_" + (f.orsak or "okopplad")] += 1
        if f.identitet and f.identitet.entitet:
            stat["identifiering_" + f.identitet.grund] += 1

    # De föreslagna id:na byts mot registrets, så att en person behåller sitt
    # id mellan körningar; namnen behövs för hänvisningar från ersatta id:n
    register = IdRegister()
    gamla_namn = {}
    if register.tidigare:
        cur = conn.cursor()
        cur.execute(f"SELECT id, namn FROM {db._prefix()}entitet WHERE id LIKE 'person:sdhk:%' OR id LIKE 'person:df:%'")
        gamla_namn = dict(cur.fetchall())
    register.tilldela(forekomster, gamla_namn)
    stat["ersatta_id"] = len(register.ersatta)
    return {"forekomster": forekomster, "institutioner": institutioner, "regenter": regenter,
            "register": register, "garningar": garningar, "brevformer": brevformer, "regesttext": regesttexter,
            "alla_brev": alla_brev,
            "datering": datering, "stat": stat, "otolkade": otolkade, "ofullstandiga": ofullst}


class Platsuppslag:
    """
    Slår upp en ort i ett utfärdarfält eller en regest bland de platser som redan finns,
    så att samma ort inte får en ny entitet för varje källa.

    Uppslaget följer platsregistrets regler (platser.py): runinskrifternas fyndplatser,
    socknarna och de andra platserna med område eller kod i id:t slås aldrig upp på
    namnet, och projektets handregistrerade platser går före de ur breven. För ett
    DF-brev går DF:s egen plats med namnet först, eftersom DF:s platsregister anger
    vilken ort som avses. En plats som har ersatts av en annan följs till den nya.
    Platserna gås igenom i id-ordning, så att ett namn alltid ger samma plats.
    """

    def __init__(self, cur) -> None:
        from platser import EJ_PA_NAMN
        p = db._prefix()
        cur.execute(f"SELECT id, namn FROM {p}entitet WHERE typ IN ('plats', 'indelning') ORDER BY id")
        rader_ = cur.fetchall()
        self.finns = {pid for pid, _ in rader_}
        cur.execute(f"SELECT entitet_id, identifierad_med FROM {p}identifiering WHERE kommentar = 'ersatt_av'")
        self.ersatt = dict(cur.fetchall())
        self.per_form: dict[str, str] = {}
        for pid, namn in rader_:
            if pid.startswith(EJ_PA_NAMN) or pid in self.ersatt:
                continue
            nyckel = ordform(namn)
            tidigare = self.per_form.get(nyckel)
            if tidigare is None or (tidigare.startswith("plats:sdhk:") and not pid.startswith("plats:sdhk:")):
                self.per_form[nyckel] = pid

    def folj(self, pid: str) -> str:
        sett = {pid}
        while pid in self.ersatt and self.ersatt[pid] not in sett:
            pid = self.ersatt[pid]
            sett.add(pid)
        return pid

    def __call__(self, ort: str, verk: str) -> str | None:
        if verk.startswith("df:") and (pid := f"plats:df:{_slug(ort)}") in self.finns:
            return self.folj(pid)
        if (pid := self.per_form.get(ordform(ort))):
            return self.folj(pid)
        # En brevort som ersatts av en annan finns inte i per_form men ska följas dit
        if (pid := f"plats:sdhk:{_slug(ort)}") in self.ersatt:
            return self.folj(pid)
        return None


ROLLNAMN = {"utfardare": "Utfärdare", "mottagare": "Mottagare", "adressat": "Adressat"}
# Ett svar utan datum kopplas bara till ett brev från det senaste året
SVAR_UTAN_DATUM_DAGAR = 365


def _dag(n: int | None) -> date | None:
    if not n or n % 100 == 0 or n // 100 % 100 == 0:
        return None
    try:
        return date(n // 10000, n // 100 % 100, n % 100)
    except ValueError:
        return None


def svarskopplingar(resultat: dict, per_brev: dict) -> dict[str, tuple[str, str, str]]:
    """
    Det brev som ett svar besvarar: brev -> (besvarat brev, grad, motivering).

    Anger utgivaren det besvarade brevets nummer ("SDHK nr 23220", i DF "n:o 5257") är
    kopplingen säker. Annars räknas ett brev som det besvarade när parterna har bytt plats: dess utfärdare är
    svarets adressat och dess adressat eller mottagare är svarets utfärdare. Saknar ett
    av breven den andra parten räcker att förnamnet stämmer. Anger regesten datumet
    ("dennes brev av 28 maj") ska det besvarade brevet ha det datumet, och kopplingen
    är sannolik. Utan datum prövas brev från det senaste året; ett enda brev där båda
    parterna stämmer ger en möjlig koppling. Hittas inget brev, eller flera, kopplas
    svaret inte.
    """
    datering = resultat["datering"]
    fornamn: dict[tuple[str, str], set[str]] = defaultdict(set)
    for f in resultat["forekomster"]:
        if f.u.fornamn:
            fornamn[(f.verk, f.roll)].add(ordform(f.u.fornamn))
    per_dag: dict[int, list[str]] = defaultdict(list)
    per_utfardare: dict[str, list[str]] = defaultdict(list)
    for verk, (_, fran, till) in datering.items():
        if fran and fran == till:
            per_dag[fran].append(verk)
        for e in per_brev[verk]["utfardare"]:
            per_utfardare[e].append(verk)

    def parter(c: str, r: str) -> tuple[bool, bool, bool]:
        c_utf, r_utf = set(per_brev[c]["utfardare"]), set(per_brev[r]["utfardare"])
        c_till = set(per_brev[c]["adressat"]) | set(per_brev[c]["mottagare"])
        r_adr = set(per_brev[r]["adressat"])
        utf_ar_adressat = bool(c_utf & r_adr)
        adressat_ar_utf = bool(c_till & r_utf)
        samma_fornamn = bool(fornamn[(c, "utfardare")] & fornamn[(r, "adressat")])
        return utf_ar_adressat, adressat_ar_utf, samma_fornamn

    def passar_odaterat(c: str, r: str) -> bool:
        """Utan datum ska kandidaten vara ett missiv från adressaten till utfärdaren, inte en gärning."""
        return bool(set(per_brev[c]["utfardare"]) & set(per_brev[r]["adressat"])) and \
            bool(set(per_brev[c]["adressat"]) & set(per_brev[r]["utfardare"]))

    def passar_daterat(c: str, r: str) -> bool:
        a, b, f = parter(c, r)
        c_till = per_brev[c]["adressat"] or per_brev[c]["mottagare"]
        return (a and (b or not c_till)) or (b and (a or f or not per_brev[r]["adressat"]))

    ut = {}
    for r, bf in resultat["brevformer"].items():
        if not bf.svar or not per_brev[r]["utfardare"]:
            continue
        _, fran, till = datering[r]
        if bf.nummer:
            kalla, nr = bf.nummer
            c = f"sdhk:{nr}" if kalla == "sdhk" else f"{r.split(':')[0]}:{nr}"
            if c != r and c in resultat["alla_brev"]:
                ut[r] = (c, "saker", f"Regesten hänvisar själv till det besvarade brevet ({c}).")
                continue
        if not fran:
            continue
        if bf.datum:
            dag, manad, ar = bf.datum
            if ar is None:
                # Utan år: samma år som svaret, eller året före om dagen ligger senare på året
                ar = fran // 10000 if (manad, dag) <= (till // 100 % 100 or 12, till % 100 or 31) else fran // 10000 - 1
            traffar = [c for c in per_dag.get(ar * 10000 + manad * 100 + dag, []) if c != r and passar_daterat(c, r)]
            if len(traffar) == 1:
                ut[r] = (traffar[0], "sannolik",
                         f"Regesten hänvisar till brevet av {dag}/{manad} {ar}; det brevet har det datumet, "
                         f"och dess utfärdare och adressat är svarets parter i omvänd ordning.")
            continue
        slut = _dag(till) or _dag(fran)
        if not slut:
            continue
        kandidater = {c for e in per_brev[r]["adressat"] for c in per_utfardare.get(e, [])}
        traffar = []
        for c in kandidater:
            _, c_fran, c_till = datering[c]
            c_dag = _dag(c_fran) if c_fran == c_till else None
            if c == r or not c_dag or not (0 <= (slut - c_dag).days <= SVAR_UTAN_DATUM_DAGAR):
                continue
            if passar_odaterat(c, r):
                traffar.append(c)
        if len(traffar) == 1:
            ut[r] = (traffar[0], "mojlig",
                     f"Regesten säger att brevet är ett svar men anger inte vilket brev. Det enda brevet från "
                     f"adressaten till utfärdaren under året före är {traffar[0]}.")
    return ut


def rader(resultat: dict, uppslag) -> dict[str, list[tuple]]:
    """Entiteter, namnformer och påståenden ur tolkningen."""
    entiteter: dict[str, tuple] = {}
    namnformer: dict[tuple, tuple] = {}
    pastaenden: dict[str, tuple] = {}
    platser: dict[str, tuple] = {}
    identifieringar: list[tuple] = []
    bedomningar: list[tuple] = []
    regenter = resultat["regenter"]

    for e in regenter.entiteter():
        entiteter[e[0]] = e
    for iid, namn in resultat["institutioner"].items():
        entiteter[iid] = (iid, "institution", namn, "Utfärdare eller mottagare i SDHK eller DF")

    def plats(ort: str | None, verk: str) -> str | None:
        if not ort:
            return None
        if (pid := uppslag(ort, verk)):
            return pid
        # En ny ort får id efter namnet, oavsett källa, så att samma namn ger samma id
        pid = f"plats:sdhk:{_slug(ort)}"
        # Ett befintligt id med annan namnform behåller sitt namn
        if pid in uppslag.finns:
            return pid
        typ = "indelning" if re.search(r"\b(härad|hundare|socken|sn|hd|lagsaga|land|län)\b", ort) else "plats"
        platser.setdefault(pid, (pid, typ, ort, "Ort i brevens utfärdarfält eller regester (SDHK, DF)"))
        return pid

    # Spann och ämbeten per person för beskrivningen
    personinfo: dict[str, dict] = defaultdict(lambda: {"ar": [], "namn": Counter(), "ambeten": Counter(), "kallor": set()})
    for f in resultat["forekomster"]:
        if f.entitet is None:
            continue
        edtf, fran, till = resultat["datering"][f.verk]
        info = personinfo[f.entitet]
        if f.ar:
            info["ar"] += list(f.ar)
        u = f.u
        info["kallor"].add(f.verk.split(":")[0])
        if f.entitet.startswith(BREVPERSON):
            info["namn"][f"{u.fornamn} {u.efternamn}" if u.efternamn else u.fornamn] += 1
        namnformer.setdefault((f.entitet, u.form), (f.entitet, u.form, "swe", f.passage_id))

        n = 0
        bas = f"{f.verk}:{f.roll}:{f.entitet.split(':', 1)[1].replace(':', '_')}"
        if f.roll == "utfardare":
            pastaenden.setdefault(f"{bas}:utfardar", (
                f"{bas}:utfardar", f.passage_id, f.entitet, "utfardar", None, f.verk, None,
                edtf, fran, till))
        ambeten = list(u.ambeten)
        if u.titel in REGENTTITLAR | {"pave"}:
            ambeten.insert(0, Ambete(u.titel, u.rike if u.titel != "pave" else None))
        titelpastaende = None
        titelpastaenden: dict[str, str] = {}
        for a in ambeten:
            etikett, begrepp = AMBETEN[a.kod]
            predikat = "har_stand" if a.kod in STAND else "innehar_ambete"
            info["ambeten"][etikett + (f" i {a.ort}" if a.ort else "")] += 1
            pid = f"{bas}:{predikat}:{a.kod}:{_slug(a.ort) if a.ort else n}"
            pastaenden.setdefault(pid, (
                pid, f.passage_id, f.entitet, predikat, begrepp, None, plats(a.ort, f.verk),
                edtf, fran, till))
            titelpastaende = titelpastaende or pid
            titelpastaenden.setdefault(a.kod, pid)
            n += 1

        ident = f.identitet
        titel = ident.titel or u.titel if ident else None
        if ident is None or titel not in REGENTTITLAR | {"pave", "biskop", "arkebiskop"}:
            continue
        # Brevet hävdar titeln; att den inte stämmer med dateringen är en
        # bedömning av påståendet, medan identiteten ligger i kopplingen
        if ident.entitet and ident.grund in GRUNDER[1:]:
            tp = titelpastaenden.get(titel, titelpastaende)
            bedomningar.append((f"{tp}:titulatur", tp, None, "titulatur", ident.grund, ident.motivering))
        if ident.grund == "oklar":
            for kid, grund in ident.kandidater:
                iid = f"identifiering:sdhk:{f.entitet.split(':', 1)[1].replace(':', '_')}:{kid.split(':', 1)[1]}"
                grupp = f"{f.verk}:{f.entitet}" if len(ident.kandidater) > 1 else None
                identifieringar.append((iid, f.entitet, kid, grupp, grund))
                motivering = ("Utfärdaren anges bara med titel och namn, och flera personer i "
                              "auktoritetslistan passar. " if len(ident.kandidater) > 1 else
                              "Utfärdaren anges bara med titel och namn, och den enda kandidaten "
                              "levde inte vid brevets datering. ") + (
                    regenter._motivering(kid, titel, grund, f.ar) if f.ar else "Brevet är odaterat.")
                bedomningar.append((f"{iid}:bedomning", None, iid, "identifiering", "mojlig", motivering))

    # Regestens huvudgärning: varje utfärdare mot varje mottagare. Värdet är
    # egendom och pris (ämbetet för 'utnamner'), platsen den första orten
    per_brev: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"utfardare": [], "mottagare": [], "adressat": []})
    for f in resultat["forekomster"]:
        if f.entitet and f.entitet not in per_brev[f.verk][f.roll]:
            per_brev[f.verk][f.roll].append(f.entitet)
    for verk, g in resultat["garningar"].items():
        edtf, fran, till = resultat["datering"][verk]
        varde = " ".join(x for x in (g.egendom, f"för {g.pris}" if g.pris else None) if x)[:400] or None
        if g.slakt:
            varde = f"{varde} (till {g.slakt})" if varde else f"till {g.slakt}"
        mottagare = per_brev[verk]["mottagare"] or [None]
        for s_id in per_brev[verk]["utfardare"]:
            for o_id in mottagare:
                if s_id == o_id or (o_id is None and not varde):
                    continue
                kortid = lambda e: e.split(":", 1)[1].replace(":", "_") if e else "x"
                pid = f"{verk}:garning:{g.predikat}:{kortid(s_id)}:{kortid(o_id)}"
                pastaenden.setdefault(pid, (pid, f"{verk}:regest", s_id, g.predikat, o_id, varde,
                                            plats(g.ort, verk), edtf, fran, till))

    # Missivens adressater, och svaren på tidigare brev. Värdet är brevets eget verk-id för
    # 'skriver_till' och det besvarade brevets verk-id för 'besvarar' när det har hittats;
    # annars står regestens hänvisning kvar ("dennes skrivelse av 28 maj").
    kortid = lambda e: e.split(":", 1)[1].replace(":", "_") if e else "x"
    kopplingar = svarskopplingar(resultat, per_brev)
    for verk, b in resultat["brevformer"].items():
        edtf, fran, till = resultat["datering"][verk]
        adressater = per_brev[verk]["adressat"]
        for s_id in per_brev[verk]["utfardare"]:
            for o_id in adressater:
                if s_id != o_id:
                    pid = f"{verk}:skriver_till:{kortid(s_id)}:{kortid(o_id)}"
                    pastaenden.setdefault(pid, (pid, f"{verk}:regest", s_id, "skriver_till", o_id, verk,
                                                None, edtf, fran, till))
            if not b.svar:
                continue
            besvarat, grad, motivering = kopplingar.get(verk, (None, None, None))
            # Utan adressat i regesten är det besvarade brevets utfärdare den som får svaret
            motparter = adressater or (per_brev[besvarat]["utfardare"] if besvarat else []) or [None]
            for o_id in motparter:
                # Ett påstående behöver ett objekt eller ett värde: "svarar" utan motpart säger inget
                if s_id == o_id or (o_id is None and not (besvarat or b.hanvisning)):
                    continue
                pid = f"{verk}:besvarar:{kortid(s_id)}:{kortid(o_id)}"
                pastaenden.setdefault(pid, (pid, f"{verk}:regest", s_id, "besvarar", o_id,
                                            besvarat or b.hanvisning, None, edtf, fran, till))
                if besvarat:
                    bedomningar.append((f"{pid}:brevkoppling", pid, None, "brevkoppling", grad, motivering))

    oklara = {f.entitet: f for f in resultat["forekomster"]
              if f.identitet and f.identitet.entitet is None and f.entitet}
    for eid, info in personinfo.items():
        if not eid.startswith(BREVPERSON):
            continue
        if eid in oklara:
            f = oklara[eid]
            u = f.u
            ar = "odaterad" if f.ar is None else str(f.ar[0]) if f.ar[0] == f.ar[1] else f"{f.ar[0]}–{f.ar[1]}"
            if f.identitet.grund == "saknas":
                anm = f"ingen {AMBETEN[u.titel][0]} {u.fornamn or ''} finns i auktoritetslistorna".replace("  ", " ")
            else:
                anm = "möjligen " + " eller ".join(regenter.per_id[k]["namn"] for k, _ in f.identitet.kandidater)
            entiteter[eid] = (eid, "person", u.form, f"{ROLLNAMN[f.roll]} i {KALLOR[f.verk.split(':')[0]]} {f.verk.split(':')[1]} ({ar}); {anm}")
            continue
        # Ett känt efternamn går före förnamnet ensamt ("Jakob Ulfsson", inte "Jakob")
        fulla = Counter({n: k for n, k in info["namn"].items() if " " in n})
        namn = (fulla or info["namn"]).most_common(1)[0][0]
        spann = f"{min(info['ar'])}–{max(info['ar'])}" if info["ar"] else "odaterad"
        amb = ", ".join(a for a, _ in info["ambeten"].most_common(3))
        kallor = " och ".join(KALLOR[k] for k in KALLOR if k in info["kallor"])
        entiteter[eid] = (eid, "person", namn, f"I {kallor} {spann}" + (f"; {amb}" if amb else ""))

    # Ersatta id:n finns kvar som hänvisningar, så att länkar från andra källor
    # går att följa till personen de slogs ihop med
    aktuella = {f.entitet for f in resultat["forekomster"]}
    for gammalt, (nytt, namn) in resultat["register"].ersatta.items():
        if gammalt in aktuella or nytt not in aktuella:
            continue
        entiteter[gammalt] = (gammalt, "person", namn, f"Ersatt av {nytt}; brevutfärdare som slagits ihop")
        iid = f"identifiering:sdhk:ersatt:{gammalt.split(':', 1)[1].replace(':', '_')}"
        identifieringar.append((iid, gammalt, nytt, None, "ersatt_av"))
        bedomningar.append((f"{iid}:bedomning", None, iid, "identifiering", "saker",
                            "Id:t ersattes när förekomsterna slogs ihop med en annan utfärdare."))

    entiteter.update(platser)
    return {"entitet": list(entiteter.values()), "entitet_namnform": list(namnformer.values()),
            "pastaende": list(pastaenden.values()), "identifiering": identifieringar,
            "bedomning": bedomningar}


def ladda_pastaenden(resultat: dict) -> None:
    conn = db._hamta_db()
    p, ph = db._prefix(), db._ph()
    try:
        cur = conn.cursor()
        r = rader(resultat, Platsuppslag(cur))
        # Ämbeten som begreppsregistret inte har ännu; befintliga begrepp
        # behåller sina namn och beskrivningar
        cur.execute(f"SELECT id FROM {p}entitet WHERE id LIKE 'begrepp:%'")
        finns = {rad[0] for rad in cur.fetchall()}
        r["entitet"] += [(bid, "ambete", etikett.capitalize(),
                          "Titel eller ämbete; termer och definition saknas ännu i begreppsregistret")
                         for etikett, bid in AMBETEN.values() if bid not in finns]

        # Klustringen kan ändras mellan körningar, så tidigare påståenden och
        # entiteter ur breven tas bort i stället för att uppdateras
        with conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {p}identifiering WHERE id LIKE 'identifiering:sdhk:%'")
            cur.execute(f"DELETE FROM {p}pastaende WHERE extraherad_av = {ph}", (EXTRAHERAD_AV,))
        db.upsert(conn, "entitet", ["id", "typ", "namn", "beskrivning", "wikidata_id"], ["id"],
                  [e if len(e) == 5 else (*e, None) for e in r["entitet"]])
        db.upsert(conn, "entitet_namnform", ["entitet_id", "namnform", "sprak", "passage_id"],
                  ["entitet_id", "namnform"], r["entitet_namnform"])
        db.upsert(conn, "pastaende",
                  ["id", "passage_id", "subjekt_id", "predikat", "objekt_id", "objekt_varde", "plats_id",
                   "tid_edtf", "tid_fran", "tid_till", "extraktion", "extraherad_av"], ["id"],
                  [(*rad, "regel", EXTRAHERAD_AV) for rad in r["pastaende"]])
        db.upsert(conn, "identifiering", ["id", "entitet_id", "identifierad_med", "alternativgrupp", "kommentar"],
                  ["id"], r["identifiering"])
        db.upsert(conn, "bedomning",
                  ["id", "pastaende_id", "identifiering_id", "aspekt", "varde", "motivering", "bedomare",
                   "registrerad_av"], ["id"],
                  [(*rad, EXTRAHERAD_AV, EXTRAHERAD_AV) for rad in r["bedomning"]])
        # Personer och institutioner som inte längre används tas bort först när de nya
        # påståendena finns, så att en entitet som de återanvänder står kvar. Platser tas
        # aldrig bort här: platser.py flyttar påståendena till den ort som avses (Viborg i
        # Jylland eller i Karelen) och rensar själv, så en plats som inte används efter
        # den här körningen kan användas igen efter platser.py.
        with conn:
            cur = conn.cursor()
            for prefix in ("person:sdhk:%", "person:df:%", "institution:sdhk:%"):
                # Entiteter som andra källor refererar till raderas aldrig
                cur.execute(f"DELETE FROM {p}entitet WHERE id LIKE {ph} AND id NOT IN "
                            f"(SELECT subjekt_id FROM {p}pastaende UNION SELECT objekt_id FROM {p}pastaende "
                            f"WHERE objekt_id IS NOT NULL UNION SELECT plats_id FROM {p}pastaende "
                            f"WHERE plats_id IS NOT NULL UNION SELECT entitet_id FROM {p}identifiering "
                            f"UNION SELECT identifierad_med FROM {p}identifiering "
                            f"UNION SELECT plats_id FROM {p}verk_plats "
                            f"UNION SELECT entitet_id FROM {p}plats_uppgift "
                            f"UNION SELECT ingar_i_id FROM {p}plats_uppgift WHERE ingar_i_id IS NOT NULL "
                            f"UNION SELECT plats_id FROM {p}sokpost_plats "
                            f"UNION SELECT sate_id FROM {p}auktoritet_titel WHERE sate_id IS NOT NULL)", (prefix,))
        log.info("%d entiteter, %d namnformer, %d påståenden, %d identifieringar, %d bedömningar",
                 len(r["entitet"]), len(r["entitet_namnform"]), len(r["pastaende"]),
                 len(r["identifiering"]), len(r["bedomning"]))
    finally:
        conn.close()


def skriv_rapport(resultat: dict, katalog: Path, antal: int = 80) -> None:
    """Statistik, otolkade fält och ett slumpat stickprov för granskning."""
    katalog.mkdir(parents=True, exist_ok=True)
    fk = resultat["forekomster"]
    slump = random.Random(1)
    rader_ = ["# Stickprov: påståenden ur SDHK:s och DF:s utfärdarfält", ""]
    rader_ += [f"- {k}: {v}" for k, v in sorted(resultat["stat"].items())]
    per_entitet = Counter(f.entitet for f in fk if f.entitet)
    rader_ += ["", f"Entiteter: {len(per_entitet)}; personer i nivå 3 med fler än en förekomst: "
               f"{sum(1 for e, n in per_entitet.items() if e.startswith(BREVPERSON) and n > 1)}", ""]
    rader_ += ["## Slumpat stickprov", "", "| brev | utfärdarfält | tolkning | entitet |", "|---|---|---|---|"]
    for f in slump.sample(fk, min(antal, len(fk))):
        u = f.u
        tolkn = "; ".join(x for x in [
            u.institution, AMBETEN[u.titel][0] if u.titel else None,
            " ".join(x for x in [u.fornamn, u.efternamn, u.ordningstal] if x),
            f"ort {u.ort}" if u.ort else None,
            ", ".join(AMBETEN[a.kod][0] + (f" i {a.ort}" if a.ort else "") for a in u.ambeten) or None,
            f"rike {u.rike}" if u.rike else None] if x)
        rader_.append(f"| {f.verk} | {u.form} | {tolkn} | {f.entitet or '–'} ({f.orsak}) |")
    stora = [(e, n) for e, n in per_entitet.most_common() if e.startswith(BREVPERSON)][:40]
    rader_ += ["", "## Största sammanslagna personer", ""]
    for e, n in stora:
        ar = [f.ar for f in fk if f.entitet == e and f.ar]
        former = Counter(f.u.form for f in fk if f.entitet == e).most_common(3)
        rader_.append(f"- {e}: {n} brev, {min(a[0] for a in ar) if ar else '?'}–"
                      f"{max(a[1] for a in ar) if ar else '?'}; {', '.join(x for x, _ in former)}")
    regenter = resultat["regenter"]
    rubriker = {
        "fore_titeln": "Kopplade, levde men hade ännu inte titeln",
        "efter_titeln": "Kopplade, levde men hade förlorat eller lämnat titeln",
        "efter_dodsfall": "Kopplade, omnämnda efter döden",
        "fore_fodelse": "Kopplade, dateringen före födelsen",
        "oklar": "Ej kopplade, oklar identitet (möjliga kandidater som identifieringar)",
        "saknas": "Ej kopplade, saknas i auktoritetslistorna",
    }
    for grund, rubrik in rubriker.items():
        urval = [f for f in fk if f.identitet and f.identitet.grund == grund]
        rader_ += ["", f"## {rubrik} ({len(urval)})", ""]
        grupper = Counter()
        for f in urval:
            if f.identitet.entitet:
                vem = regenter.per_id[f.identitet.entitet]["namn"]
            else:
                vem = " / ".join(regenter.per_id[k]["namn"] for k, _ in f.identitet.kandidater) or "–"
            grupper[(f.u.form, vem)] += 1
        for (form, vem), n in grupper.most_common(40):
            ar = sorted({a for f in urval if f.u.form == form for a in (f.ar or ())})
            rader_.append(f"- {form} → {vem}: {n} ({ar[0] if ar else '?'}–{ar[-1] if ar else '?'})")
    # Gärningar: regesten bredvid tolkningen
    rader_ += ["", "## Gärningar ur regesterna (stickprov)", "",
               "| brev | regest | gärning | utfärdare | mottagare | värde | ort |", "|---|---|---|---|---|---|---|"]
    per_brev = defaultdict(lambda: {"utfardare": [], "mottagare": [], "adressat": []})
    for f in fk:
        if f.entitet and f.entitet not in per_brev[f.verk][f.roll]:
            per_brev[f.verk][f.roll].append(f.entitet)
    for nr in slump.sample(sorted(resultat["garningar"]), min(60, len(resultat["garningar"]))):
        g = resultat["garningar"][nr]
        rader_.append(f"| {nr} | {resultat['regesttext'].get(nr, '')[:160]} | {g.predikat} | "
                      f"{', '.join(per_brev[nr]['utfardare'])} | {', '.join(per_brev[nr]['mottagare']) or g.mottagare or '–'} | "
                      f"{(g.egendom or '')[:80]}{' för ' + g.pris if g.pris else ''} | {g.ort or ''} |")
    # Missiv och svar: regesten bredvid adressaten och det besvarade brevet
    brevformer = resultat["brevformer"]
    rader_ += ["", "## Missivens adressater (stickprov)", "", "| brev | regest | utfärdare | adressat |", "|---|---|---|---|"]
    for verk in slump.sample(sorted(brevformer), min(40, len(brevformer))):
        rader_.append(f"| {verk} | {resultat['regesttext'].get(verk, '')[:140]} | {', '.join(per_brev[verk]['utfardare'])} | "
                      f"{', '.join(per_brev[verk]['adressat']) or brevformer[verk].adressat or '–'} |")
    kopplingar = svarskopplingar(resultat, per_brev)
    svar = sorted(v for v, b in brevformer.items() if b.svar)
    rader_ += ["", f"## Svar på tidigare brev ({len(svar)}, varav {len(kopplingar)} kopplade)", "",
               "| brev | regest | hänvisning | besvarat brev | grad |", "|---|---|---|---|---|"]
    for verk in svar:
        b = brevformer[verk]
        besvarat, grad, _ = kopplingar.get(verk, ("–", "", ""))
        rader_.append(f"| {verk} | {resultat['regesttext'].get(verk, '')[:140]} | {b.hanvisning or ''} | {besvarat} | {grad} |")
    (katalog / "stickprov_sdhk.md").write_text("\n".join(rader_) + "\n", encoding="utf-8")
    with open(katalog / "otolkade_sdhk.tsv", "w", encoding="utf-8") as fil:
        for nr, falt, otolkat in resultat["otolkade"]:
            fil.write(f"{nr}\t{falt}\t{' | '.join(otolkat)}\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--rapport", type=Path, help="katalog för stickprov och otolkade fält")
    parser.add_argument("--torr", action="store_true", help="skriv inget till databasen")
    args = parser.parse_args()

    db.initiera_schema()
    conn = db._hamta_db()
    try:
        resultat = bygg(conn)
    finally:
        conn.close()
    for k, v in sorted(resultat["stat"].items()):
        log.info("%s: %d", k, v)
    if args.rapport:
        skriv_rapport(resultat, args.rapport)
    if not args.torr:
        ladda_pastaenden(resultat)
        resultat["register"].spara()


if __name__ == "__main__":
    main()

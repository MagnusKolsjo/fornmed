"""
Tolkar regesterna i Diplomatarium Norvegicum: utfärdaren, huvudgärningen, missivets
adressat och om brevet svarar på ett tidigare brev.

DN saknar ett utfärdarfält. Utfärdaren är regestens subjekt, före huvudverbet:
"Biskop Olaf af Bergen udsteder Pas …", "Kong Erik av Norge skriver til Edward I …".
Regesterna i band 1–18 är skrivna på 1800-talsdanska, de i band 19–23 på nutida norska.
Subjektet skrivs om till SDHK:s svenska form ("Biskop Olaf i Bergen", "Kung Erik av
Norge") och tolkas sedan med samma regler som SDHK:s och DF:s utfärdarfält, så att
samma person och samma ämbete känns igen i alla tre samlingarna.

Vittnesbreven ("To Mænd kundgjöre, at Gudmund Amundssön solgte til Andres Ogmundssön
…") har okända utfärdare. Där är gärningen den som vittnena intygar, och dess subjekt
och mottagare tas ur at-satsen.

Användning (prov):
    python dn_regester.py            # tolka ett stickprov ur dev-databasen
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from regest_garningar import Brevform, Garning, HEDERSORD

# -----------------------------------------------------------------------------
# Stavning och titlar
# -----------------------------------------------------------------------------

# Patronymikon och vanliga namnformer i svensk form, så att "Erling Vidkunssön" och
# "Erling Vidkunsson" blir samma namn
NAMNSTAVNING = [
    (re.compile(r"s?s[öø]n\b"), "sson"), (re.compile(r"s?sen\b(?=[ ,.;)]|$)"), "sson"),
    (re.compile(r"datter\b"), "dotter"), (re.compile(r"døtter\b"), "döttrar"),
    (re.compile(r"Aa"), "Å"), (re.compile(r"aa"), "å"), (re.compile(r"ø"), "ö"), (re.compile(r"Ø"), "Ö"),
    (re.compile(r"æ"), "ä"), (re.compile(r"Æ"), "Ä"),
    # Regenternas namn som i regent- och personlistorna
    (re.compile(r"\bChrist"), "Krist"), (re.compile(r"\bEirik\b"), "Erik"), (re.compile(r"\bOlaf\b"), "Olav"),
    (re.compile(r"\bFrederik\b"), "Fredrik"),
]

# Titel och ämbete: dansk och norsk form → SDHK:s svenska. Ordning: längre former först.
TITLAR_DN = [
    (r"Erkebiskop(?:pen)?|Erkebisp(?:en)?|erkebiskop(?:en)?|erkebisp(?:en)?", "ärkebiskop"),
    (r"[Bb]iskop(?:pen)?|[Bb]isp(?:en)?", "biskop"),
    (r"[Kk]ong(?:en)?|[Kk]onge(?:n)?|[Kk]onning", "kung"),
    (r"[Dd]ronning(?:en)?", "drottning"),
    (r"[Hh]ertug(?:en)?", "hertig"), (r"[Hh]ertuginde|[Hh]ertuginne", "hertiginna"),
    (r"[Pp]ave(?:n)?", "påve"), (r"[Kk]ardinal(?:en)?", "kardinal"),
    (r"[Aa]bbed(?:en)?|[Aa]bbat", "abbot"), (r"[Aa]bbedisse(?:n)?|[Aa]bbedissen", "abbedissa"),
    (r"[Pp]rovst(?:en)?|[Pp]rost(?:en)?", "prost"), (r"[Dd]omprovst(?:en)?|[Dd]omprost(?:en)?", "domprost"),
    (r"[Kk]annik(?:en)?|[Kk]orsbroder(?:en)?|[Cc]horsbroder(?:en)?|[Kk]orsbror(?:en)?", "kanik"),
    (r"[Ss]ogneprest(?:en)?|[Ss]okneprest(?:en)?|[Ss]ognepræst(?:en)?", "kyrkoherde"),
    (r"[Pp]rest(?:en)?|[Pp]ræst(?:en)?", "präst"),
    (r"[Ll]agmand(?:en)?|[Ll]agmann(?:en)?", "lagman"),
    (r"[Ff]oged(?:en)?|[Ff]ogd(?:en)?|[Uu]nderfoged(?:en)?", "fogde"),
    (r"[Ss]ysselmand(?:en)?|[Ss]ysselmann(?:en)?", "fogde"),
    (r"[Hh]øvedsmand(?:en)?|[Hh]øvedsmann(?:en)?|[Hh]övedsmand(?:en)?|[Hh]ovedsmand(?:en)?", "hövitsman"),
    (r"[Ll]ensmand(?:en)?|[Ll]ensmann(?:en)?", "länsman"),
    (r"[Bb]efalingsmand(?:en)?|[Bb]efalingsmann(?:en)?", "hövitsman"),
    (r"[Rr]iges [Ff]orstander|[Rr]igsforstander(?:en)?|[Rr]iksforstander(?:en)?", "riksföreståndare"),
    (r"[Rr]idder(?:en)?", "riddare"), (r"[Vv]æbner(?:en)?|[Vv]epner(?:en)?|[Vv]æbnere", "väpnare"),
    (r"[Rr]aadmand(?:en)?|[Rr]ådmann(?:en)?|[Rr]aadmænd(?:ene)?|[Rr]ådmenn(?:ene)?", "rådman"),
    (r"[Bb]orgermester(?:en)?|[Bb]orgemester(?:en)?", "borgmästare"),
    (r"[Kk]ants?ler(?:en)?|[Kk]ansler(?:en)?", "kansler"),
    (r"[Dd]rotsete(?:n)?|[Dd]rottsete(?:n)?|[Dd]rost(?:en)?", "drots"), (r"[Mm]arsk(?:en)?", "marsk"),
    (r"[Rr]igsraad|[Rr]iksråd", "riksråd"), (r"[Hh]r\.?|[Hh]err", "herr"), (r"[Ff]ru|[Ff]rue", "fru"),
]
_TITEL_DN = [(re.compile(rf"\b(?:{monster})(?=\s|,|$)"), ny) for monster, ny in TITLAR_DN]

INSTITUTIONER_DN = [
    (re.compile(r"^(?:[Dd]et\s+)?norske\s+[Rr]igs?raad|^[Nn]orges\s+[Rr]igs?raad|^(?:[Dd]et\s+)?norske\s+riksråd(?:et)?|^[Nn]orges\s+riksråd"), "Norges riksråd"),
    (re.compile(r"^(?:[Dd]et\s+)?danske\s+[Rr]igs?raad|^(?:[Dd]et\s+)?danske\s+riksråd(?:et)?"), "Danmarks riksråd"),
    (re.compile(r"^(?:[Dd]et\s+)?svenske\s+[Rr]igs?raad|^(?:[Dd]et\s+)?svenske\s+riksråd(?:et)?|^Sveriges riksråd"), "Sveriges riksråd"),
    (re.compile(r"^(?:Borgermestere|Borgermestre|Borgermester|borgermestere|borgermestre|borgermester)(?:ne)?\s+og\s+(?:Raad(?:mænd)?|råd(?:menn)?)(?:et|ene)?\s+(?:i|paa|på)\s+(?P<ort>[A-ZÆØÅ][\wæøåöä-]+)"), "Rådet i {ort}"),
    (re.compile(r"^(?:Raadet|Rådet|Raadmændene|Rådmennene|Byraadet|Byrådet)\s+(?:i|paa|på)\s+(?P<ort>[A-ZÆØÅ][\wæøåöä-]+)"), "Rådet i {ort}"),
    (re.compile(r"^(?:Kapitlet|Kapitelet|Domkapitlet|Domkapitelet|Korsbrødrene|Korsbrödrene|Chorsbrödrene|Kannikerne|Kannikene)\s+(?:i|ved|paa|på)\s+(?:\w+\s+)?(?P<ort>[A-ZÆØÅ][\wæøåöä-]+)"), "Domkapitlet i {ort}"),
]

# Huvudverbet, i nusvensk betydelse, i presens: dansk (band 1–18) och norsk (19–23)
VERB_DN = {
    # vittnesbrev och kungörelser
    "kundgjøre": "kungor", "kundgjöre": "kungor", "kundgjør": "kungor", "kundgjör": "kungor", "kunngjør": "kungor",
    "kunngjøre": "kungor", "vidne": "vittnar", "vidner": "vittnar", "vitner": "vittnar", "bevidne": "vittnar",
    "bevidner": "vittnar", "bevitner": "vittnar", "gjöre": "kungor", "gjør": "kungor",
    "erkjender": "erkanner", "erkjende": "erkanner", "erkjenner": "erkanner", "tilstaar": "erkanner", "tilstår": "erkanner",
    # gärningar
    "sælger": "saljer", "sælge": "saljer", "selger": "saljer", "selge": "saljer",
    "giver": "skanker", "give": "skanker", "gir": "skanker", "skjænker": "skanker", "skjenker": "skanker",
    "mageskifter": "byter", "mageskifte": "byter", "makeskifter": "byter",
    "pantsætter": "pantsatter", "pantsetter": "pantsatter",
    "stadfæster": "stadfaster", "stadfæste": "stadfaster", "stadfester": "stadfaster", "bekræfter": "stadfaster",
    "bekrefter": "stadfaster",
    "bygsler": "upplater", "bygsle": "upplater", "forlener": "forlaner", "forlene": "forlaner",
    "overdrager": "overlater", "overdrar": "overlater", "opdrager": "overlater", "oppdrar": "overlater",
    "testamenterer": "testamenterar", "dømmer": "domer", "dömmer": "domer", "afsiger": "domer", "avsier": "domer",
    "udnævner": "utnamner", "utnevner": "utnamner", "ansætter": "utnamner", "ansetter": "utnamner",
    # missiv
    "skriver": "missiv", "tilskriver": "missiv", "underretter": "missiv", "beder": "missiv", "ber": "missiv",
    "takker": "missiv", "anmoder": "missiv", "befaler": "missiv", "paalægger": "missiv", "pålegger": "missiv",
    "minder": "missiv", "minner": "missiv", "meddeler": "missiv", "melder": "missiv", "lover": "missiv",
    "svarer": "missiv", "besvarer": "missiv", "advarer": "missiv", "formaner": "missiv", "opfordrer": "missiv",
    "oppfordrer": "missiv", "klager": "missiv", "beklager": "missiv", "tilsender": "missiv", "sender": "missiv",
    "beretter": "missiv", "oversender": "missiv", "forsikrer": "missiv", "lykønsker": "missiv", "indbyder": "missiv",
    "innbyr": "missiv", "anbefaler": "missiv", "forlanger": "missiv", "kræver": "missiv", "krever": "missiv",
    # flertal: "Borgermestere og Raad i Lübeck berette", "Kapittel og Presteskab besvare"
    "besvare": "missiv", "svare": "missiv", "berette": "missiv", "underrette": "missiv", "tilskrive": "missiv",
    "bede": "missiv", "takke": "missiv", "melde": "missiv", "meddele": "missiv", "tilkjendegive": "missiv",
    "tilkjendegiver": "missiv", "erklære": "missiv", "erklærer": "missiv",
}
PREDIKAT = {"saljer", "skanker", "byter", "pantsatter", "stadfaster", "upplater", "forlaner", "overlater",
            "testamenterar", "domer", "utnamner"}
_VERB = re.compile(r"\b(" + "|".join(sorted(VERB_DN, key=len, reverse=True)) + r")\b")

# Gärningen i at-satsen, i preteritum: "at X solgte til Y …"
PRETERITUM_DN = {
    "solgte": "saljer", "solgt": "saljer", "gav": "skanker", "gave": "skanker", "givet": "skanker", "skjænkede": "skanker",
    "skjenket": "skanker", "mageskiftede": "byter", "mageskiftet": "byter", "makeskiftet": "byter", "makeskiftede": "byter",
    "pantsatte": "pantsatter", "pantsat": "pantsatter", "pantsatt": "pantsatter", "bygslede": "upplater",
    "bygslet": "upplater", "overdrog": "overlater", "overdro": "overlater", "opgav": "overlater", "oppga": "overlater",
}
_AT_SATS = re.compile(r"\b(?:at|att)\s+(?P<subj>(?:(?!\bat\b).){2,160}?)\s+(?:(?:har|havde|hadde|have)\s+)?(?P<verb>"
                      + "|".join(sorted(PRETERITUM_DN, key=len, reverse=True)) + r")\b(?P<rest>.*)$")

_MOTTAGARE_SLUT = (r"(?=,? (?:\d|[½¼¾]|en |et |ett |sin |sit |sine |hans |hendes |hennes |deres |all |alt |alle |halv|"
                   r"hvad |hva |det |den |de |noget |noe |hele |"
                   r"Gaard|gård|Jord|jord|Part|part|Bol|bol|Öres|øres|Mærke|mark|for |med |mod |mot |paa |på |i |om )|[.;:]|$)")
_TIL = re.compile(r"^(?:\s*til\s+)(?P<adr>.{2,140}?)" + _MOTTAGARE_SLUT)

# Svar: "Svar paa", "svarer", "besvarer", "modtaget hans Brev", "mottatt hans brev"
_BREV_DN = r"(?:Brev|brev|Breve|brevet|Skrivelse|skrivelse|Skrivelser|Klage|Forespørgsel|Forespörgsel|Begjæring|Anmodning|melding)"
SVAR_DN = re.compile(r"\b(?:besvarer|besvare|svarer|svare|Svar paa|svar på|Svar på|Modtagelsen af|mottakelsen av|"
                     r"(?:modtaget|modtog|mottatt|mottok|fik|fikk)\s+(?:[\wæøåöä.()]+\s+){0,4}?" + _BREV_DN + r")\b")
# Adressaten i svaret: "besvarer et brev fra fru Anne Rud", "svarer på kong Frederik IIs brev",
# "erkjender Modtagelsen af et Brev fra Dronning (Elisabet) af 24 April"
_SVAR_FRA = re.compile(r"\b(?:besvar\w*|svar\w*(?:\s+på|\s+paa)?|Modtagelsen af|mottakelsen av|modtaget|mottatt|mottok|modtog)\s+"
                       r"(?:et|ett|to|tre|hans|hendes|deres|dennes|det)?\s*" + _BREV_DN + r"\w*\s+(?:fra|frå|af)\s+"
                       r"(?P<adr>(?:sin overordnede\s+)?(?:[Hh]r\.?\s+|[Hh]err\s+|[Ff]ru\s+|[Kk]ong(?:en)?\s+|[Dd]ronning\s+|"
                       r"[Bb]iskop(?:en)?\s+|[Ee]rkebiskop(?:en)?\s+|[Ee]rkebisp(?:en)?\s+)?"
                       r"(?:[A-ZÆØÅ(]|i\s+[A-ZÆØÅ])[^,;:]{1,80}?)"
                       r"(?=,? (?:(?:om|at|og|med|der|som|hvori|hvor|angaaende|angående|ang\.)\b|(?:af|av) \d)|[.;:,]|$)")
_SVAR_GENITIV_DN = re.compile(r"\b(?:besvar\w*|svar\w*(?:\s+på|\s+paa)?|modtaget|mottatt)\s+(?P<adr>(?:[Hh]r\.?\s+|[Hh]err\s+|"
                              r"[Ff]ru\s+|[Kk]ong\s+|[Dd]ronning\s+|[Bb]iskop\s+|[Ee]rkebiskop\s+)?[A-ZÆØÅ][\wæøåöä]+"
                              r"(?:\s+[A-ZÆØÅIVX][\wæøåöä.]*){0,3}?)(?:\.s|s|'s)\s+(?:[\wæøåöä]+\s+){0,6}?" + _BREV_DN + r"\b")
_MANAD_DN = {"januar": 1, "februar": 2, "marts": 3, "mars": 3, "april": 4, "mai": 5, "maj": 5, "juni": 6, "juli": 7,
             "august": 8, "september": 9, "oktober": 10, "october": 10, "november": 11, "december": 12, "desember": 12}
HANVISNING_DN = re.compile(r"(?:Brev|brev|Skrivelse|skrivelse)\w*(?:\s+fra\s+[^,;.]{1,60}?)?\s+(?:af|av|dat\.|dateret|datert)\s+(?:den\s+)?(\d{1,2})\.?\s+("
                           + "|".join(_MANAD_DN) + r")(?:\s+(\d{4}))?", re.I)


# -----------------------------------------------------------------------------
# Omskrivning
# -----------------------------------------------------------------------------


def svensk_stavning(text: str) -> str:
    for monster, ny in NAMNSTAVNING:
        text = monster.sub(ny, text)
    return text


PAVE_UTAN_TITEL = re.compile(r"^(?:Honorius|Innocentius|Gregorius|Alexander|Clemens|Clement|Bonifacius|Urban|Martin|"
                             r"Martinus|Eugenius|Nikolaus|Nicolaus|Calixtus|Callixtus|Pius|Paulus|Sixtus|Leo|Hadrianus|"
                             r"Julius|Benedikt|Benedictus|Johannes|Celestinus|Coelestin|Lucius|Anastasius|Eugen)\s+[IVXL]+\b")


def svensk_form(led: str) -> str:
    """Ett subjekt eller en mottagare i SDHK:s svenska form: titlar, 'af' → 'i', stavning."""
    s = led.strip(" ,")
    # "samt to Andre", "og flere andre": utfärdarna är fler än de namngivna
    s = re.sub(r",?\s+(?:samt|og)\s+(?:to|tre|fire|fem|flere|nogle|noen|\d+)\s+[Aa]ndre\b.*$", " m.fl.", s)
    for monster, ny in INSTITUTIONER_DN:
        if (m := monster.match(s)):
            return ny.format(**m.groupdict())
    # Danskan skriver substantiv med stor bokstav ("Thord Eirikssön Lagmand i Oslo"); titeln får
    # stor bokstav bara först i ledet, annars tolkas den som ett efternamn
    s = re.sub(r"\b(?:ud|ut)valgt(?:e)?\s+", "", s)
    for monster, ny in _TITEL_DN:
        s = monster.sub(lambda m: ny.capitalize() if m.start() == 0 else ny, s)
    s = re.sub(r"\b(kung|drottning|hertig)\s+til\s+", r"\1 av ", s)
    if PAVE_UTAN_TITEL.match(s):
        s = "Påve " + s
    # "Biskop Olaf af Bergen" → "i Bergen"; men "Kung Erik av Norge" behåller riket
    s = re.sub(r"\b(?:af|av)\s+(Norge|Danmark|Sverige|England|Skottland|Frankrike|Mecklenburg|Pommern|Holsten|Slesvig)\b",
               "\x00\\1", s)
    s = re.sub(r"\b(?:af|av|ved)\s+(?=[A-ZÆØÅ])", "i ", s).replace("\x00", "av ")
    s = re.sub(r"\b(?:paa|på)\s+(?=[A-ZÆØÅ])", "på ", s)
    s = re.sub(r"\b(?:og)\b", "och", s)
    return svensk_stavning(s)


def _utan_parentes(s: str) -> str:
    """'(Herr Vincens Lunge och herr Nils Lykke)': utgivaren har härlett hela subjektet."""
    return s[1:-1] if s.startswith("(") and s.endswith(")") and s.count("(") == 1 else s


@dataclass
class DnTolkning:
    utfardare: str | None          # i SDHK:s form, för tolka()
    vittnen: bool                  # vittnesbrev med okända utfärdare
    garning: Garning | None
    garning_subjekt: str | None    # gärningens subjekt när det inte är utfärdaren (vittnesbrev)
    brevform: Brevform | None


VITTNEN = re.compile(r"^(?:\d+|To|Tre|Fire|Fem|Seks|Sex|Syv|Otte|Ni|Ti|Tolv|En Del|Nogle|Flere|to|tre|fire|fem|seks|"
                     r"syv|åtte|ni|ti|tolv|noen|flere)\s+(?:svorne\s+|svorne\s+)?(?:Mænd|Mend|menn|Lagrettemænd|lagrettemenn|"
                     r"Lagrettesmænd|Raadmænd|Bönder|bønder|Prester|prester|Mænd\s+\w+)\b")


# Egendom med stor bokstav ("sælger Gaarden Guldengene") är inte en mottagare
_EGENDOM_DN = (r"(?!(?:Gaard|Gaarden|Gaardene|Gård|Gården|Gårdene|Jord|Jorden|Jordegods|Part|Parten|Halvdel|Halvdelen|"
               r"Hus|Huset|Ejendom|Eiendom|Mølle|Møllen|Kvern|Fiske|Fisket|Skog|Skogen|Teig|Teigen|Øde|Ødegaard|"
               r"Laks|Laksefiske|Grund|Grunden|Tomt|Tomten|Sæter|Seter|Bygsel|Bygselen|Rente|Renten|Landskyld)\b)")
_DIREKT = re.compile(r"^\s+" + _EGENDOM_DN + r"(?P<adr>(?:(?:hr\.|herr|Hr\.|Herr|biskop|Biskop|kongen|Kongen)\s+)?[A-ZÆØÅ][\wæøåöä-]+"
                     r"(?:\s+(?:og\s+)?[A-ZÆØÅ][\wæøåöä-]+){0,4})" + _MOTTAGARE_SLUT)


INTE_GAVA_DN = re.compile(r"\b(?:Fuldmagt|fullmakt|Lejde|lejd|Tilladelse|tillatelse|Brev|brev|Kvittering|kvittering|Grid|"
                          r"Fred|Frihed|Frihet|Beskjed|Besked|Ordre|Befaling|Svar|svar|Raad|råd|Løfte|Tilsagn|Pas|pass|"
                          r"Landsvist|Eftergivelse|Afkald|avkall)\b")
_TIL_SENARE = re.compile(r"\btil\s+(?P<adr>(?:(?:[Hh]r\.?|[Hh]err|[Bb]iskop|[Kk]ong(?:en)?|[Kk]annik|[Pp]rest(?:en)?|"
                         r"[Ll]agmand(?:en)?|[Ff]oged(?:en)?|[Hh]ustru|[Ff]ru)\s+)?[A-ZÆØÅ][\wæøåöä-]+(?:\s+(?:og\s+)?"
                         r"[A-ZÆØÅ][\wæøåöä-]+){0,3})(?=[\s,.;:]|$)")


def _garning(predikat: str, rest: str) -> Garning | None:
    if predikat == "skanker" and INTE_GAVA_DN.search(rest[:150]):
        return None
    m = _TIL.match(rest)
    if not m and predikat in ("saljer", "skanker", "byter", "pantsatter", "upplater", "forlaner", "overlater", "testamenterar"):
        # "selger Arne Hallgrimsson 6 månedsmatsbol": mottagaren utan "til"
        m = _DIREKT.match(rest)
    if m and re.search(_EGENDOM_DN.replace("(?!", "(?=").replace(")\\b)", ")\\b)"), " " + m.group("adr")) is None and \
            not re.search(r"\b(?:Gaard|Gaarden|Gård|Gården|Jord|Part|Kirkes|kirkes|Klosters|klosters)\b", m.group("adr")):
        mottagare, egendom = svensk_form(m.group("adr")), rest[m.end():].strip(" ,")
    elif (t := _TIL_SENARE.search(rest)) and predikat not in ("stadfaster", "domer", "utnamner"):
        # "sælger Gaarden Guldengene … til Nils Haavardssön": mottagaren efter egendomen
        mottagare, egendom = svensk_form(t.group("adr")), (rest[:t.start()] + rest[t.end():]).strip(" ,")
    else:
        mottagare, egendom = None, rest.strip(" ,")
    egendom = re.split(r"(?<![Hh]r)[.;]", egendom)[0][:300] or None
    pris = re.search(r"\b(?:for|mod|mot)\s+(\d[^.;,]*)", rest)
    return Garning(predikat, predikat, mottagare, None, egendom, pris.group(1).strip() if pris else None, None)


def _datum(text: str) -> tuple[int, int, int | None] | None:
    if (h := HANVISNING_DN.search(text)):
        return int(h.group(1)), _MANAD_DN[h.group(2).lower()], int(h.group(3)) if h.group(3) else None
    return None


# Förkortningar som inte avslutar meningen
_FORKORTNING = re.compile(r"(?:\b(?:Hr|hr|Dr|dr|St|No|no|Nr|nr|jfr|dvs|ca|Mag|kgl|Kgl|bl|a|o|fl|Hrs|Sr|Mr|Fr|fr|Bp|bp|Erkebp|"
                          r"s|å|f|d|v|ang|resp|ovenf|nedenf|Chr|Joh|Bisk|Mr)\.|\b[A-ZÆØÅ]\.)$")


def forsta_meningen(text: str) -> str:
    for m in re.finditer(r"[.;](?=\s|$)", text):
        if text[m.start()] == ";" or not _FORKORTNING.search(text[:m.end()]):
            return text[:m.start()]
    return text


# Ett verb i presens som inte står i listan: "-er", "-rer" ("kvitterer", "bemyndiger", "forbyder")
_ANNAT_VERB = re.compile(r"\s([a-zæøåäö]{4,}(?:er|ere))\b")
EJ_VERB = {"under", "efter", "etter", "eller", "over", "andre", "ældre", "eldre", "begge", "anden", "andere", "flere",
           "nogle", "hellere", "senere", "tidligere", "biskopper", "brødre", "brödre", "borgere", "bønder", "kanniker",
           "fogeder", "lagmænd", "herrer", "fædre", "mødre", "døtre", "gilder", "kirker", "breve", "parter", "fjerdinger"}


def tolka(regest: str) -> DnTolkning | None:
    mening = forsta_meningen(regest.strip())
    m = _VERB.search(mening)
    ann = next((a for a in _ANNAT_VERB.finditer(mening) if a.group(1) not in EJ_VERB and a.group(1) not in VERB_DN), None)
    # Ett okänt verb före det första kända är huvudverbet ("Hertug Albrecht tilsender …, og beder")
    if m and ann and ann.start() < m.start():
        m = None
    if not m:
        # Ett okänt verb ger ändå utfärdaren, när subjektet står först med stor bokstav
        ann = next((a for a in _ANNAT_VERB.finditer(mening) if a.group(1) not in EJ_VERB), None)
        if not ann or not re.match(r"^[(A-ZÆØÅ]", mening):
            return None
        avs = mening[:ann.start()].strip(" ,")
        if not avs or re.search(r"\b(?:som|der|hvilken|hvilke|at|og)\s*$", avs) or len(avs) > 160:
            return None
        return DnTolkning(None if VITTNEN.match(avs) else svensk_form(_utan_parentes(avs)), bool(VITTNEN.match(avs)), None, None, None)
    if m.start() < 2:
        return None
    avs, verb, rest = mening[:m.start()].strip(" ,"), m.group(1), mening[m.end():]
    # "Hr." och "Dr." är förkortningar, inte meningsslut
    rest = re.sub(r"\b([Hh]r|[Dd]r|St)\.\s*", r"\1 ", rest)
    rest = re.sub(r"\bv\.\s+(?=[A-ZÆØÅ])", "von ", rest)
    if re.search(r"\b(?:som|der|hvilken|hvilke|at|og)\s*$", avs):
        return None
    vittnen = bool(VITTNEN.match(avs))
    utfardare = None if vittnen else svensk_form(_utan_parentes(avs))
    kod = VERB_DN[verb]
    garning = gsubj = brevform = None
    if kod in PREDIKAT:
        garning = _garning(kod, rest)
    elif kod in ("kungor", "vittnar", "erkanner") and (at := _AT_SATS.search(rest)):
        garning = _garning(PRETERITUM_DN[at.group("verb")], at.group("rest"))
        # "hendes Husbond Asbjörn": släktordet hör inte till namnet
        subj = re.sub(r"^(?:hans|hendes|hennes|deres|sin|sine)\s+(?:afdøde\s+|afdöde\s+|avdøde\s+)?(?:Husbond|husbond|"
                      r"Hustru|hustru|Fader|far|Moder|mor|Broder|bror|Søster|Söster|søster|Søn|Sön|sønn|Datter|datter|"
                      r"Svoger|svoger|Frænde|Mand|mann)\s+", "", at.group("subj"))
        gsubj = svensk_form(subj) if garning else None
        # "erkjender at have solgt": gärningen är utfärdarens egen
        if re.match(r"(?:han|hun|de|hon)\b", at.group("subj")) or kod == "erkanner" and re.match(r"\s*(?:at\s+)?ha", rest):
            gsubj = None
    svarsord = bool(SVAR_DN.search(regest[:400]))
    if kod == "missiv" or (not garning and (re.match(r"\s*til\s", rest) or svarsord)):
        adr = None
        if verb in ("skriver",) and (t := re.match(r"\s*til\s+(.{2,140}?)(?=,? (?:og|om|at|med|angaaende|angående|ang\.|for)\b|[.;:,]|$)", rest)):
            adr = t.group(1)
        elif (t := re.match(r"\s*(?:til\s+)?((?:[A-ZÆØÅ(]|hr\.|herr|kong|biskop|erkebiskop|rådet|raadet|borgermester|"
                            r"lagmann|lagmand|høvedsmann|fogden|abbed|kannik)[^,;:]{1,120}?)"
                            r"(?=,? (?:om|at|og|med|for|paa|på|angaaende|angående|ang\.|i anledning|der|som|en|et|ett|"
                            r"nogle|noen|sin|sit|sine|hans|hendes|hennes|deres|den|det|de|ved|til)\b|[.;:]|$)", rest)):
            adr = t.group(1)
        svar = svarsord
        # I ett svar är adressaten den som skrev det besvarade brevet, när regesten säger det
        # Missivets egen adressat ("melder Raadet i Kampen") går före; svarets används när den
        # saknas, är ett ord i genitiv ("besvare Kong Christians … Breve") eller bara ett "et"/"på"
        if svar and ((t := _SVAR_FRA.search(regest[:400])) or (t := _SVAR_GENITIV_DN.search(regest[:400]))) and \
                (not adr or re.match(r"(?:et|ett|på|paa)\b", adr) or adr.startswith(t.group("adr") + "s")):
            adr = re.sub(r"^sin overordnede\s+", "", t.group("adr"))
            # "erkebiskopen i Uppsala, Birger": titeln och sätet räcker
            adr = re.sub(r"^erkebiskopen", "Erkebiskopen", adr)
        if adr:
            adr = re.sub(r"^" + HEDERSORD.pattern[1:], "", adr, flags=re.I)
        if adr or svar:
            brevform = Brevform(svensk_form(adr) if adr else None, svar, None, _datum(regest[:400]) if svar else None)
    return DnTolkning(utfardare, vittnen, garning, gsubj, brevform)


if __name__ == "__main__":
    import random
    import db
    conn = db._hamta_db()
    cur = conn.cursor()
    cur.execute(f"SELECT p.verk_id, p.text FROM {db._prefix()}passage p JOIN {db._prefix()}verk v ON v.id = p.verk_id "
                f"WHERE v.kallsamling_id = 'dn' AND p.typ = 'regest'")
    rader = cur.fetchall()
    random.seed(1)
    for verk, text in random.sample(rader, 40):
        t = tolka(text)
        print(verk, "|", text[:130])
        print("    →", t)

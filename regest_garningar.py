"""
Tolkar huvudgärningen i en SDHK-regest: verbet, mottagaren, egendomen, priset
och orten.

Regesterna följer oftast mönstret

    <utfärdare> säljer till <mottagare> <egendom> i <ort> för <pris>.

Bara regestens första mening läses, och bara när gärningsverbet står tidigt i
den, så att verbet hör till utfärdaren och inte till en bisats om en äldre
överlåtelse ("stadfäster den gåva som X gjort"). Utfärdaren tolkas inte här;
den är redan identifierad ur utfärdarfältet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Verb -> predikat. 'ger' blir en gåva bara när det följs av egendom (se nedan)
VERB = {
    "säljer": "saljer", "skänker": "skanker", "ger": "skanker", "överlåter": "overlater",
    "byter": "byter", "pantsätter": "pantsatter", "testamenterar": "testamenterar",
    "upplåter": "upplater", "förlänar": "forlaner", "stadfäster": "stadfaster", "dömer": "domer",
    "utnämner": "utnamner",
}
VERBMONSTER = re.compile(r"\b(" + "|".join(VERB) + r")\b")

# 'ger' följt av sådant är inte en gåva av egendom
INTE_GAVA = re.compile(r"\b(?:avlat|fullmakt|lejd|kvittens|tillstånd|tillåtelse|befallning|svar|råd|löfte|"
                       r"besked|order|skydd|frihet|frälse|fasta|privilegi|bekräftelse|vidimation|intyg|medgivande|"
                       r"uppdrag|dispens|absolution|nåd|rätt att|makt att)", re.I)

SLAKTORD = (r"(?:hustru|husfru|man|son|söner|dotter|döttrar|bror|bröder|broder|syster|systrar|mor|moder|"
            r"far|fader|svåger|svägerska|måg|svärson|svärmor|svärfar|frände|fränder|kusin|brorson|systerson|"
            r"brorsdotter|systerdotter|morbror|farbror|faster|moster|arvingar|barn|maka|make|styvson|styvdotter)")
# Där mottagarfrasen slutar och egendomen börjar; ett possessiv följt av ett
# släktord hör till mottagaren ("till sin måg Peter Bååt")
EGENDOMSORD = (r"(?:\d|[½¼¾]|en |ett |(?:sin|sitt|sina|hans|hennes|deras) (?!(?:kära |käre |älskade )?" + SLAKTORD +
               r"\b)|all |allt |alla |hela |halva |halvt |hälften |några |något |någon |"
               r"(?:två|tre|fyra|fem|sex|sju|åtta|nio|tio|elva|tolv|tjugo|trettio|fyrtio|femtio|hundra) |"
               r"gård|jord|gods|hus |kvarn|ränt|avgäld|del |andel|rätt |rättighet|torp|äng|skog|fiske|"
               r"tomt|mark |örtug|penning|öre |tunnland|attung|öresland|markland|"
               r"bryggeri|bod |stuga|vad |det |den |de |allt det)")
_SLUT = (r"(?=,? " + EGENDOMSORD + r"|,? för |,? med |,? mot |,? i utbyte|,? på villkor|,? såsom | etc\b|"
         r" och (?:förbinder|lovar|erkänner|kvitterar|tillstår|lägger|tar|förklarar|ber)\b|"
         r", (?:som|vilk\w+|där|varvid|vars)\b|\.|;|$)")
MOTTAGARE = re.compile(r"\b(?:till|åt) (.+?)" + _SLUT)
MOTPART = re.compile(r"\bmed (.+?)" + _SLUT.replace(",? med |", ""))
# Inskott mellan verbet och mottagaren eller egendomen
INSKOTT = re.compile(r"^(?:och sköter|och skötar|och upplåter|tillsammans med .+?(?=,| till | åt )|"
                     r"med (?:sin|sina|hans|hennes|deras)? ?[^,]*?samtycke(?: av .+?(?= till | åt |,))?|"
                     r"med samtycke av .+?(?= till | åt |,)|i öppet brev|på .+? vägnar|på \S+(?: \S+)? ting(?: i enlighet med \S+)?|"
                     r"i närvaro av .+?(?= till | åt |,)|i (?:själa)?gift[^,]*?(?= till | åt |,)|"
                     r"för (?:sin|sina|sitt|hans|hennes) (?:själ|själs)[^,]*?(?= till | åt |,)|i saköre)[, ]*")
PRIS = re.compile(r"\bför (\d[^.;]*?|[a-zåäö]+ (?:mark|öre|örtugar|penningar|fat|läster|tunnor)[^.;]*?)(?=[.;]|, (?:och|varvid|vilket|som)|$)")
ORT = re.compile(r"\bi ((?:\(?[A-ZÅÄÖ][\wåäöé\-]*\)? ?){1,3}?)(?= socken| sn\b| härad| hd\b| i |,| för | och | till |\.| samt| på |$)")
HEDERSORD = re.compile(r"^(?:(?:ärlig|ärliga|välboren|välbördig|hederlig|vördig|vördige|fromme?|beskedlig)\s+(?:och\s+)?)+"
                       r"(?:man|kvinna|herre|herr|fru|hustru)?\s*", re.I)
SLAKT = re.compile(r"^(?:sin|sina|hans|hennes|deras)\s+(?:kära\s+|käre\s+|älskade\s+)?" + SLAKTORD + r",?\s+", re.I)


@dataclass
class Garning:
    verb: str
    predikat: str
    mottagare: str | None      # mottagarfrasen som den står, utan släktord
    slakt: str | None          # släktordet före mottagaren ("sin dotter")
    egendom: str | None
    pris: str | None
    ort: str | None


def forsta_meningen(text: str) -> str:
    # Punkt efter förkortningar och initialer avslutar inte meningen
    m = re.search(r"(?<!\b[A-ZÅÄÖ])(?<!\bsn)(?<!\bhd)(?<!\bbp)(?<!\bSt)(?<!\bS:t)(?<!\bdr)(?<!\bca)(?<!\bang)\.(?:\s|$)", text)
    return text[:m.start()] if m else text


def tolka_garning(regest: str) -> Garning | None:
    mening = forsta_meningen(regest)
    m = VERBMONSTER.search(mening)
    # Verbet ska stå i huvudsatsen, inte i en bisats ("som X sålt", "vilken han gett")
    if not m or re.search(r"\b(?:som|vilk\w+|där|vari|varigenom|varav|varmed|sedan|då|att)\b[^,]*$",
                          mening[:m.start()]):
        return None
    verb = m.group(1)
    rest = mening[m.end():].strip()
    while (ik := INSKOTT.match(rest)) and ik.end() > 0:
        rest = rest[ik.end():].strip()
    if verb == "ger" and (INTE_GAVA.search(rest[:120]) or not re.search(r"\b(?:till|åt)\b", rest)):
        return None

    mottagare = slakt = None
    mm = (MOTPART.search(rest) or MOTTAGARE.search(rest)) if verb == "byter" else MOTTAGARE.search(rest)
    if mm is None and verb in ("skänker", "ger", "överlåter", "testamenterar") and SLAKT.match(rest):
        # "skänker sin dotter Ramborg gården X": mottagaren utan 'till'
        mm = re.match(r"(" + SLAKT.pattern[1:] + r".+?)" + _SLUT, rest, re.I)
    if mm and verb not in ("dömer", "stadfäster"):
        mottagare = mm.group(1).strip(" ,")
        s = SLAKT.match(mottagare)
        if s:
            slakt = s.group(0).strip(" ,")
            mottagare = mottagare[s.end():]
        # Släktord och hedersord framför senare mottagare och efter kommatecken
        mottagare = re.sub(r"(,\s*|\boch\s+)(?:sin|sina|hans|hennes|deras)\s+(?:kära\s+|käre\s+)?" + SLAKTORD + r"\s+",
                           r"\1", mottagare)
        mottagare = re.sub(r"(^|,\s*|\boch\s+)" + HEDERSORD.pattern[1:], r"\1", mottagare, flags=re.I)
        mottagare = re.sub(r"\s+", " ", mottagare).strip(" ,")
        # Ett citerat gårdsnamn direkt efter kyrkan eller klostret är egendomen
        mottagare = re.sub(r"\b(kloster|klostret|kyrka|kapell|altare|konvent|kapitel)\s+”.*$", r"\1", mottagare)
        rest_utan = (rest[:mm.start()] + rest[mm.end():]).strip(" ,")
    else:
        rest_utan = rest
    if verb == "utnämner":
        # "utnämner X till fogde på Y": den utnämnde står före 'till', ämbetet efter
        u = re.match(r"(.+?) till (.+)", rest)
        if u:
            mottagare, rest_utan = u.group(1).strip(" ,"), u.group(2)

    rest_utan = re.sub(r"\s+,", ",", re.sub(r"\s+", " ", rest_utan))
    pris = None
    pm = PRIS.search(rest_utan)
    if pm:
        pris = pm.group(1).strip(" ,")
        egendom = rest_utan[:pm.start()].strip(" ,")
    else:
        egendom = rest_utan.strip(" ,")
    om = ORT.search(egendom or "")
    ort = om.group(1).strip(" ()") if om else None
    # Socken och härad står i genitiv ("i Revsunds sn")
    if ort and om and re.match(r" (?:socken|sn|härad|hd)\b", egendom[om.end():]) and len(ort) > 4 and ort.endswith("s"):
        ort = ort[:-1]
    if ort and ort.split()[0] in ("Sverige", "Danmark", "Norge"):
        ort = None
    return Garning(verb, VERB[verb], mottagare or None, slakt, egendom[:300] or None, pris, ort)


# -----------------------------------------------------------------------------
# Brevets adressat och svar på tidigare brev
# -----------------------------------------------------------------------------
# Missiv har ingen gärning utan en adressat: "Rådet i Åbo till det i Lübeck angående
# ...", "Ärkebiskop Jakob till herr Sten Kristersson att ...", "Erik Trolle meddelar
# Sten Sture att ...". Regesten säger ibland också att brevet svarar på ett tidigare:
# "med svar på dennes skrivelse av 28 maj", "att man mottagit dennes brev av den 9 juni",
# "Biskop Magnus svarar biskopen i Strängnäs".

MANADSNAMN = {"januari": 1, "februari": 2, "mars": 3, "april": 4, "maj": 5, "juni": 6, "juli": 7,
              "augusti": 8, "september": 9, "oktober": 10, "november": 11, "december": 12}
_MANAD = r"(" + "|".join(MANADSNAMN) + r"|jan|febr?|apr|aug|sept?|okt|nov|dec)\.?"
_KORT = {"jan": 1, "feb": 2, "febr": 2, "apr": 4, "aug": 8, "sep": 9, "sept": 9, "okt": 10, "nov": 11, "dec": 12}

# Verb som tar adressaten som objekt ("meddelar Sten Sture att")
ADRESSVERB = r"(?:svarar|besvarar|meddelar|underrättar|tackar|ber|anmodar|uppmanar|befaller|varnar|förmanar|lyckönskar|tillskriver)"
# Före "till" i ett missiv står bara avsändaren: inga verb eller bisatser
INTE_AVSANDARE = re.compile(r"\b(?:att|som|vilk\w+|kungör|kungöra|förbinder|förbinda|ger|giver|skänker|säljer|lovar|"
                            r"tillstår|erkänner|stadfäster|överlåter|upplåter|pantsätter|byter|dömer|utnämner|"
                            r"intygar|vittnar|bekräftar|förklarar|befullmäktigar|gör|har|hade|sänder|sände|skickar|"
                            r"inger|framför|överlämnar|återlämna\w*|kallar|kallas|varit|är|blir|hänvisar|hänskjuter|"
                            r"frisäger|vidimerar|upprättar|avger|avlägger|bemöter|uppbär|bekänner|utfärdar|utställer|"
                            r"lämnar|donerar|förordnar|förordar|besöker|utser|sköter|översänder|förnyar|kvitterar|"
                            r"anhåller|reserverar|rekommenderar|anbefaller|inbjuder|uttalar|bemyndigar|avsäger|utlovar|"
                            r"providerar|återställer|uppgör|tilldelar|förlänar|befriar|tillåter|beviljar|förbjuder|"
                            r"\w*(?:byter|träder|förskriver|arrenderar|säljer|giver|dömer|låter|ställer|sänder|lägger|"
                            r"tager|tar|betalar|lovar|ber|meddelar|svarar|tackar|befaller|underrättar))\b|;"
                            # "bröder till", "dotter till": släktskap, inte adress
                            r"|\b(?:bröder|broder|bror|son|söner|dotter|döttrar|hustru|änka|frände|fränder|måg|syster|"
                            r"fader|far|moder|mor|arvinge|arvingar|fullmäktig\w*|ombud)$")
_ADRESSAT_SLUT = (r"(?=,? (?:med|om|att|angående|ang(?=\.)|rörande|beträffande|i anledning av|som svar|med anledning|på (?:hans|hennes|deras|dennes|"
                  r"dess|sin|sina|adressatens)|för (?:hans|hennes|deras|dennes|det|den|att)|och (?:ber|meddelar|tackar|"
                  r"begär|förklarar|lovar|beklagar|underrättar|uppmanar|anhåller|förmanar|svarar))\b|\s+\(|[.;:]|$)")
MISSIV = re.compile(r"^(?P<avs>.{2,140}?)\s+(?:skriver |skrev |hemställer |vänder sig |sänder brev |(?:meddelar|skriver) i (?:ett )?brev )?till "
                    r"(?P<adr>.{2,160}?)" + _ADRESSAT_SLUT)
BREV_FRAN = re.compile(r"^Brev från (?P<avs>.{2,120}?) till (?P<adr>.{2,160}?)" + _ADRESSAT_SLUT)
ADRESSVERB_MONSTER = re.compile(r"^(?P<avs>.{2,140}?)\s+" + ADRESSVERB + r"\s+(?P<adr>(?!att\b|om\b|sig\b|därom\b|på\b|ett\b|det\b|"
                                r"brev\w*\b|skrivelse\w*\b).{2,160}?)" + _ADRESSAT_SLUT.replace("(?=,? (?:", "(?=,? (?:för|på|", 1))
# "svarar på rådets i Danzig brev", "besvarar Vincens Lunges skrivelse": adressaten i genitiv
SVAR_GENITIV = re.compile(r"^(?P<avs>.{2,140}?)\s+(?:be)?svarar(?: på)? (?!(?:ett|en|det|de|dess|hans|hennes|deras)\b)"
                          r"(?P<adr>[A-ZÅÄÖa-zåäö](?:(?! (?:på|med|om|att|av|för|och|angående|beträffande|som) )[^,;.])*?)s(?P<par> \([^)]*\))?(?P<i> i [A-ZÅÄÖ][\wåäö-]+)? "
                          r"(?:senaste |sista |två |tre )?(?:brev|skrivelse|förfrågan|begäran|anmodan|uppmaning|"
                          r"klagomål|förslag|anhållan)\b")
# "besvarar ett brev från Ernst van Dotzem": adressaten är det besvarade brevets avsändare
SVAR_FRAN = re.compile(r"^(?P<avs>.{2,140}?)\s+(?:besvarar|svarar på) (?:ett |en |det |hans |deras |två |tre |de )?"
                       r"(?:brev|skrivelse|förfrågan|begäran)\w* (?:i)?från (?P<adr>.{2,160}?)"
                       r"(?=,?\s+(?:i vilk\w+|vari|vilk\w+|som|där|angående|gällande|om|med|och|att|ang\.|rörande)\b|[.;:]|$)")

_POSSESSIV = r"(?:dennes|dess|hans|hennes|deras|adressatens|rådets|ert|edert|eder|deras senaste|hans senaste)"
SVAR = re.compile(r"\b(?:svarar|besvarar)\b(?! för\b)|\bsvar (?:på|till) " + _POSSESSIV + r"|\bmottagit " + _POSSESSIV +
                  r"\s+(?:\w+\s+){0,3}?(?:brev|skrivelse|bud|budskap|kallelse|svar|förfrågan|begäran)|\b" + _POSSESSIV + r" \(?(?:i )?(?:brev|skrivelse)\w*\s+(?:av|daterat?|dat\.)\s+(?:den\s+)?\d")
NEKAT = re.compile(r"\b(?:inte|ej|icke|utan|aldrig|ännu ej|ännu inte)\s+(?:\w+\s+){0,3}$")
HANVISNING = re.compile(r"(?:" + _POSSESSIV + r"\s+)?\(?(?:i\s+)?(?:brev|skrivelse)\w*\s+(?:av|daterat?|dat\.)\s+"
                        r"(?:den\s+)?(\d{1,2})\s+" + _MANAD + r"(?:\s+(\d{4}))?(\s+samma år|\s+i år)?")
# "brev, daterat 24/9 (1429)", "skrivelse (25/1 1528 …)": dag och månad med snedstreck
HANVISNING_SNED = re.compile(r"(?:brev|skrivelse)\w*,?\s+\(?(?:av\s+|daterat?\s+|dat\.\s+)?(?:den\s+)?"
                             r"(\d{1,2})/(\d{1,2})(?:\s+\(?(1[1-5]\d\d)\)?)?")
# SDHK skriver ibland datumet som åååammdd: "hans brev 12990404"
HANVISNING_TAL = re.compile(r"(?:" + _POSSESSIV + r"\s+)?(?:brev|skrivelse)\w*\s+(?:av\s+|daterat?\s+)?(1[1-5]\d\d)(\d\d)(\d\d)\b")


@dataclass
class Brevform:
    adressat: str | None             # adressatfrasen som den står
    svar: bool                       # regesten säger att brevet svarar på ett tidigare
    hanvisning: str | None           # "dennes skrivelse av 28 maj"
    datum: tuple[int, int, int | None] | None   # det besvarade brevets dag, månad och år
    # Utgivarens hänvisningar till andra brev: ('sdhk', 23220), ('df', 1823) eller ('egen', 5257).
    # Det kan vara det besvarade brevet men också ett annat brev som regesten nämner.
    nummer: list[tuple[str, int]] = field(default_factory=list)


# Utgivarens hänvisning till ett brev: "(SDHK nr 23220)", "(se FMU 1823)" (= DF 1823), i DF "(n:o 1,574)"
NUMMER_SDHK = re.compile(r"\bSDHK nr\.?\s*(\d+)")
NUMMER_FMU = re.compile(r"\bFMU\s+(?:nr\.?\s*)?(\d+)")
NUMMER_EGEN = re.compile(r"\bn:o\s*(\d{1,2}[ ,.]\d{3}|\d+)")


def _manad(s: str) -> int:
    s = s.lower().rstrip(".")
    return MANADSNAMN.get(s) or _KORT[s]


def tolka_brevform(regest: str) -> Brevform | None:
    """Adressaten i ett missiv och om brevet svarar på ett tidigare brev; None om regesten inte säger något om det."""
    mening = forsta_meningen(regest)
    adressat = None
    for monster in (BREV_FRAN, SVAR_FRAN, SVAR_GENITIV, MISSIV, ADRESSVERB_MONSTER):
        m = monster.match(mening)
        if not m:
            continue
        avs, adr = m.group("avs"), re.sub(r"\s+", " ", m.group("adr")).strip(" ,")
        # Utgivarens hänvisning efter namnet hör inte till adressaten: "(se DS nr 9279 ovan)"
        adr = re.sub(r"\s*\((?:se|jfr|jämför|DS|SDHK|FMU|HR|nr|n:o)\b[^)]*\)\s*$", "", adr)
        if monster is SVAR_GENITIV:
            # "rådets i Danzig" → "rådet i Danzig", "Vincens Lunges" → "Vincens Lunge"
            adr = adr + (m.group("par") or "") + (m.group("i") or "")
        if INTE_AVSANDARE.search(avs) or VERBMONSTER.search(avs):
            continue
        # En adressat som själv innehåller ett verb är en gärning ("till Venngarn bekräftar ...")
        if INTE_AVSANDARE.search(adr) or VERBMONSTER.search(adr):
            continue
        adressat = re.sub(r"^" + HEDERSORD.pattern[1:], "", adr, flags=re.I).strip(" ,")
        break
    svar = False
    # Svaret står i regestens början: de två första meningarna
    borjan = mening + regest[len(mening):][:1] + forsta_meningen(regest[len(mening) + 1:].lstrip())
    for m in SVAR.finditer(borjan):
        if not NEKAT.search(borjan[max(0, m.start() - 40):m.start()]):
            svar = True
            break
    hanvisning = datum = None
    if svar and (h := HANVISNING.search(borjan)):
        hanvisning = h.group(0).strip(" (")
        datum = (int(h.group(1)), _manad(h.group(2)), int(h.group(3)) if h.group(3) else None)
    elif svar and (h := HANVISNING_SNED.search(borjan)) and 1 <= int(h.group(2)) <= 12 and 1 <= int(h.group(1)) <= 31:
        hanvisning = h.group(0).strip(" (,")
        datum = (int(h.group(1)), int(h.group(2)), int(h.group(3)) if h.group(3) else None)
    elif svar and (h := HANVISNING_TAL.search(borjan)) and 1 <= int(h.group(2)) <= 12 and 1 <= int(h.group(3)) <= 31:
        hanvisning = h.group(0)
        datum = (int(h.group(3)), int(h.group(2)), int(h.group(1)))
    nummer = []
    if svar:
        nummer = [("sdhk", int(n)) for n in NUMMER_SDHK.findall(borjan)] + \
                 [("df", int(n)) for n in NUMMER_FMU.findall(borjan)] + \
                 [("egen", int(re.sub(r"\D", "", n))) for n in NUMMER_EGEN.findall(borjan)]
    if not adressat and not svar:
        return None
    return Brevform(adressat or None, svar, hanvisning, datum, nummer)

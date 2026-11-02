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
from dataclasses import dataclass

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
    m = re.search(r"(?<!\b[A-ZÅÄÖ])(?<!\bsn)(?<!\bhd)(?<!\bbp)(?<!\bSt)(?<!\bS:t)(?<!\bdr)(?<!\bca)\.(?:\s|$)", text)
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

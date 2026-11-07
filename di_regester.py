"""
Tolkar rubrikerna i Diplomatarium Islandicum: utfärdaren, missivets adressat, svar och
gärningens parter, så långt rubriken anger dem.

DI har ingen regest utan en kort isländsk rubrik ur bandens innehållsförteckning. Bara
en del av rubrikerna nämner utfärdaren, och då på två sätt:

- med subjekt och verb: "Marteinn byskup Einarsson fær Daða Guðmundssyni innheimtu …",
  "Þorsteinn lögmaðr Eyjólfsson staðfestir máldaga …";
- med dokumenttypen följd av utfärdaren i genitiv: "Bannsakabréf Jóns biskups
  Haldórssonar", "Bréf Hamborgarráðs til Kristjáns konungs", "Gjafabréf Jóns Íslendings".

Rubriker som "Kaupbréf um Hraunhafnarbakka" eller "Máldagi Saxahvolskirkju" nämner
ingen utfärdare och ger inga påståenden här. "Bréf sama til sama" ("brev från samme till
samme") får föregående brevs parter.

Namnen skrivs om till nominativ med enkla regler för fornisländskans böjning ("Jóns" →
"Jón", "Ögmundar" → "Ögmundr", "Haldórssonar" → "Haldórsson", "Ingibjargar" →
"Ingibjörg") och titlarna till SDHK:s svenska ("biskups" → "Biskop"), så att samma
regler och samma id-register gäller som för de andra samlingarna. Reglerna är grova: ett
namn som de inte känner igen behåller sin form.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from regest_garningar import Brevform, Garning

# Titel i nominativ eller genitiv → SDHK:s svenska form
TITLAR_DI = {
    "biskup": "biskop", "biskups": "biskop", "byskup": "biskop", "byskups": "biskop", "biskupi": "biskop",
    "erkibiskup": "ärkebiskop", "erkibiskups": "ärkebiskop", "erkibyskup": "ärkebiskop", "erkibyskups": "ärkebiskop",
    "ábóti": "abbot", "ábóta": "abbot", "abbadís": "abbedissa", "abbadísar": "abbedissa",
    "príor": "prior", "príors": "prior", "prófastr": "prost", "prófasts": "prost", "prófastur": "prost",
    "prestr": "präst", "prests": "präst", "prestur": "präst",
    "lögmaðr": "lagman", "lögmanns": "lagman", "lögmaður": "lagman",
    "hirðstjóri": "hövitsman", "hirðstjóra": "hövitsman", "höfuðsmaðr": "hövitsman", "höfuðsmanns": "hövitsman",
    "sýslumaðr": "fogde", "sýslumanns": "fogde", "umboðsmaðr": "fogde", "umboðsmanns": "fogde",
    "konungr": "kung", "konungs": "kung", "kóngr": "kung", "kongr": "kung", "kongs": "kung", "konungur": "kung",
    "konúngr": "kung", "konúngs": "kung", "kóngs": "kung", "kóngur": "kung",
    "drottning": "drottning", "drottningar": "drottning", "páfi": "påve", "páfa": "påve",
    "riddari": "riddare", "riddara": "riddare", "herra": "herr", "síra": "herr", "séra": "herr",
    "kardínáli": "kardinal", "kardínála": "kardinal", "hertogi": "hertig", "hertoga": "hertig",
    "ráðsmaðr": "fogde", "ráðsmanns": "fogde",
}
# Sammansättningar med sätet: "Hólabiskupi", "Skálholtsbiskups", "Einglakonungs"
SAMMANSATT = re.compile(r"^(?P<ort>[A-ZÁÉÍÓÚÝÞÆÖ][\wáéíóúýþæöð]+?)(?P<titel>biskup\w*|byskup\w*|konung\w*|kongs?|ábóta?|"
                        r"lögmanns?|lögmaðr)$")
SATE = {"noregs": "Norge", "hóla": "Hólar", "skálholts": "Skálholt", "skálholt": "Skálholt", "einglа": "England", "eingla": "England",
        "engla": "England", "noregs": "Norge", "danmerkr": "Danmark", "dana": "Danmark", "svía": "Sverige",
        "niðaróss": "Nidaros", "björgvinjar": "Bergen"}
# Orter i dativ efter "í"/"á"
ORTER_DATIV = {"skálholti": "Skálholt", "hólum": "Hólar", "niðarósi": "Nidaros", "björgvin": "Bergen", "þingeyrum": "Þingeyrar",
               "möðruvöllum": "Möðruvellir", "munkaþverá": "Munkaþverá", "helgafelli": "Helgafell", "viðey": "Viðey",
               "þykkvabæ": "Þykkvibær", "kirkjubæ": "Kirkjubær", "reynistað": "Reynistaður", "pommern": "Pommern"}
# Regenternas namn som i regentlistan
REGENTNAMN = {"eiríkr": "Erik", "eiríks": "Erik", "hákon": "Håkon", "hákonar": "Håkon", "magnús": "Magnus",
              "magnúsar": "Magnus", "kristján": "Kristian", "kristjáns": "Kristian", "kristiern": "Kristiern",
              "ólafr": "Olav", "ólafs": "Olav", "friðrik": "Fredrik", "friðriks": "Fredrik", "kristófer": "Kristoffer",
              "kristófers": "Kristoffer", "hans": "Hans", "margrét": "Margareta", "margrétar": "Margareta",
              "henrik": "Henrik", "henriks": "Henrik", "henrek": "Henrik", "henreks": "Henrik", "henrekr": "Henrik", "karl": "Karl", "karls": "Karl", "elisabet": "Elisabet",
              "elisabetar": "Elisabet", "sverrir": "Sverre", "sverris": "Sverre", "kristopher": "Kristoffer",
              "kristophers": "Kristoffer", "kristjàn": "Kristian", "kristjàns": "Kristian", "nikulás": "Nikolaus",
              "nikulásar": "Nikolaus", "jóhann": "Johan", "jóhanns": "Johan", "valdimar": "Valdemar",
              "valdimars": "Valdemar", "hinrik": "Henrik", "hinriks": "Henrik", "kristín": "Kristina"}
# Kvinnonamn vars genitiv slutar på -ar: "Ingibjargar", "Guðrúnar", "Margrétar"
KVINNA = re.compile(r"(?:rún|gerð|gerðr|björg|bjarg|dís|laug|vör|hild|veig|ey|rét|fríð|frið|ný|ríð|unn|ný|borg|leif|elín|"
                    r"katrín|kristín|sigríð|helg|ólöf|þóra|þórdís|halld)$", re.I)
VERB_DI = {
    "staðfestir": "stadfaster", "selr": "saljer", "selur": "saljer", "gefr": "skanker", "gefur": "skanker",
    "dæmir": "domer", "dæma": "domer", "skipar": "utnamner", "byggir": "upplater", "léngir": "forlaner",
    "lénar": "forlaner", "arfleiðir": "testamenterar", "kvittar": "kungor", "lofar": "kungor", "vottar": "kungor",
    "lýsir": "kungor", "játar": "kungor", "sver": "kungor", "fær": "overlater", "afhendir": "overlater",
    "veitir": "forlaner", "leggr": "missiv", "leggur": "missiv", "skrifar": "missiv", "biðr": "missiv", "biður": "missiv",
    "býðr": "missiv", "býður": "missiv", "bannar": "missiv", "sendir": "missiv", "tilkynnir": "missiv",
    "svarar": "missiv", "þakkar": "missiv", "áminnir": "missiv", "skipar fyrir": "missiv", "fyrirbýðr": "missiv",
    "leyfir": "missiv", "kærir": "missiv", "samþykkir": "kungor", "setr": "kungor", "setur": "kungor",
}
PREDIKAT = {"stadfaster", "saljer", "skanker", "domer", "utnamner", "upplater", "forlaner", "testamenterar", "overlater"}
_VERB = re.compile(r"\s(" + "|".join(sorted(VERB_DI, key=len, reverse=True)) + r")\b")
DOKUMENT = re.compile(r"^(?:Bréf|Bréfságrip|Ágrip af bréfi|Bannsakabréf|Bannsbréf|Gjafabréf|Prófentubréf|Leyfisbréf|"
                      r"Verndarbréf|Umboðsbréf|Kvittunarbréf|Kvittun|Kvittan|Skipan|Úrskurðr|Dómr|Lögfesta|Lýsing|"
                      r"Vitnisburðr|Vitnisburðarbréf|Testamentisbréf|Testamenti|Erfðaskrá|Konungsbréf|Svar|Afsalsbréf|"
                      r"Forboðunarbréf|Skipunarbréf|Veitingarbréf|Staðfesting|Samþykkt|Yfirlýsing|Kæra|Kærubréf|"
                      r"Áminningarbréf|Boðsbréf|Fyrirboðsbréf|Sendibréf|Tilskipan|Réttarbót|Hirðstjórabréf|"
                      r"Biskupsbréf|Páfabréf)\s+(?P<resten>.+)$")
# Ett led i genitiv: namn och titel, till ett ord som inleder något annat ("um", "til", "fyrir")
_LED_SLUT = r"(?=\s+(?:um|til|fyrir|yfir|handa|að|á|í|við|vegna|upp á|út af|eptir|eftir|með|frá|sem|er|,)\b|[,.;]|$)"


# Namn som slutar på -s redan i nominativ, och vars genitiv har samma form
NOMINATIV_S = {"hans", "magnús", "nikulás", "klemens", "jóhannes", "andrés", "tómas", "mattías", "markús", "lárus",
               "nikolás", "jónas", "bartholomeus", "erasmus", "dionysius"}


def _nominativ_namn(ord_: str) -> str:
    """Ett namn i genitiv i nominativ, så gott reglerna räcker."""
    o = ord_
    lag = o.lower()
    # Latinska namn ("Gregorius", "Bonifacius") böjs inte på isländskt sätt
    if lag in NOMINATIV_S or lag.endswith("us"):
        return o
    if lag.endswith("sonar"):
        return o[:-2]
    if lag.endswith("dóttur"):
        return o[:-2] + "ir"
    if lag.endswith("ar"):
        stam = o[:-2]
        if KVINNA.search(stam):
            return stam.replace("bjarg", "björg")
        # "Hákonar" → "Hákon": efter n faller nominativens -r bort
        return stam if stam.endswith("n") else stam + "r"
    if lag.endswith("s") and len(o) > 3:
        stam = o[:-1]
        return stam if re.search(r"[nlrs]$", stam) else stam + "r"
    if lag.endswith("a") and len(o) > 3:
        return o[:-1] + "i"
    # Kvinnonamn på -a har genitiv på -u: "Halldóru" → "Halldóra"
    if lag.endswith("u") and len(o) > 3:
        return o[:-1] + "a"
    return o


def svensk_form(led: str, genitiv: bool, dativ: bool = False) -> str:
    """Ett led ur rubriken i SDHK:s form, en eller flera personer förenade med "og"."""
    delar = [d for d in re.split(r"\s+(?:og|ok)\s+", led) if d.strip()]
    former = [_en_person(_dativ(d) if dativ else d, genitiv and not dativ) for d in delar]
    return " och ".join(f for f in former if f)


def _en_person(led: str, genitiv: bool) -> str:
    """En person ur rubriken i SDHK:s form: titel först, namnen i nominativ."""
    ord_ = re.findall(r"\(?[\wáéíóúýþæöðÁÉÍÓÚÝÞÆÖÐ.'-]+\)?", led)
    titlar, namn, orter = [], [], []
    kung = False
    efter_prep = None
    for o in ord_:
        lag = o.lower().strip("()")
        # "í Skálholti", "á Hólum", "af Pommern": orten, i nominativ där den är känd
        if lag in ("í", "á", "af", "frá", "i"):
            efter_prep = lag
            continue
        if efter_prep and o[0].isupper():
            plats = SATE.get(lag) or ORTER_DATIV.get(lag) or (o[:-1] if lag.endswith("i") and len(o) > 4 else o)
            orter.append(("av " if efter_prep == "af" else "i ") + plats)
            efter_prep = None
            continue
        efter_prep = None
        if lag in TITLAR_DI:
            titlar.append(TITLAR_DI[lag])
            kung = kung or TITLAR_DI[lag] in ("kung", "drottning")
            continue
        if (m := SAMMANSATT.match(o)) and not o[0].islower():
            t = TITLAR_DI.get(re.sub(r"i$", "", m.group("titel").lower()), TITLAR_DI.get(m.group("titel").lower()))
            if t:
                titlar.append(t)
                ort = SATE.get(m.group("ort").lower())
                kung = kung or t == "kung"
                if ort:
                    orter.append(("av " if t == "kung" else "i ") + ort)
                continue
        if lag in ("hins", "hinn", "hinna", "hin", "og", "officialis", "officiali"):
            continue
        # Riket i genitiv: "Magnús Erlíngsson Noregs konúngr"
        if lag in SATE and SATE[lag] in ("Norge", "Danmark", "Sverige", "England"):
            orter.append("av " + SATE[lag])
            continue
        if re.fullmatch(r"[a-záéíóúýþæöð]+", lag) and not o[0].isupper():
            continue
        namn.append(o)
    original = list(namn)
    if genitiv:
        namn = [_nominativ_namn(n) if not n.startswith("(") else n for n in namn]
    if kung or "påve" in titlar:
        namn = [REGENTNAMN.get(o.lower(), REGENTNAMN.get(n.lower(), n)) for o, n in zip(original, namn)]
    if not namn and not titlar:
        return ""
    titel = titlar[0].capitalize() + " " if titlar else ""
    rest = " ".join(t for t in titlar[1:] if t not in ("herr",))
    form = (titel + " ".join(namn) + (" " + " ".join(orter) if orter else "")).strip()
    return form + (f", {rest}" if rest else "")


@dataclass
class DiTolkning:
    utfardare: str | None
    garning: Garning | None
    brevform: Brevform | None
    sama: bool                       # "sama til sama": föregående brevs utfärdare och adressat
    sama_utfardare: bool = False     # "Bréf sama til presta": föregående brevs utfärdare


NUMMER_DI = re.compile(r"\bNr\.?\s*(\d+)")


def tolka(rubrik: str) -> DiTolkning | None:
    r = re.sub(r"^\[[^\]]*\]\.?\s*|^[A-ZÁÉÍÓÚÝÞÆÖ][\wáéíóúýþæöð ]{2,25}\.\s+(?=[A-ZÁÉÍÓÚÝÞÆÖ])", "", rubrik.strip())
    if re.match(r"^(?:Bréf|Sendibréf|Bréfságrip)?\s*sama til sama\b", r, re.I) or re.match(r"^Samskonar", r):
        return DiTolkning(None, None, None, True)
    if (m := re.match(r"^(?:Bréf|Sendibréf|Bréfságrip)\s+sama\s+til\s+(?P<adr>.+?)" + _LED_SLUT.replace("til|", ""), r)):
        adr = svensk_form(m.group("adr"), genitiv=True) or None
        return DiTolkning(None, None, Brevform(adr, False, None, None, []), False, True)
    svar = bool(re.match(r"^Svar\b|.*\bsvarbréf", r, re.I))
    nummer = [("egen", int(n)) for n in NUMMER_DI.findall(r)] if svar else []
    # Dokumenttypen följd av utfärdaren i genitiv
    if (d := DOKUMENT.match(r)):
        resten = d.group("resten")
        if re.match(r"(?:um|upp á|út af|fyrir|á|í|til|eptir|eftir|milli|að)\b", resten):
            if svar or nummer:
                return DiTolkning(None, None, Brevform(None, svar, None, None, nummer), False)
            return None
        # Utfärdaren börjar med ett namn eller en titel, inte med ett verb ("Dómr skyldar …")
        forsta = resten.split()[0].strip("()").lower() if resten.split() else ""
        if not (resten[0].isupper() or resten[0] == "(" or forsta in TITLAR_DI):
            return None
        m = re.match(r"(?P<utf>.+?)" + _LED_SLUT, resten)
        utf = svensk_form(m.group("utf"), genitiv=True) if m else ""
        adressat = None
        # Adressaten står direkt efter utfärdaren: "Bréf Jóns biskups til Alþingis"
        if m and (t := re.match(r"\s+(?P<prep>til handa|til|handa)\s+(?P<adr>.+?)" + _LED_SLUT.replace("til|", "").replace("handa|", ""),
                                resten[m.end():])):
            # "til" styr genitiv, "handa" dativ
            adressat = svensk_form(t.group("adr"), genitiv=True, dativ="handa" in t.group("prep")) or None
        brevform = Brevform(adressat, svar, None, None, nummer) if (adressat or svar) else None
        return DiTolkning(utf or None, None, brevform, False)
    # Subjekt och verb i presens
    if (v := _VERB.search(r)) and v.start() < 80:
        subj = r[:v.start()]
        if not re.match(r"^[A-ZÁÉÍÓÚÝÞÆÖþ]", subj) or re.search(r"\b(?:sem|er|að)\s*$", subj):
            return None
        # En dom som "Tylftardómr, kvaddr af Ormi lögmanni" utfärdas av nämnden, inte av en person
        if re.search(r"dómr|dómur|nefnd|bréf|^Skrá|^Minnisgrein|^Reikningr", subj, re.I):
            return None
        utf = svensk_form(subj, genitiv=False)
        kod = VERB_DI[v.group(1)]
        rest = r[v.end():]
        garning = brevform = None
        if kod in PREDIKAT:
            # Mottagaren står i dativ direkt efter verbet ("fær Daða Guðmundssyni …")
            mott = re.match(r"\s+(?P<m>(?:(?:síra|séra|herra)\s+)?[A-ZÁÉÍÓÚÝÞÆÖ][\wáéíóúýþæöð]+(?:\s+[A-ZÁÉÍÓÚÝÞÆÖ][\wáéíóúýþæöð]+)?)", rest)
            garning = Garning(kod, kod, svensk_form(mott.group("m"), genitiv=False, dativ=True) if mott else None, None,
                              (rest[mott.end():] if mott else rest).strip()[:300] or None, None, None)
        elif kod == "missiv":
            mott = re.match(r"\s+(?:fyrir\s+)?(?P<m>[A-ZÁÉÍÓÚÝÞÆÖ][\wáéíóúýþæöð]+(?:\s+[A-ZÁÉÍÓÚÝÞÆÖ][\wáéíóúýþæöð]+)?)", rest)
            brevform = Brevform(svensk_form(mott.group("m"), genitiv=False, dativ=True) if mott else None, svar or v.group(1) == "svarar", None, None, nummer)
        return DiTolkning(utf or None, garning, brevform, False)
    return None


def _dativ(namn: str) -> str:
    """'Daða Guðmundssyni' → 'Daði Guðmundsson', 'Jóni' → 'Jón'."""
    ut = []
    for o in namn.split():
        lag = o.lower()
        if lag in TITLAR_DI or not o[0].isupper():
            ut.append(o)
        elif lag.endswith("syni"):
            ut.append(o[:-4] + "son")
        elif lag.endswith("dóttur"):
            ut.append(o[:-2] + "ir")
        elif lag.endswith("i") and len(o) > 3 and not lag.endswith("ði") or lag.endswith("ni"):
            ut.append(o[:-1])
        elif lag.endswith("a") and len(o) > 3:
            ut.append(o[:-1] + "i")
        else:
            ut.append(o)
    return " ".join(ut)


if __name__ == "__main__":
    import random
    import db
    cur = db._hamta_db().cursor()
    cur.execute(f"SELECT p.verk_id, p.text FROM {db._prefix()}passage p JOIN {db._prefix()}verk v ON v.id = p.verk_id "
                f"WHERE v.kallsamling_id = 'di' AND p.typ = 'regest'")
    rader = cur.fetchall()
    random.seed(3)
    for verk, text in random.sample(rader, 50):
        print(verk, "|", text[:110], "\n    →", tolka(text))

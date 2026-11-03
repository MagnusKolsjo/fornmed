"""
Kopplar verkens och auktoritetslängdernas geografiska platser till entiteter.

Plats betyder här geografisk plats i vid bemärkelse: rike, landskap, härad,
socken, stad, gård, kloster och fyndplats. Källornas platser står som text på
tre ställen, och här blir de kopplingar till entiteter:

- brevens ort i SDHK (verk.utfardandeort) blir rollen utfardandeort i verk_plats,
- runinskrifternas plats (fyndplats, socken, härad, kommun, område och nuvarande
  förvaring i verk.extra) blir egna roller i verk_plats,
- sätet i auktoritetslängderna (auktoritet_titel.sate) blir sate_id.

Källans ordalydelse behålls alltid, i namnform och i de ursprungliga fälten.
Ortfältet i SDHK tolkas med regler: "(Lübeck.)" och "[Stockholm]" är Lübeck och
Stockholm, markerade som härledda; "Rom?" är osäkert; "Tälje (= Södertälje)" är
Södertälje med Tälje som namnform; "Visby eller Riga" blir två osäkra kopplingar
och "Skanör och Falsterbo" två säkra; "Rom, Peterskyrkan" och "Peterskyrkan, Rom"
blir "Peterskyrkan i Rom". Tolkningen är medvetet försiktig: en form som inte
känns igen blir en egen plats med sin form som namn.

Kopplingen går på namnet och avgör därför inte vilken plats ett vanligt namn
avser. Alla brev från en ort som heter Vik hamnar på samma entitet. Runinskrifternas
socknar och kommuner kopplas i stället till platsregistrets socknar och kommuner,
med landskapet som avgränsning, och deras härader och fyndplatser har område i
id:t. Fyndplatsens koordinater, socken och kommun sparas i plats_uppgift.

Förvaringen är fritext på engelska. Museer känns igen med data/platser/
forvaringsplatser.tsv och blir egna platser. "In the church porch" anger läget
i förhållande till platsen och kopplas till socknen eller fyndplatsen, markerat
som härlett. "At Dagsnäs, Bjärka parish" kopplas till socknen. Annan fritext
kopplas inte och finns kvar i verk.extra.

Vilken nutida plats ett brevorts namn avser står i data/platser/orter.tsv: orter
med minst två brev eller med en socken som namne, bedömda av två oberoende språkmodeller. Bara det de är överens
om kommer dit; resten står i orter_att_avgora.tsv och väntar på mer underlag.
Ett namn som avser en enda plats får sina uppgifter i plats_uppgift med metoden
sprakmodell och granskad falsk. Ett namn som delas av flera platser förblir en
allmän entitet, med socknarna och Wikidatas platser som möjliga identifieringar.
I data/platser/delade_orter.json är breven fördelade brev för brev på egna
entiteter (Viborg i Jylland och i Karelen), och breven påståenden följer med.

Ortfältet och regesterna ger ibland text som inte är ett platsnamn. I ortfältet
tas ord som "trol." och "vid" bort när resten är en känd ort. En plats vars namn
börjar med en känd ort och fortsätter med annat ("Roskilde ombud till mötet i
Halmstad") ersätts av orten. I "X i Y" är X platsen och Y bara sammanhang:
X blir en sökbar namnform, och Y används för att hitta X bland landskapets socknar.
Bara en plats inne i en ort ("Bredgatan i Lund") ingår i orten och får dess läge
som närmevärde. Land och landskap ger aldrig något läge, eftersom gränser flyttas
och en punkt mitt i Gotland inte säger var Klinteholm ligger. X som har slagits
upp i Wikidata (en enda plats med namnet nära Y, genomläst) står i x_uppslag.tsv
och har sitt eget läge. Står socknen i brevet ("Eksjö (Vallsjö sn)",
"gården X i Y socken", "Romfartuna kyrka") knyts platsen till socknen och får dess
läge som närmevärde, om socknen går att bestämma entydigt. Det avgörs brev för brev:
ett namn med flera brev får en egen plats per socken, "Viby (Hassle socken)". Kan platsen hittas i de historiska registren och
brevet nämner häradet (platslexikon.py), eller två oberoende bedömare har valt samma
kandidat utifrån breven (brevgranskning.tsv), knyts brevet till den platsen. Text som inte alls anger en plats ("på kung Eriks vägnar") märks med slaget ej_plats och kopplas
bort från påståendena. Entiteterna och deras id:n finns kvar.

Befintliga entiteter skrivs aldrig över och tas aldrig bort, så deras id:n är
stabila. Nya platser får id:n som bildas av namnet. Kopplingarna byggs om vid
varje körning. Kör platsregister.py först, och kör det här skriptet efter varje
import av SDHK, runinskrifter eller auktoriteter.

Användning:
    python platser.py
    python platser.py --rapport rapport.txt     # former som blev egna platser
"""

import argparse
import csv
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

import db
from fragor import _rader
from normalisering import ordform
from pastaenden_sdhk import _slug

log = logging.getLogger("platser")

# Ortfältet säger uttryckligen att orten saknas
UTAN_ORT = {"u.o", "u. o", "uo", "?", "", "okänd", "utan ort", "oläslig ort", "oviss ort", "svenska"}

# Ord före ortnamnet i ortfältet. Första gruppen gör orten osäker.
OSAKER_FORE = re.compile(r"^(?:trol|antagl)\.?\s+(.+)$", re.I)
UTAN_ORT_MEN = re.compile(r"^utan ort /(.+)/$", re.I)
ORD_FORE = re.compile(r"^(?:(?:på|paa|pa|uppå|i|vid|wedh|ved|utanför|framför|a|in)\s+)?"
                      r"(?:(?:in )?castro(?: nostro| regis)?\s+|villa(?: nostra)?\s+|curia\s+|monte\s+|borgen\s+|slottet\s+|gården\s+|sin sätesgård\s+)?"
                      r"(.+)$", re.I)

# Namn som ska granskas: långa, med gemen begynnelse eller med siffror
MISSTANKT = re.compile(r"^[a-zåäö]|\d|^.{31,}$")
EJ_PLATS = re.compile(r"\bvägn|^samma |^minoriterna$|^(?:herr|väpnaren|kung|fru) ", re.I)
X_OCH_Y = re.compile(r"^(.+?)\s+(i|på|vid)\s+([A-ZÅÄÖ][\w-]*(?: [a-zåäö]*(?:härad|hundare|socken))?)\s*$")
# Slutar X så här är hela X en plats, inte ett ortnamn följt av en titel
BYGGNAD = re.compile(r"(kyrka|kloster|slott|gård|hus|borg|holm|gata|stuga|ting)\w*$", re.I)
# Indelningar som aldrig ger en plats dess läge
REGION = {"land", "landskap", "lan", "omrade"}
# Ord som inleder ett längre namn och inte är en ort i sig
INLEDANDE_ORD = {"norra", "södra", "östra", "västra", "övre", "nedre", "stora", "lilla", "gamla", "nya", "s:t", "s:ta", "sankt", "sankta"}

# Id:n som aldrig slås upp på enbart namnet
EJ_PA_NAMN = ("plats:runa:", "plats:socken:", "plats:kommun:", "plats:lan:", "plats:wd:", "plats:museum:")

# Rundata räknar Skåne, Blekinge och Halland till Danmark. Socknarna där finns i
# RAÄ:s auktoriteter, under landskapen.
GAMLA_DANSKA = ("Skåne", "Blekinge", "Halland")

KATALOG = Path(__file__).parent / "data" / "platser"
RAA_FIL = KATALOG / "raa_geo.json"
WIKIDATA_FIL = KATALOG / "wikidata_fakta.json"
ORTFIL = KATALOG / "orter.tsv"
DELADE_FIL = KATALOG / "delade_orter.json"
FORVARINGSFIL = KATALOG / "forvaringsplatser.tsv"
UPPSLAGSFIL = KATALOG / "x_uppslag.tsv"
LEXIKONFIL = KATALOG / "lexikon_beslut.tsv"
GRANSKNINGSFIL = KATALOG / "brevgranskning.tsv"
KORRIGERINGSFIL = KATALOG / "platskorrigeringar.tsv"
SAMMANSLAGNINGSFIL = KATALOG / "platssammanslagningar.tsv"
DEL_AV_ORT = re.compile(r"^plats:sdhk:[^:]+:[^:]+$")
BEDOMARE = "Fornmeds platsregister"

# Läget anges i förhållande till kyrkan eller fyndplatsen, inte som en egen plats
RELATIVT_LAGE = re.compile(
    r"^(now |set |built |fastened |leaning |moved |kept |lying |standing )?(in|on|at|into|under|over|above|below|beside|near|by|against|outside|inside|w of|e of|n of|s of|north|south|east|west)?\b.*"
    r"\b(church|churchyard|chancel|porch|tower|nave|sacristy|vestry|choir|transept|lychgate|altar|mortuary chapel|rectory|parish hall|parish storehouse|ruin)\b",
    re.I)
SAKNAS = re.compile(r"\b(missing|lost|destroyed|disappeared|stolen|private ownership|whereabouts)\b", re.I)
I_SOCKEN = re.compile(r",\s*([^,]+?)s? parish\b", re.I)

INDELNING = re.compile(r"\b(härad|hundare|socken|sn|hd|lagsaga|land|län|fylke|skeppslag|tingslag|kommun)\b")

# Runinskrifter utanför Sverige har landet som område; kommuner och härader med
# samma namn i olika länder hålls isär med det
LAND = {"Norge", "Danmark", "England", "Isle of Man", "Irland", "Skottland", "Island", "Grönland",
        "Frankrike", "Tyskland", "Ryssland", "Finland", "Färöarna", "Orkney", "Shetland", "Nederländerna",
        "Polen", "Lettland", "Estland", "Ukraina", "Schweiz", "Italien", "Grekland", "Turkiet"}


def _enkel(namn: str) -> bool:
    """Ett namn utan beskrivande ord, så att 'och' och 'eller' verkligen skiljer två platser."""
    return bool(re.fullmatch(r"[A-ZÅÄÖÆØÞ][\w’'-]*(?: [A-ZÅÄÖÆØÞ][\w’'-]*)?", namn))


def tolka_ort(text: str, kanda: frozenset[str] = frozenset()) -> list[dict]:
    """Ortfältet som en lista av platser: namn, osäker, härledd och historisk namnform.

    `kanda` är vanliga orter (ordform), som avgör vilken del av "A, B" som är orten.
    Tom lista betyder att fältet inte anger någon ort.
    """
    t = text.strip()
    osaker = "?" in t
    harledd = False

    # "Tälje (= Södertälje)", "”Hersama” (=Häradshammar)", "Mons Gratie (Bayern) [=Gnadenberg]"
    historisk = None
    if lika := re.search(r"[(\[]\s*=\s*([^)\]]+)(?:[)\]]|$)", t):
        historisk = t[:lika.start()].strip(" ”\"")
        t = lika.group(1).strip()
        historisk = re.sub(r"\s*[(\[].*$", "", historisk).strip() or None

    t = t.replace("?", "").strip()
    # Hela fältet inom parentes eller hakparentes: orten är härledd
    while (m := re.fullmatch(r"[(\[]([^()\[\]]*)[)\]]\.?", t)):
        t, harledd = m.group(1).strip(), True
    # "”Lästa”; ”in placito iusticiarum”": det första ledet är orten
    t = t.split(";")[0]
    t = t.rstrip(". ").strip("”\" ")
    if t.casefold() in UTAN_ORT:
        return []

    # "(Söder-)Tälje" och "Ärkebiskopsgården på (Biskops-)Arnö"
    t = re.sub(r"\(([^()]*)-\)(\w)(\w*)", lambda m: m.group(1) + m.group(2).lower() + m.group(3), t)
    # "(Österrekarnes)tingsplats"
    t = re.sub(r"^\(([^()]+)\)(?=\w)", r"\1 ", t)
    # "Eksjö (Vallsjö sn, Västra härad, Njudung)": parentesen förklarar orten
    t = re.sub(r"\s*[(\[][^()\[\]]*[)\]]\s*$", "", t).strip().strip("”\" ")
    if not t:
        return []

    for ord_, osakert in ((" eller ", True), (" och ", False)):
        if ord_ in t:
            delar = t.split(ord_)
            if len(delar) == 2 and all(_enkel(d.strip()) for d in delar):
                return [{"namn": d.strip(), "osaker": osaker or osakert, "harledd": harledd, "historisk": None}
                        for d in delar]

    # "Eksjö, Vallsjö sn, Västra härad": resten förklarar orten
    forsta, _, resten = t.partition(",")
    if resten and INDELNING.search(resten):
        t = forsta.strip()

    # "Rom, Peterskyrkan" och "Gråbrödraklostret, Stockholm" blir "X i Rom"
    if t.count(",") == 1:
        a, b = (d.strip() for d in t.split(","))
        if a and b:
            if ordform(a) in kanda and ordform(b) not in kanda:
                t = f"{b[0].upper()}{b[1:]} i {a}"
            elif ordform(b) in kanda and ordform(a) not in kanda:
                t = f"{a[0].upper()}{a[1:]} i {b}"

    return [{"namn": t, "osaker": osaker, "harledd": harledd, "historisk": historisk}]


class Platsregister:
    """Slår upp namn bland platserna och samlar nya entiteter och namnformer."""

    def __init__(self) -> None:
        self.per_form: dict[str, str] = {}
        self.befintliga: set[str] = set()
        for r in _rader(f"SELECT id, namn FROM {db._prefix()}entitet WHERE typ IN ('plats', 'indelning')"):
            self.befintliga.add(r["id"])
            # Runinskrifternas särhållna platser slås aldrig upp på namn: Lund i
            # Björklinge ska inte bli biskopssätet Lund. Socknarnas namn är inte
            # heller unika och slås upp med landskapet, i socken().
            if r["id"].startswith(EJ_PA_NAMN):
                continue
            nyckel = ordform(r["namn"])
            # Projektets handregistrerade platser går före de ur SDHK
            if nyckel not in self.per_form or self.per_form[nyckel].startswith("plats:sdhk:"):
                self.per_form[nyckel] = r["id"]
        self.alla_id = {r["id"] for r in _rader(f"SELECT id FROM {db._prefix()}entitet")}
        self.nya: dict[str, tuple] = {}
        self.namnformer: set[tuple[str, str]] = set()
        self.uppgifter: dict[str, dict] = {}
        self.wikidata: dict[str, str] = {}
        self.museer = forvaringsplatser()
        self.fakta: dict = json.loads(WIKIDATA_FIL.read_text(encoding="utf-8"))
        self.kommun_per_q = {r["wikidata_id"]: r for r in _rader(
            f"""SELECT e.wikidata_id, u.entitet_id, u.lan_id FROM {db._prefix()}plats_uppgift u
                 JOIN {db._prefix()}entitet e ON e.id = u.entitet_id WHERE u.slag = 'kommun'""")}
        self.socken_per_q = {r["wikidata_id"]: r for r in _rader(
            f"""SELECT e.wikidata_id, u.entitet_id, u.kommun_id, u.lan_id, u.landskap_id FROM {db._prefix()}plats_uppgift u
                 JOIN {db._prefix()}entitet e ON e.id = u.entitet_id WHERE u.slag = 'socken'""")}
        self.identifieringar: dict[str, tuple] = {}
        self.delade: dict[tuple[str, str], str] = {}
        self.flyttade: list[tuple[str, str, str]] = []
        self.runstader: dict[tuple[str, str], str] = {}
        self.ambeten: dict[str, dict[str, str]] = {}
        self.bort: list[str] = []
        self.utan_wikidata: set[str] = set()
        self.ersatta: dict[str, str] = {}
        # Land som fanns före registret har kvar sina id:n, så de hittas på namnet
        land_per_namn = {r["namn"].casefold(): r["id"] for r in _rader(
            f"""SELECT e.id, e.namn FROM {db._prefix()}plats_uppgift u
                 JOIN {db._prefix()}entitet e ON e.id = u.entitet_id WHERE u.slag = 'land'""")}
        raa = json.loads(RAA_FIL.read_text(encoding="utf-8"))
        self.land = {x["kod"]: land_per_namn.get(x["namn"].casefold()) for x in raa["land"]}
        self.socknar: dict[tuple[str, str], tuple] = {}
        self.kommuner: dict[str, tuple] = {}
        for r in _rader(f"""SELECT u.entitet_id, u.slag, u.nutida_namn, u.kommun_id, u.lan_id, u.land_id, u.landskap_id, u.latitud, u.longitud, l.namn AS landskap
                             FROM {db._prefix()}plats_uppgift u LEFT JOIN {db._prefix()}entitet l ON l.id = u.landskap_id
                             WHERE u.slag IN ('socken', 'kommun')"""):
            if r["slag"] == "socken":
                self.socknar[(r["landskap"], ordform(r["nutida_namn"]))] = r
            else:
                self.kommuner[ordform(r["nutida_namn"])] = r
        self.landskap_per_namn = {s["landskap"]: s["landskap_id"] for s in self.socknar.values() if s["landskap"]}

    def ny_institution(self, pid: str, namn: str, wikidata: str | None) -> None:
        if pid not in self.alla_id and pid not in self.nya:
            self.nya[pid] = (pid, "institution", namn, "Museum eller samling som förvarar runinskrifter",
                             json.dumps({}, ensure_ascii=False))
        if wikidata:
            self.wikidata[pid] = wikidata

    def socken(self, landskap: str, text: str) -> dict | None:
        """Socknen i platsregistret, ur Rundatas form: 'Hovs', 'Bondkyrka (nu Uppsala)', 'Sävsjö (Vallsjö)'."""
        forsta = re.sub(r"\s*\(.*$", "", text).strip()
        inom = re.search(r"\((?:nu |f\.d\. |eg\. )?([^)]+)\)", text)
        for namn in (forsta, inom.group(1).strip() if inom else ""):
            for form in (namn, namn[:-1] if namn.endswith("s") else ""):
                if form and (traff := self.socknar.get((landskap, ordform(form)))):
                    return traff
        return None

    def _ny(self, pid: str, namn: str, beskrivning: str, extra: dict | None = None) -> str:
        if pid not in self.alla_id and pid not in self.nya:
            typ = "indelning" if INDELNING.search(namn) else "plats"
            self.nya[pid] = (pid, typ, namn, beskrivning, json.dumps(extra or {}, ensure_ascii=False))
        return pid

    def efter_namn(self, namn: str, prefix: str, beskrivning: str) -> str:
        """Platsen med det här namnet, eller en ny om den saknas."""
        nyckel = ordform(namn)
        if nyckel in self.per_form:
            return self.per_form[nyckel]
        pid = self._ny(f"{prefix}{_slug(namn)}", namn, beskrivning)
        self.per_form[nyckel] = pid
        return pid

    def med_omrade(self, slag: str, omrade: str, namn: str, beskrivning: str, extra: dict | None = None,
                   visningsnamn: str | None = None) -> str:
        """Plats vars namn inte är unikt: området ingår i id:t, så att Hovs sn i två landskap hålls isär."""
        return self._ny(f"plats:runa:{slag}:{_slug(omrade)}:{_slug(namn)}", visningsnamn or namn, beskrivning, extra)


def rensa_ortform(plats: dict, register: Platsregister) -> None:
    """'trol. Kalmar', 'vid Stockholm', 'in castro Holmensi': orten, när resten är en känd ort."""
    namn = plats["namn"]
    if (m := UTAN_ORT_MEN.match(namn)):
        plats.update(namn=m.group(1).strip(), harledd=True)
    elif (m := OSAKER_FORE.match(namn)):
        plats.update(namn=m.group(1).strip(), osaker=True)
    elif (m := ORD_FORE.match(namn)) and m.group(1) != namn and ordform(m.group(1)) in register.per_form:
        plats["namn"] = m.group(1).strip()


def koppla_brev(register: Platsregister, ovanliga: Counter) -> list[tuple]:
    p = db._prefix()
    rader = _rader(f"SELECT id, utfardandeort FROM {p}verk WHERE utfardandeort IS NOT NULL")
    antal = Counter(ordform(r["utfardandeort"].strip("()[]. ")) for r in rader)
    kanda = frozenset(k for k, n in antal.items() if n >= 5)
    kopplingar = {}
    for r in rader:
        for plats in tolka_ort(r["utfardandeort"], kanda):
            rensa_ortform(plats, register)
            pid = register.efter_namn(plats["namn"], "plats:sdhk:", "Ort i SDHK:s ortfält")
            if (delad := register.delade.get((r["id"], ordform(plats["namn"])))):
                register.flyttade.append((r["id"], pid, delad))
                pid = delad
            if pid in register.nya:
                ovanliga[plats["namn"]] += 1
            if plats["historisk"] and ordform(plats["historisk"]) != ordform(plats["namn"]):
                register.namnformer.add((pid, plats["historisk"]))
            kopplingar[(r["id"], "utfardandeort", pid)] = (r["id"], pid, "utfardandeort", r["utfardandeort"],
                                                           plats["osaker"], plats["harledd"])
    return list(kopplingar.values())


def koppla_runor(register: Platsregister) -> list[tuple]:
    p = db._prefix()
    kopplingar = {}
    for r in _rader(f"SELECT id, extra FROM {p}verk WHERE kallsamling_id = 'rundata'"):
        extra = r["extra"] if isinstance(r["extra"], dict) else json.loads(r["extra"] or "{}")
        omrade = (extra.get("omrade") or "okänt område").strip()
        land = omrade if omrade in LAND else "Sverige"

        def lagg_till(roll: str, pid: str, namn: str) -> None:
            kopplingar[(r["id"], roll, pid)] = (r["id"], pid, roll, namn, False, False)

        if extra.get("omrade"):
            lagg_till("omrade", register.efter_namn(omrade, "plats:", "Landskap eller land i Rundata"), omrade)

        kommun = (extra.get("municipality") or "").strip(" ?")
        kommun_post = None
        if kommun:
            kommun_post = register.kommuner.get(ordform(kommun)) if land == "Sverige" or omrade == "Danmark" else None
            if kommun_post:
                lagg_till("kommun", kommun_post["entitet_id"], kommun)
            else:
                pid = register.med_omrade("kommun", land, kommun, f"Nutida kommun i {land}, ur Rundata",
                                          visningsnamn=f"{kommun} kommun")
                lagg_till("kommun", pid, kommun)

        if (harad := (extra.get("district") or "").strip()) and harad != "?":
            lagg_till("harad", register.med_omrade("harad", omrade, harad, f"Härad eller motsvarande i {omrade}, ur Rundata"), harad)

        socken = (extra.get("parish") or "").strip()
        socken_post = None
        if socken and socken != "?":
            if INDELNING.search(socken):
                utan_sn = re.sub(r"\s+sn\b", "", socken)
                landskap = GAMLA_DANSKA if omrade == "Danmark" and kommun_post else (omrade,)
                for namn in landskap:
                    socken_post = socken_post or register.socken(namn, utan_sn)
                pid = socken_post["entitet_id"] if socken_post else \
                    register.med_omrade("socken", omrade, socken, f"Socken i {omrade}, ur Rundata")
            else:
                # Utan "sn" är det en stad, som Lund eller Bergen, och samma plats som i andra källor
                pid = register.runstader.get((omrade, ordform(socken))) or \
                    register.efter_namn(socken, "plats:", f"Stad i {omrade}, ur Rundata")
            lagg_till("socken", pid, socken)

        if (fynd := (extra.get("found_location") or "").strip()) and fynd != "?":
            lat, lon = extra.get("latitude"), extra.get("longitude")
            # Socknen ingår i id:t: Hovs kyrka finns på många håll
            var = socken if socken and socken != "?" else omrade
            pid = register.med_omrade("fyndplats", f"{omrade}_{var}", fynd, f"Fyndplats i {var}, {omrade}, ur Rundata")
            lagg_till("fyndplats", pid, fynd)
            hemma = socken_post or kommun_post
            register.uppgifter[pid] = {
                "slag": "annat", "nutida_namn": fynd, "land_id": hemma["land_id"] if hemma else None,
                "landskap_id": socken_post["landskap_id"] if socken_post else None,
                "lan_id": hemma["lan_id"] if hemma else None,
                "kommun_id": (socken_post["kommun_id"] if socken_post else None) or (kommun_post["entitet_id"] if kommun_post else None),
                "socken_id": socken_post["entitet_id"] if socken_post else None,
                "latitud": float(lat) if lat else None, "longitud": float(lon) if lon else None,
                "kalla": "Rundata", "metod": "regel",
            }

        if (nu := (extra.get("current_location") or "").strip(" .")) and not SAKNAS.search(nu):
            hemmaplats = socken_post["entitet_id"] if socken_post else (pid if fynd and fynd != "?" else None)
            if (museum := forvaring(register, nu)):
                kopplingar[(r["id"], "forvaring", museum)] = (r["id"], museum, "forvaring", nu, False, False)
            elif (i_socken := I_SOCKEN.search(nu)) and (traff := register.socken(omrade, i_socken.group(1))):
                kopplingar[(r["id"], "forvaring", traff["entitet_id"])] = (r["id"], traff["entitet_id"], "forvaring", nu, False, False)
            elif hemmaplats and RELATIVT_LAGE.search(nu):
                kopplingar[(r["id"], "forvaring", hemmaplats)] = (r["id"], hemmaplats, "forvaring", nu, False, True)
    return list(kopplingar.values())


def forvaringsplatser() -> list[dict]:
    with FORVARINGSFIL.open(encoding="utf-8", newline="") as f:
        return [{**rad, "monster": re.compile(rad["monster"], re.I)} for rad in csv.DictReader(f, delimiter="\t")]


def forvaring(register: Platsregister, text: str) -> str | None:
    """Museet i förvaringsuppgiften. Vid "SHM, on deposit at Lödöse Museum" är det Lödöse som har stenen."""
    if " deposit " in text:
        text = text.split(" deposit ", 1)[1]
    for rad in register.museer:
        if rad["monster"].search(text):
            pid = f"plats:museum:{rad['id']}"
            if pid not in register.uppgifter:
                register.ny_institution(pid, rad["namn"], rad["wikidata"] or None)
                stad = register.efter_namn(rad["stad"], "plats:", "Museets ort") if rad["stad"] else None
                register.uppgifter[pid] = {"slag": "museum", "nutida_namn": rad["namn"], "ingar_i_id": stad,
                                           "land_id": register.land.get(rad["land"].lower()),
                                           "kalla": "Wikidata" if rad["wikidata"] else None, "metod": "regel"}
            return pid
    return None


def nutida_uppgift(register: Platsregister, rad: dict, kalla: str = "Wikidata") -> dict:
    """Uppgifterna om en plats som granskningen har bestämt, med Wikidatas koordinater och kommun."""
    fakta = register.fakta.get(rad.get("wikidata") or "", {})
    socken = register.socken_per_q.get(rad.get("wikidata")) or angiven_socken(register, rad)
    kommun = register.kommun_per_q.get(fakta.get("over"))
    anm = rad.get("anm") or None
    lat, lon = fakta.get("lat"), fakta.get("lon")
    # Utan eget läge blir socknen ett närmevärde; landskap och land ger aldrig något läge
    if lat is None and socken and socken.get("latitud") is not None:
        lat, lon = socken["latitud"], socken["longitud"]
        anm = " ".join(filter(None, [anm, "Läget är socknens, som närmevärde."]))
    return {
        "slag": rad.get("slag") or None, "nutida_namn": rad.get("nutida_namn") or None,
        "land_id": register.land.get((rad.get("land") or "").lower()),
        "landskap_id": socken["landskap_id"] if socken else register.landskap_per_namn.get(rad.get("landskap")),
        "lan_id": socken["lan_id"] if socken else (kommun["lan_id"] if kommun else None),
        "kommun_id": socken["kommun_id"] if socken else (kommun["entitet_id"] if kommun else None),
        "socken_id": socken["entitet_id"] if socken else None,
        "latitud": lat, "longitud": lon,
        "kalla": kalla if fakta else ("Riksantikvarieämbetet" if socken else None), "metod": "sprakmodell", "anm": anm,
    }


def angiven_socken(register: Platsregister, rad: dict) -> dict | None:
    """Socknen som granskningen har angett: i landskapet om det är känt, annars den enda med namnet i landet."""
    namn = re.sub(r"\s+socken$", "", rad.get("socken") or "").strip()
    if not namn or (rad.get("land") or "SE") != "SE":
        return None
    if rad.get("landskap"):
        return register.socken(rad["landskap"], namn)
    for form in (namn, namn[:-1] if namn.endswith("s") else ""):
        traffar = [s for (_, n), s in register.socknar.items() if n == ordform(form)] if form else []
        if len(traffar) == 1:
            return traffar[0]
    return None


def las_delade(register: Platsregister) -> None:
    """Orter som är fördelade brev för brev: varje plats blir en egen entitet."""
    for namn, post in json.loads(DELADE_FIL.read_text(encoding="utf-8")).items():
        for pid, plats in post["platser"].items():
            register._ny(pid, plats["namn"], f"Ort i SDHK:s ortfält, skild från andra platser som heter {namn}")
            register.uppgifter[pid] = nutida_uppgift(register, plats)
            if plats.get("wikidata"):
                register.wikidata[pid] = plats["wikidata"]
            for verk_id in plats["brev"]:
                register.delade[(verk_id, ordform(namn))] = pid
        for omrade, pid in post.get("runor", {}).items():
            register.runstader[(omrade, ordform(namn))] = pid
        # Orten kan sakna entitet före den första körningen
        allman = register.efter_namn(namn, "plats:sdhk:", "Ort i SDHK:s ortfält")
        register.ambeten[allman] = post.get("ambeten", {})


def tillampa_orter(register: Platsregister) -> None:
    """Granskningens beslut om brevorterna."""
    delade = json.loads(DELADE_FIL.read_text(encoding="utf-8"))
    with ORTFIL.open(encoding="utf-8", newline="") as f:
        rader = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    # Orter där granskningen av breven har visat att namnet pekade ut fel plats
    with KORRIGERINGSFIL.open(encoding="utf-8", newline="") as f:
        korrigerade = {r["ort"] for r in csv.DictReader(f, delimiter="\t")}
    for rad in rader:
        pid = register.per_form.get(ordform(rad["namn"]))
        if not pid:
            continue
        if rad["namn"] in korrigerade:
            register.utan_wikidata.add(pid)
            continue
        if rad["beslut"] == "ej_plats":
            register.uppgifter[pid] = {"slag": "ej_plats", "metod": "sprakmodell", "anm": rad["anm"] or "Fältet anger inte en plats"}
            continue
        if rad["beslut"] == "entydig":
            uppgift = nutida_uppgift(register, rad)
            if rad["ingar_i"]:
                uppgift["ingar_i_id"] = register.efter_namn(rad["ingar_i"], "plats:", "Större plats som en brevort ingår i")
            register.uppgifter[pid] = uppgift
            if rad["wikidata"]:
                register.wikidata[pid] = rad["wikidata"]
            continue
        grupp = f"plats:{_slug(rad['namn'])}"
        mojliga = [s["entitet_id"] for (_, namn), s in register.socknar.items() if namn == ordform(rad["namn"])]
        egna = delade.get(rad["namn"], {}).get("platser", {})
        mojliga.extend(egna)
        for q in dict.fromkeys(re.findall(r"\bQ\d+\b", rad["alternativ"])):
            if q not in register.fakta or any(plats.get("wikidata") == q for plats in egna.values()):
                continue
            if q in register.socken_per_q:
                mojliga.append(register.socken_per_q[q]["entitet_id"])
                continue
            mojlig = f"plats:wd:{q}"
            etikett = register.fakta[q].get("namn") or rad["namn"]
            register._ny(mojlig, etikett, f"Möjlig plats för namnet {rad['namn']} i SDHK")
            register.wikidata[mojlig] = q
            register.uppgifter[mojlig] = nutida_uppgift(register, {"wikidata": q, "nutida_namn": etikett, "land": rad["land"]})
            mojliga.append(mojlig)
        for mojlig in dict.fromkeys(mojliga):
            if mojlig != pid:
                iid = f"identifiering:plats:{_slug(rad['namn'])}:{mojlig.split(':', 1)[1].replace(':', '_')}"
                register.identifieringar[iid] = (iid, pid, mojlig, grupp, "Samma namn; brevet avgör vilken plats som avses")


def rensa_platser(register: Platsregister) -> None:
    """Entiteter vars namn inte är ett rent platsnamn, och platser som ingår i en större."""
    p = db._prefix()
    # Orter vi vet något om: granskade i den här körningen, samt land och landskap
    slag = {pid: u.get("slag") for pid, u in register.uppgifter.items()}
    for r in _rader(f"SELECT entitet_id, slag FROM {p}plats_uppgift WHERE slag IN ('land', 'landskap')"):
        slag.setdefault(r["entitet_id"], r["slag"])
    kanda = {nyckel: pid for nyckel, pid in register.per_form.items() if pid in slag}
    namn_per_id = {}
    rader = _rader(f"SELECT id, namn FROM {p}entitet WHERE id LIKE {db._ph()} AND typ IN ('plats', 'indelning')", ("plats:sdhk:%",))
    for r in rader:
        namn_per_id[r["id"]] = r["namn"]
    # Rena ortnamn, som kan stå först i en längre text
    rena = {ordform(n): pid for pid, n in namn_per_id.items() if not MISSTANKT.search(n) and not X_OCH_Y.match(n)}
    rena.update(kanda)

    def ersatt(pid: str, ny: str) -> None:
        register.ersatta[pid] = ny
        iid = f"identifiering:plats:ersatt:{pid.split(':', 1)[1].replace(':', '_')}"
        register.identifieringar[iid] = (iid, pid, ny, None, "ersatt_av")

    exakta = {r["namn"].casefold() for r in _rader(f"SELECT namn FROM {p}entitet WHERE typ IN ('plats', 'indelning')")}

    def inledande_ort(text: str, pid: str) -> str | None:
        """Orten först i "Roskilde med kapitlet": exakt namn följt av något som inte beskriver en plats."""
        ord_ = text.split()
        if not ord_[0][0].isupper() or ord_[0].casefold() in INLEDANDE_ORD:
            return None
        for antal in range(min(3, len(ord_) - 1), 0, -1):
            forsta = " ".join(ord_[:antal])
            nasta = ord_[antal]
            # "Holma i Brastads socken" och "Konga härad i Värend" är egna platser
            if forsta.casefold() not in exakta or not nasta[0].islower() or nasta in ("i", "på", "vid") \
                    or INDELNING.search(" ".join(ord_[antal:])) or BYGGNAD.search(nasta):
                continue
            if (traff := rena.get(ordform(forsta))) and traff != pid:
                return traff
        return None

    for pid, namn in namn_per_id.items():
        if pid in register.uppgifter:
            continue
        misstankt = bool(MISSTANKT.search(namn))
        if misstankt and EJ_PLATS.search(namn):
            register.uppgifter[pid] = {"slag": "ej_plats", "metod": "regel", "anm": "Texten anger inte en plats"}
            register.bort.append(pid)
            continue
        delar = X_OCH_Y.match(namn)
        if not delar:
            if misstankt and (ort := inledande_ort(namn, pid)):
                ersatt(pid, ort)
            continue
        x, relation, y = delar.groups()
        # "Slesvig subkollektor i Sverige": X är en ort följd av en titel
        ord_ = x.split()
        if (misstankt or (len(ord_) > 1 and ord_[1][0].islower() and not BYGGNAD.search(x))) \
                and not INDELNING.search(namn) and (ort := inledande_ort(x, pid)):
            ersatt(pid, ort)
            continue
        over = kanda.get(ordform(y))
        if over == pid:
            continue
        egennamn = x[0].isupper()
        if egennamn:
            register.namnformer.add((pid, x.strip(" ”\"'")))
        # "Bro på Gotland": socknen i landskapet, när X heter som en socken där
        if egennamn and slag.get(over) == "landskap" and (socken := register.socken(y, x)):
            register.uppgifter[pid] = {
                "nutida_namn": x, "socken_id": socken["entitet_id"], "kommun_id": socken["kommun_id"], "lan_id": socken["lan_id"],
                "landskap_id": socken["landskap_id"], "land_id": socken["land_id"], "latitud": socken["latitud"],
                "longitud": socken["longitud"], "metod": "regel", "anm": f"Socknen med namnet, i källan {relation} {y}",
            }
        elif over and relation != "vid" and slag.get(over) not in REGION:
            register.uppgifter[pid] = {"ingar_i_id": over, "metod": "regel", "nutida_namn": x if egennamn else None}
        elif egennamn:
            register.uppgifter[pid] = {"nutida_namn": x, "metod": "regel", "anm": f"I källan {relation} {y}; läget är inte bestämt"}


SOCKEN_I_TEXT = re.compile(r"\b([A-ZÅÄÖ][\w-]+(?:[ -][A-ZÅÄÖ][\w-]+)?) (?:socken|sn)\b")
SOCKENS_DEL = re.compile(r"^(.+?)(?:s? socken|s? sn|s? sockens? .+|s? sn:s .+| kyrka| kyrkby| sockenkyrka| prästgård)$")
FORE_SOCKEN = re.compile(r"(?:\bi|,|\(|\(i)\s*$")


def socken_ur_brev(register: Platsregister, kopplingar: list[tuple]) -> list[tuple]:
    """Socknen som brevet själv anger. Ett namn kan avse flera platser, så det avgörs brev för brev.

    "Romfartuna kyrka" och ett namn med ett enda brev knyts till socknen direkt. Annars får
    brevet en egen plats, "Viby (Hassle socken)", och breven utan socken står kvar på namnet.
    """
    p = db._prefix()
    per_namn: dict[str, list[dict]] = {}
    for (_, namn), socken in register.socknar.items():
        per_namn.setdefault(namn, []).append(socken)

    def bestam(namn: str, text: str) -> dict | None:
        """Socknen med namnet (eller utan genitiv-s): den enda i landet, eller den enda i ett landskap som texten nämner."""
        for form in (namn, namn[:-1] if namn.endswith("s") else ""):
            kandidater = per_namn.get(ordform(form), []) if form else []
            if len(kandidater) == 1:
                return kandidater[0]
            i_texten = [k for k in kandidater if k["landskap"] and k["landskap"] in text]
            if len(i_texten) == 1:
                return i_texten[0]
        return None

    def i_brevet(namn: str, text: str) -> dict | None:
        """Socknen, om den står strax efter ortnamnet: "Dicka (i Folkärna sn)", "gården Rogsta i Hälsingtuna socken"."""
        forsta = ordform(namn.split()[0])
        hittade = {}
        for m in SOCKEN_I_TEXT.finditer(text):
            fore = text[max(0, m.start() - 30):m.start()]
            if FORE_SOCKEN.search(fore) and forsta in {ordform(o) for o in re.findall(r"[\w-]+", fore)} and (traff := bestam(m.group(1), text)):
                hittade[traff["entitet_id"]] = traff
        return next(iter(hittade.values())) if len(hittade) == 1 else None

    texter = {f"sdhk:{r['sdhk_nr']}": f"{r['ort'] or ''} | {r['regest'] or ''}"
              for r in _rader(f"SELECT sdhk_nr, ort, regest FROM {p}sdhk_brev")}
    namn_per_id = {r["id"]: r["namn"] for r in _rader(f"SELECT id, namn FROM {p}entitet WHERE id LIKE {db._ph()}", ("plats:sdhk:%",))}
    namn_per_id.update({pid: rad[2] for pid, rad in register.nya.items()})
    antal = Counter(k[1] for k in kopplingar)

    def uppgift(namn: str, socken: dict) -> dict:
        return {
            "nutida_namn": namn, "socken_id": socken["entitet_id"], "kommun_id": socken["kommun_id"], "lan_id": socken["lan_id"],
            "landskap_id": socken["landskap_id"], "land_id": socken["land_id"], "latitud": socken["latitud"],
            "longitud": socken["longitud"], "kalla": "SDHK; Riksantikvarieämbetet", "metod": "regel",
            "anm": "Socknen står i brevet. Läget är socknens, som närmevärde.",
        }

    resultat = []
    for koppling in kopplingar:
        verk_id, pid, *resten = koppling
        namn = namn_per_id.get(pid)
        if not namn or pid in register.uppgifter or pid in register.ersatta or not namn[0].isupper():
            resultat.append(koppling)
            continue
        text = texter.get(verk_id, "")
        if (del_ := SOCKENS_DEL.match(namn)) and (socken := bestam(del_.group(1), text)):
            register.uppgifter[pid] = uppgift(namn, socken)
        elif (socken := i_brevet(namn, text)):
            if antal[pid] == 1:
                register.uppgifter[pid] = uppgift(namn, socken)
            else:
                ny = f"{pid}:{socken['entitet_id'].rsplit(':', 1)[1]}"
                register._ny(ny, f"{namn} ({socken['nutida_namn']} socken)", f"{namn} i SDHK:s ortfält, där brevet anger socknen")
                register.uppgifter[ny] = uppgift(namn, socken)
                register.flyttade.append((verk_id, pid, ny))
                koppling = (verk_id, ny, *resten)
        resultat.append(koppling)
    return resultat


def lexikon_beslut(register: Platsregister, kopplingar: list[tuple]) -> list[tuple]:
    """Besluten från platslexikon.py: brev där häradet i brevet pekar ut en plats i de historiska registren."""
    beslut: dict[str, dict] = {}
    # Granskningen går före regeln, eftersom den har läst hela brevet
    for fil in (LEXIKONFIL, GRANSKNINGSFIL):
        if fil.exists():
            with fil.open(encoding="utf-8", newline="") as f:
                beslut.update({r["verk_id"]: r for r in csv.DictReader(f, delimiter="\t") if r["lat"]})
    if not beslut:
        return kopplingar
    antal = Counter(k[1] for k in kopplingar)
    namn_per_id = {r["id"]: r["namn"] for r in _rader(f"SELECT id, namn FROM {db._prefix()}entitet WHERE id LIKE {db._ph()}", ("plats:sdhk:%",))}
    namn_per_id.update({pid: rad[2] for pid, rad in register.nya.items()})
    kallor = {"tora": "Riksarkivet: TORA",
              "kartor": "Riksarkivet: Äldre geometriska kartor 1630-1655 (CC BY 4.0)",
              "rosenberg": "Riksarkivet: Rosenbergs geografiska lexikon (Public Domain Mark)"}
    # Är alla brev från en ort placerade på samma ställe behöver orten inte delas
    platser_per_ort: dict[str, set] = {}
    placerade: Counter = Counter()
    for verk_id, pid, *_ in kopplingar:
        if (rad := beslut.get(verk_id)) and rad["ort"] == namn_per_id.get(pid):
            platser_per_ort.setdefault(pid, set()).add(rad["socken"])
            placerade[pid] += 1
    resultat = []
    for koppling in kopplingar:
        verk_id, pid, *resten = koppling
        rad = beslut.get(verk_id)
        # En plats med känt läge rörs inte; har den bara ett namn kan brevet bestämma platsen
        rattas = bool(rad) and rad["niva"] == "korrigering"
        if not rad or rad["ort"] != namn_per_id.get(pid) or (register.uppgifter.get(pid, {}).get("latitud") is not None and not rattas):
            resultat.append(koppling)
            continue
        socken = next((s for l in rad["landskap"].split(",") if (s := register.socken(l, rad["socken"]))), None)
        # Står orten redan på samma socken behövs ingen egen plats för brevet
        if socken and register.uppgifter.get(pid, {}).get("socken_id") == socken["entitet_id"]:
            resultat.append(koppling)
            continue
        granskad_av_tva = rad["niva"] in ("granskning", "korrigering")
        anm = "Två oberoende bedömare är överens utifrån breven." if granskad_av_tva else f"Häradet i brevet stämmer med {rad['harad']}."
        if rad["lage"] == "socken":
            anm += " Läget är socknens, som närmevärde."
        uppgift = {
            "nutida_namn": rad["kandidat"], "socken_id": socken["entitet_id"] if socken else None,
            "kommun_id": socken["kommun_id"] if socken else None, "lan_id": socken["lan_id"] if socken else None,
            "landskap_id": socken["landskap_id"] if socken else None, "land_id": register.land.get("se"),
            "latitud": float(rad["lat"]), "longitud": float(rad["lon"]), "kalla": kallor[rad["kalla"]], "metod": "sprakmodell" if granskad_av_tva else "regel", "anm": anm,
        }
        if not rattas and (antal[pid] == 1 or platser_per_ort[pid] == {rad["socken"]} and placerade[pid] == antal[pid]):
            register.uppgifter[pid] = uppgift
        else:
            # Samma namn kan avse flera platser, så breven hålls isär
            # Samma socken ger samma entitet, oavsett vilken regel som hittade den
            namn = namn_per_id[pid]
            if socken:
                ny = f"{pid}:{socken['entitet_id'].rsplit(':', 1)[1]}"
                visning = f"{namn} ({socken['nutida_namn']} socken)"
            else:
                ny = f"{pid}:{_slug(rad['socken'] or rad['harad'])}"
                visning = f"{namn} ({rad['socken'] or rad['harad']})"
            register._ny(ny, visning, f"{namn} i SDHK:s ortfält, bestämd genom brevet")
            register.uppgifter[ny] = uppgift
            register.flyttade.append((verk_id, pid, ny))
            koppling = (verk_id, ny, *resten)
        resultat.append(koppling)
    return resultat


def sammanslagningar(register: Platsregister, kopplingar: list[tuple]) -> list[tuple]:
    """Samma plats under två namn: "Erikstad i Bankekinds härad" och "Erikstad (Bankekind)". Det gamla id:t hänvisar vidare."""
    namn_till_id = {r["namn"]: r["id"] for r in _rader(f"SELECT id, namn FROM {db._prefix()}entitet WHERE id LIKE {db._ph()}", ("plats:sdhk:%",))}
    namn_till_id.update({rad[2]: pid for pid, rad in register.nya.items()})
    flytt: dict[str, str] = {}
    with SAMMANSLAGNINGSFIL.open(encoding="utf-8", newline="") as f:
        for rad in csv.DictReader(f, delimiter="\t"):
            gammal, ny = namn_till_id.get(rad["gammal"]), namn_till_id.get(rad["ny"])
            if not gammal or not ny or gammal == ny:
                log.warning("Kan inte slå ihop %s med %s", rad["gammal"], rad["ny"])
                continue
            flytt[gammal] = ny
            register.ersatta[gammal] = ny
            register.uppgifter.pop(gammal, None)
            iid = f"identifiering:plats:ersatt:{gammal.split(':', 1)[1].replace(':', '_')}"
            register.identifieringar[iid] = (iid, gammal, ny, None, "ersatt_av")
    resultat = []
    for verk_id, pid, *resten in kopplingar:
        resultat.append((verk_id, flytt.get(pid, pid), *resten))
    return resultat


def samma_socken(register: Platsregister, kopplingar: list[tuple]) -> list[tuple]:
    """En ort och en egen plats för ett brev i samma socken är samma plats: brevet flyttas till orten.

    Så kan det bli när en regel först ger ett brev en egen plats och en annan sedan bestämmer
    hela orten. Det gamla id:t finns kvar och hänvisar vidare. Tomma platser som heter likadant
    som en annan plats under samma ort hänvisar också vidare.
    """
    flytt: dict[str, str] = {}

    def hanvisa(gammal: str, ny: str) -> None:
        flytt[gammal] = ny
        register.ersatta[gammal] = ny
        register.uppgifter.pop(gammal, None)
        iid = f"identifiering:plats:ersatt:{gammal.split(':', 1)[1].replace(':', '_')}"
        register.identifieringar[iid] = (iid, gammal, ny, None, "ersatt_av")

    for pid in {k[1] for k in kopplingar}:
        if not DEL_AV_ORT.match(pid):
            continue
        ort = pid.rsplit(":", 1)[0]
        socken = register.uppgifter.get(pid, {}).get("socken_id")
        if socken and register.uppgifter.get(ort, {}).get("socken_id") == socken:
            hanvisa(pid, ort)

    anvanda = {k[1] for k in kopplingar}
    delar: dict[tuple[str, str], list[str]] = {}
    for r in _rader(f"SELECT id, namn FROM {db._prefix()}entitet WHERE id LIKE {db._ph()}", ("plats:sdhk:%:%",)):
        delar.setdefault((r["id"].rsplit(":", 1)[0], r["namn"]), []).append(r["id"])
    for pid, rad in register.nya.items():
        if DEL_AV_ORT.match(pid) and pid not in delar.get((pid.rsplit(":", 1)[0], rad[2]), []):
            delar.setdefault((pid.rsplit(":", 1)[0], rad[2]), []).append(pid)
    for (ort, _), ider in delar.items():
        kvar = [i for i in ider if i in anvanda and i not in flytt]
        mal = kvar[0] if kvar else next((flytt[i] for i in ider if i in flytt), None)
        for pid in ider:
            if mal and pid != mal and pid not in anvanda and pid not in register.uppgifter:
                hanvisa(pid, mal)
    return [(verk_id, flytt.get(pid, pid), *resten) for verk_id, pid, *resten in kopplingar]


def las_uppslag(register: Platsregister) -> None:
    """X:s eget läge ur Wikidata, där det är känt. Går före ortens närmevärde."""
    raa = json.loads(RAA_FIL.read_text(encoding="utf-8"))
    land_per_q = {x["wikidata"]: register.land.get(x["kod"]) for x in raa["land"]}
    pid_per_namn = {r["namn"]: r["id"] for r in _rader(
        f"SELECT id, namn FROM {db._prefix()}entitet WHERE id LIKE {db._ph()}", ("plats:sdhk:%",))}
    with UPPSLAGSFIL.open(encoding="utf-8", newline="") as f:
        for rad in csv.DictReader(f, delimiter="\t"):
            pid = pid_per_namn.get(rad["namn"])
            uppgift = register.uppgifter.get(pid)
            fakta = register.fakta.get(rad["wikidata"])
            if not uppgift or not fakta or uppgift.get("socken_id"):
                continue
            kommun = register.kommun_per_q.get(fakta.get("over"))
            uppgift.update(latitud=fakta.get("lat"), longitud=fakta.get("lon"), kalla="Wikidata",
                           land_id=land_per_q.get(fakta.get("land")),
                           kommun_id=kommun["entitet_id"] if kommun else None, lan_id=kommun["lan_id"] if kommun else None,
                           anm=f"Enda platsen med namnet {rad['x']} nära {rad['y']} i Wikidata")
            register.wikidata[pid] = rad["wikidata"]


def arv_fran_storre(register: Platsregister) -> None:
    """En plats inne i en ort får ortens läge som närmevärde. Land och landskap ger inget läge."""
    for uppgift in register.uppgifter.values():
        over = register.uppgifter.get(uppgift.get("ingar_i_id"))
        if not over or over.get("slag") in REGION:
            continue
        for falt in ("land_id", "lan_id", "kommun_id", "socken_id"):
            if uppgift.get(falt) is None:
                uppgift[falt] = over.get(falt)
        if uppgift.get("latitud") is None and over.get("latitud") is not None:
            uppgift["latitud"], uppgift["longitud"] = over["latitud"], over["longitud"]
            uppgift["anm"] = " ".join(filter(None, [uppgift.get("anm"), "Läget är ortens, som närmevärde."]))


def landskap_ur_lage(register: Platsregister) -> None:
    """Landskapet för svenska platser med läge: den närmaste socknens. Gör att landskap går att söka på."""
    sverige = register.land.get("se")
    socknar = [(s["latitud"], s["longitud"], s["landskap_id"]) for s in register.socknar.values()
               if s.get("latitud") is not None and s.get("landskap_id")]
    for uppgift in register.uppgifter.values():
        lat, lon = uppgift.get("latitud"), uppgift.get("longitud")
        if uppgift.get("land_id") != sverige or uppgift.get("landskap_id") or lat is None:
            continue
        skala = math.cos(math.radians(lat)) ** 2
        uppgift["landskap_id"] = min(socknar, key=lambda s: (s[0] - lat) ** 2 + skala * (s[1] - lon) ** 2)[2]


def koppla_saten(register: Platsregister) -> list[tuple]:
    p = db._prefix()
    rader = _rader(f"SELECT DISTINCT langd_id, sate FROM {p}auktoritet_titel WHERE sate IS NOT NULL")
    return [(register.efter_namn(r["sate"], "plats:", f"Säte i auktoritetslängden {r['langd_id']}"), r["sate"]) for r in rader]


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--rapport", help="skriv de former som blev nya platser till en fil")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db.initiera_schema()
    register = Platsregister()
    las_delade(register)
    ovanliga: Counter = Counter()
    brev = koppla_brev(register, ovanliga)
    runor = koppla_runor(register)
    saten = koppla_saten(register)
    tillampa_orter(register)
    rensa_platser(register)
    brev = socken_ur_brev(register, brev)
    brev = lexikon_beslut(register, brev)
    brev = sammanslagningar(register, brev)
    brev = samma_socken(register, brev)
    las_uppslag(register)
    arv_fran_storre(register)
    landskap_ur_lage(register)

    p, ph = db._prefix(), db._ph()
    conn = db._hamta_db()
    try:
        db.upsert(conn, "entitet", ["id", "typ", "namn", "beskrivning", "extra"], ["id"], list(register.nya.values()))
        db.upsert(conn, "entitet_namnform", ["entitet_id", "namnform"], ["entitet_id", "namnform"], sorted(register.namnformer))
        # Uppgifterna ur auktoriteterna ligger kvar; resten byggs om från grunden
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {p}plats_uppgift WHERE metod <> {ph}", ("auktoritet",))
        conn.commit()
        kolumner = ["slag", "nutida_namn", "land_id", "landskap_id", "lan_id", "kommun_id", "socken_id", "ingar_i_id",
                    "latitud", "longitud", "kalla", "metod", "anm"]
        db.upsert(conn, "plats_uppgift", ["entitet_id", *kolumner], ["entitet_id"],
                  [(pid, *(u.get(k) for k in kolumner)) for pid, u in register.uppgifter.items()])
        cur = conn.cursor()
        for pid in register.utan_wikidata:
            cur.execute(f"UPDATE {p}entitet SET wikidata_id = NULL WHERE id = {ph}", (pid,))
        for pid, q in register.wikidata.items():
            cur.execute(f"UPDATE {p}entitet SET wikidata_id = {ph} WHERE id = {ph} AND wikidata_id IS NULL", (q, pid))
        cur.execute(f"DELETE FROM {p}verk_plats")
        cur.execute(f"DELETE FROM {p}identifiering WHERE id LIKE 'identifiering:plats:%'")
        conn.commit()
        db.upsert(conn, "verk_plats", ["verk_id", "plats_id", "roll", "namnform", "osaker", "harledd"],
                  ["verk_id", "roll", "plats_id"], brev + runor)
        db.upsert(conn, "identifiering", ["id", "entitet_id", "identifierad_med", "alternativgrupp", "kommentar"], ["id"],
                  list(register.identifieringar.values()))
        db.upsert(conn, "bedomning", ["id", "identifiering_id", "aspekt", "varde", "motivering", "bedomare"], ["id"],
                  [(f"{iid}:bedomning", iid, "identifiering", "saker", "Namnet var inte ett rent platsnamn.", BEDOMARE)
                   if rad[4] == "ersatt_av" else
                   (f"{iid}:bedomning", iid, "identifiering", "mojlig", "Namnet delas av flera platser.", BEDOMARE)
                   for iid, rad in register.identifieringar.items()])
        cur = conn.cursor()
        # Påståendena följer breven och ämbetena till den plats som avses
        for allman, ambeten in register.ambeten.items():
            for ambete, plats in ambeten.items():
                cur.execute(f"UPDATE {p}pastaende SET plats_id = {ph} WHERE plats_id = {ph} AND objekt_id = {ph}", (plats, allman, ambete))
        for verk_id, allman, plats in register.flyttade:
            cur.execute(f"""UPDATE {p}pastaende SET plats_id = {ph} WHERE plats_id = {ph} AND passage_id IN
                            (SELECT id FROM {p}passage WHERE verk_id = {ph})""", (plats, allman, verk_id))
        for gammal, ny in register.ersatta.items():
            cur.execute(f"UPDATE {p}pastaende SET plats_id = {ph} WHERE plats_id = {ph}", (ny, gammal))
        for pid in register.bort:
            cur.execute(f"UPDATE {p}pastaende SET plats_id = NULL WHERE plats_id = {ph}", (pid,))
        for pid, sate in saten:
            cur.execute(f"UPDATE {p}auktoritet_titel SET sate_id = {ph} WHERE sate = {ph}", (pid, sate))
        conn.commit()
    finally:
        conn.close()

    log.info("Nya platser: %d. Kopplingar: %d brev, %d runinskrifter. Säten: %d. Ersatta namn: %d, ej platser: %d.",
             len(register.nya), len(brev), len(runor), len(saten), len(register.ersatta), len(register.bort))
    if argument.rapport:
        with open(argument.rapport, "w", encoding="utf-8") as f:
            for namn, n in ovanliga.most_common():
                f.write(f"{n}\t{namn}\n")


if __name__ == "__main__":
    main()

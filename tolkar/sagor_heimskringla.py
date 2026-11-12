"""
Tolk för islänningasagor, fornaldarsagor, norska och danska kungakrönikor
och Grágás ur heimskringla.no.

- Íslendinga sögur: alla sagor och þættir i Guðni Jónssons utgåva
  (Reykjavík 1946–49, normaliserad stavning), i den ordning de står i
  heimskringla.nos förteckning.
- Fornaldarsagor ur Guðni Jónsson & Bjarni Vilhjálmssons Fornaldarsögur
  Norðurlanda: Völsunga saga och Ragnars saga loðbrókar med Norna-Gests
  þáttr, och de sagor som utspelar sig i Sverige och Götaland (Hervarar,
  Yngvars, Gautreks, Hrólfs saga Gautrekssonar, Bósa, Örvar-Odds,
  Ásmundar saga kappabana, Sturlaugs, Hrólfs saga kraka, Sögubrot och
  Af Upplendinga konungum). Ragnarssona þáttr efter Hauksbók och Krákumál
  efter Finnur Jónssons Carmina Scaldica, med en passage per strof.
- Ágrip af Nóregskonungasögum, Fagrskinna (Finnur Jónsson 1902–03),
  Morkinskinna (C. R. Unger 1867) och Knýtlinga saga.
- Sven Aggesens danska krönika och Grágás, som heimskringla.no bara har i
  dansk översättning (Grágás: Vilhjálmur Finsen 1870).

Varje verk får sin originaltext med passager per kapitel och, där
heimskringla.no länkar en, en äldre svensk eller dansk översättning.
Översättningar tas bara med om titelsidan anger ett tryckår före 1931, så
att översättaren med god marginal är död sedan mer än 70 år. Verk som är
delade på flera sidor (Fagrskinna, Morkinskinna, Grágás) får kapitlen per
delsida, med delsidans titel i adressen.

Islänningasagor som saknas på heimskringla.no (bland andra Njáls, Laxdæla
och Vatnsdæla saga) hämtas ur Icelandic Saga Database (sagadb.org, public
domain), som har texten i modern isländsk stavning efter Netútgáfan och äldre
översättningar. Därifrån tas också en översättning till verk som på
heimskringla.no saknar en fri: svenska går före danska och engelska, med samma
gräns för tryckåret.

Verk utan fri översättning har svenska översättningar gjorda av språkmodell
i data/oversattningar/sagor/ (se RIKTLINJER.md i data/oversattningar/), som
laddas som egna utgåvor märkta som maskinöversättning.

Kapitlen tas fram som i Heimskringla (fetstilta nummer i wikitexten). Sidor
utan numrerade kapitel delas i stycken om högst cirka 4 000 tecken.

Användning:
    python -m tolkar.sagor_heimskringla
    python -m tolkar.sagor_heimskringla --torr
"""

import argparse
import html
import logging
import re
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda
from tolkar.heimskringla_no import _slug, hamta_wikitext as _hamta_wikitext, kapitel, rensa_wiki, sidlank

log = logging.getLogger("tolkar.sagor_heimskringla")

ISLENDINGA = "Íslendinga sögur"
OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "sagor"
SAGADB = "https://sagadb.org"
SAGADB_KATALOG = Path(__file__).parent.parent / "data" / "raw" / "sagadb"
USER_AGENT = "fornmed-forskningsdatabas/0.1 (öppen forskningsdatabas över medeltida källor)"
# sagadb:s språkkoder för översättningar i den ordning de föredras
SAGADB_SPRAK = [("se", "swe"), ("da", "dan"), ("en", "eng"), ("en2", "eng")]
# Titlar vars sagadb-namn inte följer av titeln
SAGADB_NAMN = {"Njáls saga": "brennu-njals_saga", "Þorskfirðinga saga": "gull-thoris_saga",
               "Hallfreðar saga": "hallfredar_saga_vandraedaskalds", "Egils saga Skalla-Grímssonar": "egils_saga",
               "Hænsa-Þóris saga": "haensna-thoris_saga", "Harðar saga ok Hólmverja": "hardar_saga_og_holmverja",
               "Grettis saga Ásmundarsonar": "grettis_saga", "Bandamanna saga in skemmri": "bandamanna_saga",
               "Vápnfirðinga saga": "vopnfirdinga_saga"}
# Sidor i förteckningen som är en annan version av en saga som redan tas med
DUBBLETTER = {"Grettis saga Ásmundarsonar", "Bandamanna saga in skemmri", "Bandamanna saga in meiri",
              "Gunnars saga Keldugnúpsfífls",
              # Förteckningssida över þættir, inte en text
              "Fjörutíu Íslendinga þættir"}
SENASTE_AR = 1930
STYCKE = 4000

# Kolumnerna i heimskringla.nos språktabell
SPRAKKOLUMNER = ["non", "isl", "nor", "dan", "swe", "fao"]

# Ungefärliga tillkomsttider (Íslenzk fornrit och Kulturhistoriskt lexikon);
# övriga islänningasagor och þættir dateras till 1200–1400
DATERING = {
    "Íslendingabók": ("1122/1133", 11220101, 11331231),
    "Landnámabók": ("1275/1280", 12750101, 12801231),
    "Kristni saga": ("1245/1260", 12450101, 12601231),
    "Egils saga Skalla-Grímssonar": ("1220/1240", 12200101, 12401231),
    "Eyrbyggja saga": ("1245/1265", 12450101, 12651231),
    "Laxdæla saga": ("1245/1260", 12450101, 12601231),
    "Njáls saga": ("1275/1290", 12750101, 12901231),
    "Grettis saga": ("1310/1330", 13100101, 13301231),
    "Grettis saga Ásmundarsonar": ("1310/1330", 13100101, 13301231),
    "Gísla saga Súrssonar": ("1250/1270", 12500101, 12701231),
    "Eiríks saga rauða": ("1260/1280", 12600101, 12801231),
    "Grænlendinga saga": ("1200/1230", 12000101, 12301231),
    "Gunnlaugs saga ormstungu": ("1270/1290", 12700101, 12901231),
    "Hrafnkels saga Freysgoða": ("1280/1310", 12800101, 13101231),
    "Fóstbræðra saga": ("1200/1300", 12000101, 13001231),
    "Vatnsdæla saga": ("1270/1290", 12700101, 12901231),
    "Víga-Glúms saga": ("1220/1250", 12200101, 12501231),
    "Kormáks saga": ("1200/1230", 12000101, 12301231),
    "Hallfreðar saga": ("1200/1230", 12000101, 12301231),
    "Heiðarvíga saga": ("1200/1230", 12000101, 12301231),
    "Bandamanna saga in skemmri": ("1250/1300", 12500101, 13001231),
    "Bandamanna saga in meiri": ("1250/1300", 12500101, 13001231),
}
STANDARD_DATERING = ("1200/1400", 12000101, 14001231)


@dataclass
class Konfig:
    sida: str                       # originalets (eller den enda textens) sida
    verk_id: str
    titel: str
    genre: str
    datering: tuple[str, int, int]
    beskrivning: str
    upphov: str | None = None
    utgava: str = ""                # originalutgåvans referens
    sprak: str = "non"              # originaltextens språk på sidan
    delsidor: str | None = None     # delsidornas titel slutar på detta, 'prefix:…' eller 'alla'
    uteslut: list[str] = field(default_factory=list)
    strofer: bool = False           # dikt med numrerade strofer i stället för kapitel
    oversattning: tuple[str, str] | None = None  # (språk, sida) när språktabellens första val är ofullständigt


FSN = "Guðni Jónsson & Bjarni Vilhjálmsson (utg.), Fornaldarsögur Norðurlanda, Reykjavík 1943–44"
# Språktabellen länkar för Völsunga saga Sanders utdrag och för Krákumál Sandvigs tolkning;
# Winkel Horns och Rafns översättningar är fullständiga
OVERSATTNING_VAL = {"Völsunga saga": ("dan", "Saga om Vølsungerne"),
                    "Krákumál": ("dan", "Krákumál (C. C. Rafn)")}

OVRIGA = [
    Konfig("Hervarar saga ok Heiðreks", "verk:saga:hervarar_saga", "Hervarar saga ok Heiðreks", "saga",
           ("1200/1300", 12000101, 13001231),
           "Fornaldarsaga om svärdet Tyrfing och Heidreks ätt; slutar med en lista över svenska kungar "
           "från Ivar vidfamne till Filip Hallstensson.",
           utgava=FSN),
    *[Konfig(sida, f"verk:saga:{_slug(titel)}", titel, genre, datering, beskrivning, utgava=utgava,
             oversattning=OVERSATTNING_VAL.get(sida), strofer=genre == "skaldedikt")
      for sida, titel, genre, datering, beskrivning, utgava in [
        ("Völsunga saga", "Völsunga saga", "saga", ("1250/1275", 12500101, 12751231),
         "Fornaldarsaga om Völsungarnas ätt, Sigurd Fafnesbane, Brynhild och Gudrun; bevarad i en enda "
         "handskrift från omkring 1400 (NKS 1824 b 4to) och där följd av Ragnars saga loðbrókar.", FSN),
        ("Ragnars saga loðbrókar ok sona hans", "Ragnars saga loðbrókar ok sona hans", "saga",
         ("1230/1270", 12300101, 12701231),
         "Fornaldarsaga om Ragnar lodbrok, hans hustrur Tora borgarhjort och Aslög (Kraka), Sigurd "
         "Fafnesbanes dotter, och hans söner; Ragnar dör i kung Ellas ormgrop i England.", FSN),
        ("Ragnarssona þáttr", "Ragnarssona þáttr", "saga", ("1280/1310", 12800101, 13101231),
         "Kort berättelse om Ragnar lodbrok och hans söners härnadståg, med ättartal fram till Harald "
         "hårfagre; bevarad i Hauksbók (1302–10).",
         "Eiríkur Jónsson & Finnur Jónsson (utg.), Hauksbók, København 1892–96"),
        ("Norna-Gests þáttr", "Norna-Gests þáttr", "saga", ("1280/1320", 12800101, 13201231),
         "Berättelse om den trehundraårige Norna-Gest, som vid Olav Tryggvasons hov berättar om "
         "Sigurd Fafnesbane och Ragnar lodbroks söner; bevarad i Flateyjarbók.", FSN),
        ("Krákumál", "Krákumál", "skaldedikt", ("1100/1200", 11000101, 12001231),
         "Ragnar lodbroks dödskväde, diktat i hans namn; 29 strofer om hans härnadståg, sagt i kung "
         "Ellas ormgrop.", "Finnur Jónsson (utg.), Carmina Scaldica, København 1913"),
        ("Yngvars saga víðförla", "Yngvars saga víðförla", "saga", ("1200/1300", 12000101, 13001231),
         "Fornaldarsaga om den svenske hövdingen Ingvar den vittfarnes färd österut, samma tåg som "
         "Ingvarsstenarna i Mälardalen minns, och om hans son Sven.", FSN),
        ("Sögubrot af nokkurum fornkonungum í Dana- ok Svíaveldi", "Sögubrot af fornkonungum", "saga",
         ("1250/1300", 12500101, 13001231),
         "Fragmentarisk saga om de danska och svenska sagokungarna från Ivar vidfamne till Harald "
         "hildetand och Sigurd ring, med slaget på Bråvalla.", FSN),
        ("Af Upplendinga konungum", "Af Upplendinga konungum", "saga", ("1250/1350", 12500101, 13501231),
         "Kort ättartal över kungarna i Upplanden i Norge, ättlingar till Olof trätälja av "
         "ynglingaätten.", FSN),
        ("Hrólfs saga kraka ok kappa hans", "Hrólfs saga kraka ok kappa hans", "saga",
         ("1300/1400", 13000101, 14001231),
         "Fornaldarsaga om den danske sagokungen Rolf krake och hans kämpar, med färden till kung "
         "Adils i Uppsala och guldsådden på Fyrisvallarna.", FSN),
        ("Gautreks saga", "Gautreks saga", "saga", ("1250/1350", 12500101, 13501231),
         "Fornaldarsaga om kungarna i Götaland: Gauti, hans son Gautrek och Starkad och Vikar.", FSN),
        ("Hrólfs saga Gautrekssonar", "Hrólfs saga Gautrekssonar", "saga", ("1250/1300", 12500101, 13001231),
         "Fornaldarsaga om Rolf, son till Gautrek i Götaland, och hans frieri till den svenska "
         "kungadottern Torbjörg.", FSN),
        ("Bósa saga ok Herrauðs", "Bósa saga ok Herrauðs", "saga", ("1300/1350", 13000101, 13501231),
         "Fornaldarsaga om Herröd, son till kung Ring i Östergötland, och hans fosterbror Bose.", FSN),
        ("Örvar-Odds saga", "Örvar-Odds saga", "saga", ("1250/1300", 12500101, 13001231),
         "Fornaldarsaga om Orvar-Odd, med Hjalmar den högmodige vid den svenske kungens hov i Uppsala "
         "och striden på Samsö mot Angantyr och hans bröder.", FSN),
        ("Ásmundar saga kappabana", "Ásmundar saga kappabana", "saga", ("1200/1300", 12000101, 13001231),
         "Fornaldarsaga om Asmund kämpabane och Budle, kung i Sverige, och om svärden som smiddes åt honom.",
         FSN),
        ("Sturlaugs saga starfsama", "Sturlaugs saga starfsama", "saga", ("1300/1400", 13000101, 14001231),
         "Fornaldarsaga om Sturlaug den idoge och kung Ingvar i Svitjod.", FSN),
    ]],
    Konfig("Ágrip", "verk:agrip", "Ágrip af Nóregskonungasögum", "kronika", ("1190", 11900101, 11901231),
           "Kortfattad norsk kungakrönika på fornnorska, den äldsta bevarade på folkspråket.",
           utgava="Gustav Indrebø (utg.), Ágrip. Norrøne bokverk 32, Oslo 1936"),
    Konfig("Fagrskinna", "verk:fagrskinna", "Fagrskinna", "kronika", ("1220/1230", 12200101, 12301231),
           "Norsk kungakrönika från Halvdan svarte till 1177, troligen skriven i Norge.",
           utgava="Finnur Jónsson (utg.), Fagrskinna. Nóregs kononga tal, København 1902–03",
           delsidor="(Fagrskinna)", uteslut=["Indledning (Fagrskinna)"]),
    Konfig("Morkinskinna", "verk:morkinskinna", "Morkinskinna", "kronika", ("1217/1222", 12170101, 12221231),
           "Isländsk kungasagasamling om de norska kungarna från Magnus den gode till 1157.",
           utgava="C. R. Unger (utg.), Morkinskinna, Christiania 1867",
           delsidor="(Morkinskinna)", uteslut=["Forord (Morkinskinna)"]),
    Konfig("Knytlinga saga", "verk:knytlinga_saga", "Knýtlinga saga", "saga", ("1250/1260", 12500101, 12601231),
           "Isländsk saga om de danska kungarna från Harald Blåtand till Knut VI.",
           utgava="Carl af Petersens & Emil Olson (utg.), Sögur Danakonunga, København 1919–25"),
    Konfig("Sven Aggesøn: Danernes historie", "verk:sven_aggesen", "Brevis historia regum Dacie",
           "kronika", ("1185/1190", 11850101, 11901231),
           "Sven Aggesens kortfattade danska kungakrönika. Den latinska texten finns inte på "
           "heimskringla.no; här i dansk översättning.",
           upphov="Sven Aggesen", sprak="dan", utgava="Jørgen Olrik (övers.), Sven Aggesøn, Danernes historie, i Krøniker fra Valdemarstiden, København 1900–01"),
    Konfig("Grágás (Dansk)", "verk:gragas", "Grágás", "lag", ("1117/1271", 11170101, 12711231),
           "Den isländska fristatens lagar efter Konungsbók; i Vilhjálmur Finsens danska "
           "översättning. Den fornisländska texten finns inte på heimskringla.no.",
           sprak="dan", utgava="Vilhjálmur Finsen (övers.), Grágás. Islændernes Lovbog i Fristatens Tid, "
                               "København 1870",
           delsidor="alla", uteslut=["Grágás (Dansk)", "Heimskringla Reprint", "Vilhjálmur Ludvig Finsen biografi",
                                     "Efterskrift (Grágás)"]),
]


def hamta_wikitext(sida: str) -> tuple[str, list[str]]:
    """Som heimskringla_no.hamta_wikitext, men följer omdirigeringar (#OMDIRIGERING [[Sida]])."""
    w, lankar = _hamta_wikitext(sida)
    m = re.match(r"\s*#(?:OMDIRIGERING|REDIRECT)\s*\[\[([^\]|]+)", w, re.IGNORECASE)
    return _hamta_wikitext(m.group(1).strip()) if m else (w, lankar)


def omdirigerad(sida: str) -> str:
    w, _ = _hamta_wikitext(sida)
    m = re.match(r"\s*#(?:OMDIRIGERING|REDIRECT)\s*\[\[([^\]|]+)", w, re.IGNORECASE)
    return m.group(1).strip() if m else sida


def stada(text: str) -> str:
    """HTML-entiteter (h&#339;) och rester av bildlänkar ('thumb|right|350px|') som rensa_wiki lämnar."""
    text = html.unescape(text)
    return re.sub(r"\b(?:thumb|right|left|center|\d+px)\|\s*", "", text)


def sprakrad(wikitext: str) -> dict[str, str]:
    """Sidnamn per språk ur språktabellens första rad (originalutgåvan)."""
    i = wikitext.find("Denne teksten finnes")
    if i < 0:
        return {}
    rad = wikitext[i:wikitext.find("|-", i)]
    ut = {}
    for sprak, cell in zip(SPRAKKOLUMNER, rad.split("!!")[1:]):
        m = re.search(r"link=([^\]]+)\]\]", cell)
        if m:
            ut[sprak] = m.group(1).strip()
    return ut


def titelsida(wikitext: str) -> str:
    """Texten mellan språktabellen och första kapitlet: titel, utgivare, tryckort och år."""
    i = wikitext.find("|}", wikitext.find("Velg språk")) + 2 if "Velg språk" in wikitext else 0
    return re.sub(r"\s+", " ", rensa_wiki(wikitext[i:i + 800]))


def tryckar(wikitext: str) -> int | None:
    """Översättningens tryckår; None för nya översättningar med copyrighttecken (© 2020)."""
    titel = titelsida(wikitext)
    if re.search(r"©|&#169;", titel):
        return None
    m = re.findall(r"\b(1[5-9]\d\d)\b", titel)
    return int(m[-1]) if m else None


def stycken(wikitext: str) -> list[tuple[int, str, str]]:
    """Text utan numrerade kapitel delad i stycken om högst STYCKE tecken."""
    if "Velg språk" in wikitext:
        wikitext = wikitext[wikitext.find("|}", wikitext.find("Velg språk")) + 2:]
    text = re.sub(r"\[\[Kategori:[^\]]*\]\]", "", wikitext)
    rader = rensa_wiki(text).split("\n")
    # Titelsidans korta rader (titel, översättare, tryckort) hör inte till texten
    start = next((i for i, r in enumerate(rader) if len(r) >= 120), 0)
    ut, buf = [], ""
    for stycke in rader[start:]:
        if buf and len(buf) + len(stycke) > STYCKE:
            ut.append(buf.strip())
            buf = ""
        buf += stycke + "\n"
    if buf.strip():
        ut.append(buf.strip())
    return [(i, "", t) for i, t in enumerate(ut, 1)]


ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _romersk(tal: str) -> int:
    v = [ROMERSKA[c] for c in tal]
    return sum(-a if a < b else a for a, b in zip(v, v[1:] + [0]))


def normalisera_kapitel(wikitext: str) -> str:
    """Skriver om kapitelrubriker som kapitel() inte känner igen till formen '''N. Rubrik'''.

    Fornaldarsögur har '''I. KAPÍTULI''', Grágás '''<span id="2">2.</span> Om Ligførsel'''.
    """
    wikitext = re.sub(r"</?span[^>]*>", "", wikitext)
    # Kapitelnumret kan stå direkt efter en bildlänk på samma rad (Kröningssvärd, Winkel Horn)
    wikitext = re.sub(r"\]\]\s*(?='''\s*\d+\.)", "]]\n", wikitext)
    # och följas av kapitlets första stycke på samma rad; det är text, ingen rubrik
    wikitext = re.sub(r"(?m)^('''\s*\d+\.\s*''')[ \t]*(?=[^\n]{150})", r"\1\n", wikitext)
    return re.sub(r"(?m)^'''\s*([IVXLC]+)\.\s*KAP[ÍI]TULI\s*'''",
                  lambda m: f"'''{_romersk(m.group(1))}.'''", wikitext)


def kapitel_fran_forsta(wikitext: str) -> list[tuple[int, str, str]]:
    """Som kapitel(), men numreringen får börja på vilket tal som helst (Landnámabóks andra del börjar på 2)."""
    if "Velg språk" in wikitext:
        wikitext = wikitext[wikitext.find("|}", wikitext.find("Velg språk")) + 2:]
    traffar = list(re.finditer(r"(?m)^(?:<center>)?'''\s*(\d+)\.(.*)$", wikitext))
    if not traffar:
        return []
    ut, forra = [], int(traffar[0].group(1)) - 1
    for i, m in enumerate(traffar):
        nr = int(m.group(1))
        if nr != forra + 1:
            continue
        slut = next((t.start() for t in traffar[i + 1:] if int(t.group(1)) == nr + 1), len(wikitext))
        ut.append((nr, rensa_wiki(m.group(2)).strip(" ."), rensa_wiki(wikitext[m.end():slut])))
        forra = nr
    return ut


def strofer(wikitext: str) -> list[tuple[int, str, str]]:
    """(nummer, '', text) per strof i en dikt där strofen inleds med sitt nummer ('1.' eller '1. Svunge vi')."""
    if "Velg språk" in wikitext:
        wikitext = wikitext[wikitext.find("|}", wikitext.find("Velg språk")) + 2:]
    # Faktarutan om dikten hör inte till texten
    wikitext = re.sub(r'<div class="toccolours">.*?</div>', "", wikitext, flags=re.S)
    text = rensa_wiki(re.sub(r"<br\s*/?>", "\n", wikitext))
    ut, forra = [], 0
    for m in re.finditer(r"(?ms)^\s*(\d+)\.\s*(.*?)(?=^\s*\d+\.\s|\Z)", text):
        nr = int(m.group(1))
        if nr == forra + 1:
            ut.append((nr, "", re.sub(r"(?m)^Kategori:.*$", "", m.group(2)).strip()))
            forra = nr
    return ut


def delar(wikitext: str) -> list[tuple[int, str, str]]:
    """Kapitel om sidan har numrerade kapitel, annars stycken. Kategorirader tas bort."""
    wikitext = normalisera_kapitel(wikitext)
    kap = kapitel(wikitext)
    if len(kap) < 2:
        kap = kapitel_fran_forsta(wikitext)
    if len(kap) >= 2:
        return [(nr, rub, re.sub(r"(?m)^Kategori:.*$", "", t).strip()) for nr, rub, t in kap]
    return stycken(wikitext)


def _sagadb_hamta(namn: str) -> str:
    fil = SAGADB_KATALOG / namn
    if not fil.exists():
        SAGADB_KATALOG.mkdir(parents=True, exist_ok=True)
        url = f"{SAGADB}/{namn}" if "." not in namn or namn.endswith(".html") else f"{SAGADB}/files/text/{namn}"
        log.info("Hämtar %s", url)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as svar:
            fil.write_bytes(svar.read())
        time.sleep(1)
    return fil.read_text(encoding="utf-8")


def sagadb_sprak() -> dict[str, set[str]]:
    """Sagorna i sagadb.org:s förteckning med de språk de finns på."""
    ut: dict[str, set[str]] = {}
    for namn, sprak in re.findall(r'href="([a-z_-]+)\.([a-z]{2}\d?)"', _sagadb_hamta("index_az.html")):
        ut.setdefault(namn, set()).add(sprak)
    return ut


def sagadb_namn(titel: str) -> str:
    """sagadb.org:s namn på en saga: titeln med isländska tecken omskrivna, 'ok' som 'og'."""
    if titel in SAGADB_NAMN:
        return SAGADB_NAMN[titel]
    t = titel.lower().replace(" ok ", " og ")
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ý", "y"), ("ð", "d"),
                 ("þ", "th"), ("æ", "ae"), ("ö", "o"), ("ǫ", "o")):
        t = t.replace(a, b)
    return re.sub(r"\s+", "_", re.sub(r"[^a-z0-9 -]", "", t)).strip("_")


def sagadb_text(namn: str, sprak: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Utgåvans beskrivning (andra raden) och kapitlen ("1. kafli", "Chapter 1 - …", "Kapitel 1")."""
    text = _sagadb_hamta(f"{namn}.{sprak}.txt")
    rader = text.split("\n")
    beskrivning = rader[2].strip() if len(rader) > 2 else ""
    rubrik = re.compile(r"(?m)^(?:(\d+)\. kafli|Chapter (\d+)(?:\s*-\s*(.*))?|Kapitel (\d+)(?:\s*[-.]\s*(.*))?)\s*$")
    traffar = list(rubrik.finditer(text))
    kap = []
    for i, m in enumerate(traffar):
        nr = int(m.group(1) or m.group(2) or m.group(4))
        slut = traffar[i + 1].start() if i + 1 < len(traffar) else len(text)
        innehall = re.sub(r"\n\s*\n+", "\n", text[m.end():slut]).strip()
        kap.append((nr, (m.group(3) or m.group(5) or "").strip(), innehall))
    return beskrivning, kap


def lagg_till_sagadb(paket: Kallpaket, k: Konfig, namn: str, sprak: str, typ: str, sprakkod: str,
                     ordning_bas: int) -> tuple[int, int | None]:
    """Lägger till en sagadb-text; returnerar antalet passager och tryckåret (för översättningar)."""
    beskrivning, kap = sagadb_text(namn, sprak)
    ar = int(m[-1]) if (m := re.findall(r"\b(1[5-9]\d\d)\b", beskrivning)) else None
    if typ == "oversattning" and (ar is None or ar > SENASTE_AR):
        return 0, ar
    slug = k.verk_id.split(":")[-1]
    utg = f"utgava:sagadb:{slug}:{sprak}"
    referens = (f"{k.utgava}, i modern isländsk stavning (Netútgáfan)" if typ == "originaltext" else beskrivning)
    paket.utgavor.append((k.verk_id, Utgava(utg, f"{referens}. Icelandic Saga Database (sagadb.org).",
                                            "Public domain enligt sagadb.org")))
    sett: set[int] = set()
    for nr, rubrik, text in kap:
        # Tomma kapitelrubriker och upprepade nummer i sagadb-texten hoppas över
        if not text or nr in sett:
            continue
        sett.add(nr)
        paket.passager.append((k.verk_id, Passage(
            id=f"{k.verk_id.split(':', 1)[1].replace(':', '_')}:{sprakkod}:{nr}", typ=typ, adress=f"kap. {nr}",
            sprak=sprakkod, text=(f"{nr}. {rubrik}\n" if rubrik else "") + text, ordning=ordning_bas + nr,
            utgava_id=utg, url=f"{SAGADB}/{namn}.{sprak}")))
    return len(sett), ar


def sagadb_oversattning(paket: Kallpaket, k: Konfig, namn: str, finns: set[str]) -> str | None:
    """Den första fria översättningen ur sagadb.org; returnerar en beskrivning för loggen."""
    for sprak, kod in SAGADB_SPRAK:
        if sprak in finns:
            n, ar = lagg_till_sagadb(paket, k, namn, sprak, "oversattning", kod, 100000)
            if n:
                return f"{n} {kod} ur sagadb ({ar})"
    return None


def islendinga_konfig() -> list[Konfig]:
    """En konfiguration per saga eller þáttr i heimskringla.nos förteckning över Íslendinga sögur."""
    w, _ = hamta_wikitext(ISLENDINGA)
    ut = []
    for m in re.finditer(r"(?m)^\*\s*\[\[([^\]|]+)", w):
        sida = m.group(1).strip()
        if "Formáli" in sida or "Nafnaskrá" in sida or sida in DUBBLETTER:
            continue
        titel = re.sub(r"\s*\((?:GJ|Indrebø|1866)\)$", "", sida)
        # Landnámabók är delad på fem delar och ett supplement
        delsidor = f"prefix:{sida} - " if sida == "Landnámabók" else None
        ut.append(Konfig(
            sida, f"verk:saga:{_slug(titel)}", titel, "saga", DATERING.get(titel, STANDARD_DATERING),
            "Islänningasaga eller þáttr i Íslendinga sögur." if "þáttr" in titel or "saga" in titel
            else "Text i Íslendinga sögur.",
            utgava="Guðni Jónsson (utg.), Íslendinga sögur I–XIII, Reykjavík 1946–49", delsidor=delsidor))
    return ut


def lagg_till_text(paket: Kallpaket, k: Konfig, sida: str, typ: str, sprak: str, utgava_id: str,
                   delprefix: str = "", deladress: str = "", ordning_bas: int = 0) -> int:
    if k.strofer:
        w, _ = hamta_wikitext(sida)
        slug = k.verk_id.split(':', 1)[1].replace(':', '_')
        for nr, _, text in strofer(w):
            paket.passager.append((k.verk_id, Passage(
                id=f"{slug}:{sprak}:{nr}", typ=typ, adress=f"str. {nr}", sprak=sprak, text=stada(text),
                ordning=ordning_bas + nr, utgava_id=utgava_id, url=sidlank(sida))))
        return len(strofer(w))
    w, _ = hamta_wikitext(sida)
    # Fagrskinnas sidor upprepar texten under "===Tekst med fotnoter===" med
    # utgivarens fotnoter; bara den första versionen tas med
    w = re.split(r"(?m)^=+\s*Tekst med fotnoter\s*=+", w)[0]
    n = 0
    for nr, rubrik, text in delar(w):
        if not text:
            continue
        adress = (f"{deladress}, " if deladress else "") + (f"kap. {nr}" if rubrik or len(text) < STYCKE + 500
                                                             else f"avsnitt {nr}")
        paket.passager.append((k.verk_id, Passage(
            id=f"{k.verk_id.split(':', 1)[1].replace(':', '_')}:{delprefix}{sprak}:{nr}", typ=typ, adress=adress,
            sprak=sprak, text=stada((f"{nr}. {rubrik}\n" if rubrik else "") + text), ordning=ordning_bas + nr,
            utgava_id=utgava_id, url=sidlank(sida))))
        n += 1
    return n


def lagg_till_verk(paket: Kallpaket, k: Konfig, sagadb: dict[str, set[str]]) -> None:
    namn = sagadb_namn(k.titel)
    try:
        w, lankar = hamta_wikitext(k.sida)
    except RuntimeError:
        if "is" not in sagadb.get(namn, set()):
            log.warning("%-44s finns varken på heimskringla.no eller i sagadb.org", k.titel)
            return
        paket.verk.append(Verk(
            id=k.verk_id, titel=k.titel, upphov=k.upphov, genre=k.genre, sprak=[k.sprak],
            datering_edtf=k.datering[0], datering_fran=k.datering[1], datering_till=k.datering[2],
            beskrivning=k.beskrivning, extern_url=f"{SAGADB}/{namn}"))
        n, _ = lagg_till_sagadb(paket, k, namn, "is", "originaltext", "non", 0)
        log.info("%-44s %4d passager original ur sagadb, %s", k.titel, n,
                 sagadb_oversattning(paket, k, namn, sagadb[namn]) or "ingen fri översättning")
        return
    paket.verk.append(Verk(
        id=k.verk_id, titel=k.titel, upphov=k.upphov, genre=k.genre, sprak=[k.sprak],
        datering_edtf=k.datering[0], datering_fran=k.datering[1], datering_till=k.datering[2],
        beskrivning=k.beskrivning, extern_url=sidlank(k.sida)))
    slug = k.verk_id.split(":")[-1]
    org_typ = "originaltext" if k.sprak == "non" else "oversattning"
    org_utg = f"utgava:heimskringla:{slug}:{k.sprak}"
    paket.utgavor.append((k.verk_id, Utgava(org_utg, f"{k.utgava}. heimskringla.no.", "Public domain enligt heimskringla.no")))

    if k.delsidor:
        kandidater = [l for l in lankar if l not in k.uteslut
                      and (k.delsidor == "alla" or l.endswith(k.delsidor)
                           or (k.delsidor.startswith("prefix:") and l.startswith(k.delsidor[7:])))]
        # API:t ger länkarna i bokstavsordning; delarna ska stå i sidans ordning
        kandidater.sort(key=lambda l: (w.find(f"[[{l}") if f"[[{l}" in w else len(w)))
        # Omdirigeringar ("Eiríkr saga jarls" → "Eiríks saga jarls") ska inte ge samma text två gånger
        sidor = list(dict.fromkeys(omdirigerad(l) for l in kandidater))
        n = 0
        for i, delsida in enumerate(sidor, 1):
            del_titel = re.sub(r"\s*\((?:Fagrskinna|Morkinskinna)\)$", "", delsida)
            n += lagg_till_text(paket, k, delsida, org_typ, k.sprak, org_utg, delprefix=f"{i}:",
                                deladress=del_titel, ordning_bas=i * 1000)
        log.info("%-44s %3d delsidor, %4d passager", k.titel, len(sidor), n)
        return

    n = lagg_till_text(paket, k, k.sida, org_typ, k.sprak, org_utg)
    if k.sprak != "non":
        log.info("%-44s %4d passager (%s)", k.titel, n, k.sprak)
        return
    rad = dict([k.oversattning]) if k.oversattning else sprakrad(w)
    for sprak in ("swe", "dan"):
        sida = rad.get(sprak)
        # Språktabellen kan länka en annan originaltext (verserna ur en skaldediktsutgåva)
        if not sida or sida in (k.sida, rad.get("non")):
            continue
        tw, _ = hamta_wikitext(sida)
        ar = tryckar(tw)
        if ar is None or ar > SENASTE_AR:
            log.info("%-44s %s-översättningen '%s' har tryckår %s och tas inte med", k.titel, sprak, sida, ar)
            continue
        utg = f"utgava:heimskringla:{slug}:{sprak}"
        paket.utgavor.append((k.verk_id, Utgava(
            utg, f"{titelsida(tw)[:300]}. heimskringla.no.", "Public domain")))
        m = lagg_till_text(paket, k, sida, "oversattning", sprak, utg, ordning_bas=100000)
        log.info("%-44s %4d passager original, %4d %s (%s %s)", k.titel, n, m, sprak, sida, ar)
        # En översättning räcker; svenska går före danska
        return
    fran_sagadb = sagadb_oversattning(paket, k, namn, sagadb[namn]) if namn in sagadb else None
    log.info("%-44s %4d passager original, %s", k.titel, n, fran_sagadb or "ingen fri översättning")


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="sagor_heimskringla",
            namn="heimskringla.no och sagadb.org: Íslendinga sögur, fornaldarsagor, kungakrönikor och Grágás",
            utgivare="heimskringla.no", url="https://heimskringla.no/wiki/Íslendinga_sögur",
            licens="Public domain enligt heimskringla.no (sajten anges som källa) och sagadb.org",
            version="2026-10"),
        verk=[])
    sagadb = sagadb_sprak()
    for k in islendinga_konfig() + OVRIGA:
        try:
            lagg_till_verk(paket, k, sagadb)
        except RuntimeError as e:
            log.warning("%s: %s", k.titel, e)
    for fil in sorted(OVERSATTNINGAR.glob("*.json")):
        paket.lagg_till_maskinoversattningar(fil, "fornvästnordiskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    log.info("%d verk, %d utgåvor, %d passager", len(paket.verk), len(paket.utgavor), len(paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

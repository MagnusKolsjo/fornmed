"""
Handregistrerade påståenden: Hygelac, Eadgils och Onela i Beowulf och deras
motsvarigheter i frankiska och fornnordiska källor.

Kretsen rymmer hela spektret mellan belagt och legendariskt:
- en uppgift med oberoende samtida stöd (Hygelacs räd, Gregorius av Tours),
- en senare källa som bara återger en äldre (Liber historiae Francorum),
- två oberoende traditioner om samma konflikt (Beowulf och Ynglinga saga),
- en omstridd identifiering med svensk räckvidd (gēatas = götar, jutar
  eller en litterär konstruktion),
- omstridda dateringar av både Beowulf och Ynglingatal.

Påståendena bygger på passager som tolkarna läst in (Beowulf, openMGH,
Heimskringla, Ynglingatal, Liber monstrorum), och citaten är hämtade ur dem.

Bedömningarna är registrerade som ogranskade (granskad = false). Referenserna
avser verkliga publikationer, men sammanfattningen av varje forskares
ståndpunkt ska kontrolleras mot publikationen innan den används som belägg.

Tolkarna för Beowulf, openMGH, Heimskringla, Ynglingatal och Liber monstrorum måste ha körts först.

Användning:
    python pastaenden_hygelac.py
"""

import logging

import db
from kallpaket import Kallpaket, Kallsamling, ladda

log = logging.getLogger("pastaenden_hygelac")

KALLSAMLING_ID = "pastaenden_hygelac"
REGISTRERAD_AV = "pastaenden_hygelac.py"


def ar(edtf_fran: int, edtf_till: int) -> tuple[int, int]:
    """Årsintervall som heltalsintervall ÅÅÅÅMMDD."""
    return edtf_fran * 10000 + 101, edtf_till * 10000 + 1231


# -----------------------------------------------------------------------------
# Samlingen äger inga verk; alla passager kommer från tolkarna
# -----------------------------------------------------------------------------

PAKET = Kallpaket(
    kallsamling=Kallsamling(
        id=KALLSAMLING_ID, namn="Handregistrerade påståenden: Hygelac och ynglingakretsen",
        utgivare=None, url=None, licens=None, version="1"),
    verk=[],
    befintliga_verk=["verk:beowulf", "verk:historia_francorum", "verk:liber_historiae_francorum",
                     "verk:ynglinga_saga", "verk:ynglingatal", "verk:liber_monstrorum"],
)

# -----------------------------------------------------------------------------
# Entiteter och identifieringar
# -----------------------------------------------------------------------------
# Varje namnform i en källa får en egen entitet; att de avser samma person
# eller folk är en identifiering som kan bedömas.

# (id, typ, namn, beskrivning)
ENTITETER = [
    ("person:hygelac", "person", "Hygelac", "Geaternas kung i Beowulf"),
    ("person:chlochilaicus", "person", "Chlochilaicus", "Danernas kung hos Gregorius av Tours"),
    ("person:huiglaucus", "person", "Huiglaucus", "Geternas kung i Liber monstrorum (Hugilaicus hos Haupt)"),
    ("person:theudebert", "person", "Theudebert I", "Frankisk kung, son till Theuderik I"),
    ("person:eadgils", "person", "Eadgils", "Ohtheres son i Beowulf"),
    ("person:onela", "person", "Onela", "Svearnas kung i Beowulf"),
    ("person:adils", "person", "Aðils", "Ynglingakung i Ynglingatal och Ynglinga saga"),
    ("person:ali", "person", "Áli", "Kung som besegras av Aðils i Ynglinga saga"),
    ("grupp:geatas", "grupp", "Gēatas", "Folket Hygelac och Beowulf tillhör i Beowulf"),
    ("grupp:dani", "grupp", "Dani", "Daner enligt Gregorius av Tours"),
    ("grupp:getae", "grupp", "Getae", "Geter, ett folk i antik och medeltida lärd geografi"),
    ("grupp:gotar", "grupp", "Götar", "Folk i Väster- och Östergötland"),
    ("grupp:jutar", "grupp", "Jutar", "Folk på Jylland"),
    ("plats:frisland", "plats", "Frisland", None),
    ("plats:vanern", "plats", "Vänern", None),
    ("plats:uppsala", "plats", "Uppsala", "Gamla Uppsala"),
]

# (id, entitet, identifierad_med, alternativgrupp, kommentar)
IDENTIFIERINGAR = [
    ("ident:hygelac=chlochilaicus", "person:hygelac", "person:chlochilaicus", None, None),
    ("ident:hygelac=huiglaucus", "person:hygelac", "person:huiglaucus", None, None),
    ("ident:eadgils=adils", "person:eadgils", "person:adils", None, None),
    ("ident:onela=ali", "person:onela", "person:ali", None,
     "Áli är norsk kung hos Snorre men svensk (Onela) i Beowulf"),
    ("ident:geatas=gotar", "grupp:geatas", "grupp:gotar", "geatas_identitet", None),
    ("ident:geatas=jutar", "grupp:geatas", "grupp:jutar", "geatas_identitet", None),
    ("ident:geatas=getae", "grupp:geatas", "grupp:getae", "geatas_identitet",
     "Innebär att gēatas är en lärd, litterär folkbeteckning snarare än ett historiskt folk"),
]

# -----------------------------------------------------------------------------
# Påståenden: vad varje passage hävdar
# -----------------------------------------------------------------------------
# Beowulf citeras efter Harrison & Sharp (fitt 19 = rad 1193–1251, fitt 34 =
# rad 2392–2460), Ynglinga saga efter Linder & Haggson (kap. 33 = kap. 29 hos
# Olson) och Ynglingatal efter citatens löpnummer i sagan (citat 16 = strofen
# om Aðils i kap. 33).

AAR_500TAL = ar(500, 599)
RADEN = ar(516, 534)

# (id, passage, subjekt, predikat, objekt_id, objekt_varde, plats, tid_edtf, (från, till), citat)
PASTAENDEN = [
    ("p:beowulf:hygelac_styr", "beowulf:fitt:19", "person:hygelac", "styr_over",
     "grupp:geatas", None, None, None, (None, None), "Higelāc Gēata"),
    ("p:beowulf:hygelac_faller", "beowulf:fitt:19", "person:hygelac", "dor",
     None, "faller i strid mot friserna", "plats:frisland", "05XX", AAR_500TAL,
     "fǣhðe tō Frȳsum"),
    ("p:hf:chlochilaicus_styr", "historia_francorum:iii:3", "person:chlochilaicus",
     "styr_over", "grupp:dani", None, None, None, (None, None), "Dani cum rege suo"),
    ("p:hf:chlochilaicus_dodas", "historia_francorum:iii:3", "person:theudebert",
     "dodar", "person:chlochilaicus", None, None, "0516/0534", RADEN, "interfectu rege"),
    ("p:lhf:chochilaicus_dodas", "liber_historiae_francorum:text:19",
     "person:theudebert", "dodar", "person:chlochilaicus", None, None, "0516/0534", RADEN, None),
    ("p:lm:huiglaucus_styr", "liber_monstrorum:1.3", "person:huiglaucus", "styr_over",
     "grupp:getae", None, None, None, (None, None), "qui imperavit Getis"),
    ("p:lm:huiglaucus_dodas", "liber_monstrorum:1.3", "person:huiglaucus", "dor",
     None, "dödad av frankerna", None, "05XX", AAR_500TAL, "a Francis occisus est"),
    ("p:beowulf:eadgils_dodar_onela", "beowulf:fitt:34", "person:eadgils", "dodar",
     "person:onela", None, None, "05XX", AAR_500TAL, "cyning ealdre binēat"),
    ("p:ys:adils_besegrar_ali", "ynglinga_saga:non:33", "person:adils", "besegrar",
     "person:ali", None, "plats:vanern", "05XX", AAR_500TAL,
     "áttu orrostu á Vænis ísi; þar féll Áli konungr"),
    ("p:yt:adils_dor", "ynglingatal:non:16", "person:adils", "dor",
     None, "faller av hästen", "plats:uppsala", "05XX", AAR_500TAL,
     "deyja skyldi Ála dólgr at Uppsölum"),
    ("p:ys:adils_dor", "ynglinga_saga:non:33", "person:adils", "dor",
     None, "faller av hästen vid diserblotet", "plats:uppsala", "05XX", AAR_500TAL,
     "Aðils konungr var at dísablóti"),
]

# (från, till, relation, kommentar)
RELATIONER = [
    ("p:hf:chlochilaicus_dodas", "p:beowulf:hygelac_faller", "stoder",
     "Oberoende frankisk källa, nära i tid, om samma räd"),
    ("p:lm:huiglaucus_dodas", "p:beowulf:hygelac_faller", "stoder",
     "Oberoende anglosaxisk tradition om en kung som dödas av frankerna"),
    ("p:lhf:chochilaicus_dodas", "p:hf:chlochilaicus_dodas", "beroende_av",
     "LHF bygger på Gregorius och tillför inget oberoende stöd"),
    ("p:ys:adils_besegrar_ali", "p:beowulf:eadgils_dodar_onela", "stoder",
     "Oberoende traditioner om samma konflikt; stödet gäller traditionen, "
     "inte nödvändigtvis händelsen"),
    ("p:ys:adils_dor", "p:yt:adils_dor", "beroende_av", "Snorre citerar Ynglingatal"),
]

# -----------------------------------------------------------------------------
# Bedömningar
# -----------------------------------------------------------------------------

KLAEBER = ("R. D. Fulk, Robert E. Bjork & John D. Niles (red.), Klaeber's Beowulf and the "
           "Fight at Finnsburg, 4 uppl., Toronto: University of Toronto Press 2008")
FULK = "R. D. Fulk, A History of Old English Meter, Philadelphia: University of Pennsylvania Press 1992"
KIERNAN = "Kevin S. Kiernan, Beowulf and the Beowulf Manuscript, New Brunswick: Rutgers University Press 1981"
NERMAN = "Birger Nerman, Det svenska rikets uppkomst, Stockholm 1925"
KRAG = ("Claus Krag, Ynglingatal og Ynglingesaga: en studie i historiske kilder, "
        "Oslo: Universitetsforlaget 1991 (Studia humaniora 2)")
FAHLBECK = ("Pontus Fahlbeck, \"Beowulfsqvädet såsom källa för nordisk fornhistoria\", "
            "Antiqvarisk tidskrift för Sverige 8 (1884)")
LEAKE = ("Jane Acomb Leake, The Geats of Beowulf: A Study in the Geographical Mythology of "
         "the Middle Ages, Madison: University of Wisconsin Press 1967")
SNORRI = "Snorri Sturluson, Heimskringla, prologen"

# (id, måltyp, mål, aspekt, värde, säkerhet, bedömare, publikation, år, motivering)
BEDOMNINGAR = [
    # Hygelacs räd
    ("b:klaeber:hf_raden", "pastaende", "p:hf:chlochilaicus_dodas", "historicitet", "belagd",
     "hog", "Fulk, Bjork & Niles", KLAEBER, 2008,
     "Räden återges av en samtida frankisk historiker och behandlas som den fasta "
     "historiska punkten i Beowulfs kronologi."),
    ("b:klaeber:beowulf_hygelac", "pastaende", "p:beowulf:hygelac_faller", "historicitet",
     "sannolik", "hog", "Fulk, Bjork & Niles", KLAEBER, 2008,
     "Diktens uppgift om Hygelacs fall i Frisland har en historisk kärna som "
     "bekräftas av Gregorius."),
    ("b:klaeber:ident_hygelac", "identifiering", "ident:hygelac=chlochilaicus", "identifiering",
     "sannolik", "hog", "Fulk, Bjork & Niles", KLAEBER, 2008, None),
    ("b:klaeber:ident_huiglaucus", "identifiering", "ident:hygelac=huiglaucus", "identifiering",
     "sannolik", "hog", "Fulk, Bjork & Niles", KLAEBER, 2008, None),

    # Vilka var gēatas?
    ("b:klaeber:geatas_gotar", "identifiering", "ident:geatas=gotar", "identifiering",
     "sannolik", "medel", "Fulk, Bjork & Niles", KLAEBER, 2008,
     "Gēatas motsvarar etymologiskt fornvästnordiska gautar, dvs. götar."),
    ("b:klaeber:geatas_jutar", "identifiering", "ident:geatas=jutar", "identifiering",
     "osannolik", "medel", "Fulk, Bjork & Niles", KLAEBER, 2008, None),
    ("b:fahlbeck:geatas_jutar", "identifiering", "ident:geatas=jutar", "identifiering",
     "sannolik", "medel", "Pontus Fahlbeck", FAHLBECK, 1884,
     "Argumenterade för att diktens gēatas var jutar."),
    ("b:leake:geatas_getae", "identifiering", "ident:geatas=getae", "identifiering",
     "sannolik", "medel", "Jane Acomb Leake", LEAKE, 1967,
     "Läser gēatas som diktens återgivning av de lärda geterna, en del av medeltidens "
     "geografiska mytologi snarare än ett historiskt folk."),

    # Eadgils och Onela / Aðils och Áli
    ("b:klaeber:ident_eadgils", "identifiering", "ident:eadgils=adils", "identifiering",
     "sannolik", "hog", "Fulk, Bjork & Niles", KLAEBER, 2008, None),
    ("b:klaeber:ident_onela", "identifiering", "ident:onela=ali", "identifiering",
     "sannolik", "medel", "Fulk, Bjork & Niles", KLAEBER, 2008, None),
    ("b:nerman:adils_ali", "pastaende", "p:ys:adils_besegrar_ali", "historicitet", "sannolik",
     "medel", "Birger Nerman", NERMAN, 1925,
     "Behandlar ynglingakungarna som historiska och kopplar dem till Uppsala högar."),
    ("b:nerman:adils_dor", "pastaende", "p:yt:adils_dor", "historicitet", "sannolik",
     "medel", "Birger Nerman", NERMAN, 1925, None),
    ("b:krag:adils_dor", "pastaende", "p:yt:adils_dor", "historicitet", "legendarisk",
     "medel", "Claus Krag", KRAG, 1991,
     "Daterar Ynglingatal till 1100-talet; dikten är då inget självständigt belägg "
     "för 500-talets kungar."),

    # Dateringar av verken
    ("b:fulk:beowulf_datering", "verk", "verk:beowulf", "datering", "../0825", "medel",
     "R. D. Fulk", FULK, 1992,
     "Metriska kriterier talar för tillkomst senast omkring 725 (mercisk) eller 825 "
     "(nordhumbrisk)."),
    ("b:kiernan:beowulf_datering", "verk", "verk:beowulf", "datering", "0975/1025", "medel",
     "Kevin S. Kiernan", KIERNAN, 1981,
     "Dikten i sin bevarade form är samtida med handskriften."),
    ("b:snorri:ynglingatal_datering", "verk", "verk:ynglingatal", "datering", "0850/0950",
     "medel", "Snorri Sturluson", SNORRI, None,
     "Tillskriver dikten Þjóðólfr ór Hvini vid Harald hårfagres tid; en medeltida "
     "bedömning, registrerad som sådan."),
    ("b:krag:ynglingatal_datering", "verk", "verk:ynglingatal", "datering", "1100/1199",
     "medel", "Claus Krag", KRAG, 1991, None),
]

MALKOLUMN = {
    "pastaende": "pastaende_id",
    "verk": "verk_id",
    "vittne": "vittne_id",
    "identifiering": "identifiering_id",
}


def kontrollera_citat(conn) -> None:
    """Varje citat ska stå ordagrant i sin passage; annars är påståendet felkopplat."""
    p, ph = db._prefix(), db._ph()
    cur = conn.cursor()
    for pid, passage, *_, citat in PASTAENDEN:
        cur.execute(f"SELECT text FROM {p}passage WHERE id = {ph}", (passage,))
        rad = cur.fetchone()
        if rad is None:
            raise ValueError(f"{pid}: passagen {passage} finns inte; kör tolken först")
        if citat and citat not in " ".join(rad[0].split()):
            raise ValueError(f"{pid}: citatet '{citat}' står inte i {passage}")


def ladda_pastaenden() -> None:
    """Skriver verk, passager, entiteter, påståenden och bedömningar. Idempotent."""
    db.initiera_schema()
    ladda(PAKET)
    conn = db._hamta_db()
    try:
        kontrollera_citat(conn)
        db.upsert(conn, "entitet", ["id", "typ", "namn", "beskrivning"], ["id"], ENTITETER)
        db.upsert(conn, "identifiering",
                  ["id", "entitet_id", "identifierad_med", "alternativgrupp", "kommentar"],
                  ["id"], IDENTIFIERINGAR)
        db.upsert(conn, "pastaende",
                  ["id", "passage_id", "subjekt_id", "predikat", "objekt_id", "objekt_varde",
                   "plats_id", "tid_edtf", "tid_fran", "tid_till", "citat", "extraktion",
                   "extraherad_av"], ["id"],
                  [(*p[:8], *p[8], p[9], "manuell", REGISTRERAD_AV) for p in PASTAENDEN])
        db.upsert(conn, "pastaende_relation", ["fran_id", "till_id", "relation", "kommentar"],
                  ["fran_id", "till_id", "relation"], RELATIONER)

        # Varje måltyp skrivs för sig eftersom målet ligger i olika kolumner
        for maltyp, kolumn in MALKOLUMN.items():
            db.upsert(conn, "bedomning",
                      ["id", kolumn, "aspekt", "varde", "sakerhet", "bedomare", "publikation",
                       "ar", "motivering", "registrerad_av"], ["id"],
                      [(b[0], b[2], *b[3:], REGISTRERAD_AV) for b in BEDOMNINGAR
                       if b[1] == maltyp])
    finally:
        conn.close()

    log.info("%d entiteter, %d identifieringar, %d påståenden, %d relationer, %d bedömningar",
             len(ENTITETER), len(IDENTIFIERINGAR), len(PASTAENDEN), len(RELATIONER),
             len(BEDOMNINGAR))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ladda_pastaenden()

"""
Skriver en utskrivbar beskrivning av databasens schema som HTML.

Tabellerna, kolumnerna, typerna, nycklarna, kopplingarna och villkoren läses
ur databasen själv, så att beskrivningen alltid stämmer med schemat.
Förklaringarna av tabeller och kolumner står här nedan. Sidan är gjord för
utskrift som PDF i liggande A4.

Användning:
    python databasschema.py rapporter/databasschema.html
"""

import argparse
import html
import math
from datetime import date

import db
from fragor import _rader

# -----------------------------------------------------------------------------
# Förklaringar
# -----------------------------------------------------------------------------

GRUPPER = [
    ("Källor", "Texterna i fyra nivåer: verket, dess bevarade vittnen, utgåvorna och de citerbara passagerna, "
               "med källsamlingen de lästs in ur och sökningens chunkar och vektorer.",
     ["kallsamling", "verk", "verk_plats", "vittne", "utgava", "passage", "chunk", "embedding", "sdhk_brev"]),
    ("Entiteter och begrepp", "Personer, platser, folk, institutioner, ämbeten och begrepp som delas mellan "
                              "källorna, med namnformer, identifieringar, termer och ordböcker.",
     ["entitet", "entitet_namnform", "plats_uppgift", "identifiering", "term", "begreppsrelation", "ordboksartikel"]),
    ("Påståenden och bedömningar", "Vad en passage hävdar, hur påståenden hänger ihop och forskningens "
                                   "omdömen om påståenden, verk, vittnen och identifieringar.",
     ["pastaende", "pastaende_relation", "bedomning"]),
    ("Auktoriteter", "Längderna över regenter, biskopar och påvar.",
     ["auktoritetslangd", "auktoritet", "auktoritet_titel"]),
    ("Register och drift", "Kontrollerade värden, databasens leveranser och sökindexet, som härleds ur övriga "
                           "tabeller.",
     ["vokabular", "leverans", "sokpost", "sokpost_plats"]),
    ("Vyer", "Sammanställningar som räknas fram ur tabellerna när de läses; de lagrar inget själva.",
     ["pastaende_oversikt", "omstridda", "konkurrerande_identifieringar"]),
]

TABELLER = {
    "kallsamling": "Ett dataset som materialet har lästs in ur, till exempel SDHK, Rundata eller Fornsvenska textbanken, med utgivare, licens och version.",
    "verk": "Texten som intellektuell enhet: ett brev, en runinskrift, en lag, en saga, en krönika. Verkets datering är textens tillkomst, skild från handskrifternas och händelsernas.",
    "plats_uppgift": "Var en plats ligger i dag: nutida namn, land, län, kommun, socken och koordinater. Bedömningar med metod och granskningsstatus, skilda från källans namnform. Fylls av platsregister.py och platser.py.",
    "sokpost": "Sökindexet: ett sökbart verk eller en entitet med rubrik, sammanfattning och tre tider: tillkomst, förlaga (äldsta daterade vittne) och händelse (påståendenas tid). Byggs om av sokindex.py.",
    "sokpost_plats": "Sökpostens platser i rollerna händelse, tillkomst, förvaring och läge, med de platser som visas först på kartan markerade. Byggs om av sokindex.py.",
    "verk_plats": "Verkets geografiska platser som entiteter: brevens utfärdandeort och runinskrifternas fyndplats, socken, härad, kommun, område och förvaring. Ett verk kan ha flera platser. Fylls av platser.py.",
    "vittne": "En fysisk eller registrerad överlevnad av verket: original, avskrift, registratur eller tryck, med egen datering.",
    "utgava": "En tryckt eller digital utgåva av verket, och därmed en språkversion: original, översättning, maskinöversättning eller maskintranskription.",
    "passage": "Den citerbara textenheten: en regest, en flock i en lag, ett kapitel, en strof eller en inskrifts translitterering. Sökningens fulltextindex ligger här.",
    "chunk": "En passage delad i bitar om högst 800 tecken med överlapp, för den semantiska sökningen. Bara texter på moderna språk och de latinska krönikorna delas.",
    "embedding": "Vektorn för en chunk, beräknad med en av de två embeddingmodellerna. Har ett vektorindex (HNSW) per modell.",
    "sdhk_brev": "Riksarkivets SDHK-poster exakt som i källans CSV-fil. Den normaliserade strukturen (verk, vittne, utgåva, passage) byggs ur denna tabell.",
    "entitet": "En person, plats, grupp eller folk, institution, indelning, ett ämbete, en händelse eller ett begrepp. Delas mellan källorna och behåller sitt id mellan versionerna av databasen.",
    "entitet_namnform": "De former ett namn har i källorna (Hygelac, Chlochilaicus, Huiglaucus), med språk och passagen där formen förekommer.",
    "identifiering": "Att två entiteter avser samma person eller sak. En identifiering är ett omdöme som kan bedömas och ifrågasättas, inte en sammanslagning.",
    "term": "Ett begrepps termer på olika språk och i olika historiska former (leþunger, ledhunger, leiðangr, expeditio), med länk till ordboksartikeln.",
    "begreppsrelation": "Relationer mellan begrepp enligt SKOS: bredare, smalare och relaterade begrepp.",
    "ordboksartikel": "En betydelse i Schlyters eller Söderwalls ordbok, en rad per betydelse.",
    "pastaende": "Vad en passage hävdar: subjekt, predikat och objekt eller värde, med tid, plats och citat. Beskriver vad källan hävdar, inte vad som hände.",
    "pastaende_relation": "Relationer mellan påståenden: stöder, motsäger eller är beroende av. Beroende källor korroborerar inte varandra.",
    "bedomning": "En forskares eller publikations omdöme om exakt ett mål: ett påstående, ett verk, ett vittne eller en identifiering. Flera bedömningar av samma mål gör oenighet synlig.",
    "auktoritetslangd": "En längd över ämbetsinnehavare: regenter, biskopar eller påvar, med licens och ursprung.",
    "auktoritet": "En person i en längd, med levnadsår och Wikidata-id. person_id är personens entitets-id.",
    "auktoritet_titel": "En titel med säte och år för en person i en längd. En person kan ha flera titlar och säten.",
    "vokabular": "Kontrollerade värden för alla klassificeringar: genre, passagetyp, predikat, bedömningsaspekter och deras värden, deltyp med flera. Definieras i vokabular.py.",
    "leverans": "En kopia av databasen som lämnat utvecklingsdatorn, med antal per tabell och skillnaden mot förra leveransen. Skrivs av leverans.py.",
    "pastaende_oversikt": "Varje påstående med källans genre och datering, det minsta möjliga tidsavståndet mellan händelse och källa, antal bedömningar och om de går isär.",
    "omstridda": "Mål där minst två bedömningar inom samma aspekt ger olika värden.",
    "konkurrerande_identifieringar": "Entiteter där flera uteslutande identifieringar har bedömts som säkra eller sannolika.",
}

KOLUMNER = {
    "kallsamling": {"id": "Kort namn, t.ex. sdhk eller rundata", "namn": "Källsamlingens namn", "utgivare": "Den som ger ut materialet",
                    "url": "Källsamlingens webbplats", "licens": "Licens för materialet", "version": "Version eller ögonblicksbild",
                    "importerad": "När materialet lästes in"},
    "verk": {"id": "Verkets id, t.ex. verk:lag:aldre_vastgotalagen eller sdhk:1000", "kallsamling_id": "Källsamlingen verket lästs in ur",
             "titel": "Verkets titel", "upphov": "Författare, utfärdare eller ristare", "genre": "Källgenre (vokabulär genre)",
             "sprak": "Verkets språk, ISO 639-3", "utfardandeort": "Var ett brev utfärdades", "datering_edtf": "Datering i EDTF, t.ex. 1276-05-23 eller 1375/1378?",
             "datering_fran": "Tidigaste möjliga datum, ÅÅÅÅMMDD", "datering_till": "Senaste möjliga datum, ÅÅÅÅMMDD", "datering_anm": "Anmärkning om dateringen",
             "beskrivning": "Kort beskrivning", "extern_url": "Länk till verket hos källan", "extra": "Övriga uppgifter, t.ex. runinskrifters fyndort och bildlänkar"},
    "sokpost": {"id": "Verkets eller entitetens id", "objekttyp": "verk eller entitet", "undertyp": "Verkets genre eller entitetens typ",
                "soknamn": "Rubrik och namnformer i sökform, för namnsökning", "forlaga_typ": "Vittnestypen för det äldsta daterade vittnet",
                "handelse_fran": "Tidigaste tid i påståendena (ÅÅÅÅMMDD)", "handelse_till": "Senaste tid i påståendena (ÅÅÅÅMMDD)",
                "tid_fran": "Den tid som visas först: händelsen om den är känd, annars tillkomsten", "tid_kalla": "handelse eller tillkomst"},
    "sokpost_plats": {"sokpost_id": "Sökposten", "plats_id": "Platsen", "roll": "handelse, tillkomst, forvaring eller lage (vokabulär sokplatsroll)",
                      "primar": "Visas först på kartan", "osaker": "Kopplingen till platsen är osäker eller härledd", "antal": "Antal påståenden som anger platsen"},
    "verk_plats": {"verk_id": "Verket", "plats_id": "Platsen", "roll": "utfardandeort, fyndplats, socken, harad, kommun, omrade eller forvaring (vokabulär platsroll)",
                   "namnform": "Platsen som den står i källan", "osaker": "Källan anger orten med frågetecken eller som ett alternativ",
                   "harledd": "Orten står inom parentes eller hakparentes i källan, eller läget anges i förhållande till platsen"},
    "plats_uppgift": {"entitet_id": "Platsen", "slag": "Stad, by, gård, slott, kloster, socken m.m. (vokabulär platsslag)", "nutida_namn": "Platsens nutida namn",
                      "land_id": "Nutida land", "landskap_id": "Landskap", "lan_id": "Nutida län", "kommun_id": "Nutida kommun", "socken_id": "Socken",
                      "ingar_i_id": "Större plats som platsen är en del av", "latitud": "Latitud, WGS84", "longitud": "Longitud, WGS84",
                      "kalla": "Varifrån uppgifterna kommer", "metod": "auktoritet, regel eller sprakmodell", "granskad": "En människa har kontrollerat kopplingen", "anm": "Anmärkning, t.ex. om namnbyte"},
    "vittne": {"id": "Vittnets id", "verk_id": "Verket", "typ": "Original, avskrift, registratur, tryck m.m. (vokabulär vittnestyp)",
               "beskrivning": "Beskrivning ur källan", "signum": "Arkiv- eller handskriftssignum", "datering_edtf": "Vittnets datering i EDTF",
               "datering_fran": "Tidigaste datum, ÅÅÅÅMMDD", "datering_till": "Senaste datum, ÅÅÅÅMMDD", "iiif_manifest": "Länk till digitaliserade sidbilder"},
    "utgava": {"id": "Utgåvans id; maskinöversättningar slutar på :sv_modell", "verk_id": "Verket", "referens": "Bibliografisk referens",
               "licens": "Utgåvans licens", "sprak": "Utgåvans språk, ISO 639-3; tomt när utgåvan har flera språk",
               "typ": "original, oversattning, maskinoversattning eller maskintranskription", "roll": "huvudtext eller skolier",
               "oversattare": "Översättare för tryckta översättningar", "ar": "Utgivningsår"},
    "passage": {"id": "Passagens id; översättningar har originalets id med språksuffix, t.ex. :sv", "verk_id": "Verket",
                "utgava_id": "Utgåvan; tomt för SDHK:s regester", "typ": "originaltext, regest, oversattning, normaliserad eller skolion",
                "adress": "Passagens adress i verket, t.ex. ÄVgL Kkb 1 — Kirkiu bolkær, flock 1", "ordning": "Ordningen i utgåvan",
                "sprak": "Passagens språk, ISO 639-3", "text": "Texten", "sokvektor": "Fulltextindex; svensk stemming för modern svenska",
                "url": "Länk till sidbild eller sida i den digitala utgåvan", "del": "Del av verket: bok, balk, saga eller avsnitt",
                "del_typ": "Delens typ (vokabulär deltyp)"},
    "chunk": {"id": "Löpnummer", "passage_id": "Passagen", "chunk_nr": "Chunkens nummer i passagen", "text": "Chunkens text"},
    "embedding": {"chunk_id": "Chunken", "modell": "Embeddingmodellen som beräknade vektorn", "vektor": "Vektor med 768 dimensioner"},
    "sdhk_brev": {"sdhk_nr": "SDHK-numret", "titel": "Rubrik", "utfardare": "Utfärdarfältet", "datum": "Datering som i källan",
                  "ort": "Utfärdandeort", "sprak": "Språk", "regest": "Riksarkivets regest", "kommentar": "Kommentar", "tillagg": "Tillägg",
                  "sigill": "Sigill", "original": "Original (vittne)", "medeltida_avskrift": "Medeltida avskrift", "eftermedeltida_avskrift": "Eftermedeltida avskrift",
                  "medeltida_registratur": "Medeltida registratur", "eftermedeltida_registratur": "Eftermedeltida registratur", "fotokopia": "Fotokopia",
                  "tryck": "Tryck", "tryckt_regest": "Tryckt regest", "faksimil": "Faksimil", "oversattning": "Översättning", "edition": "Edition (originaltext)"},
    "entitet": {"id": "Entitetens id, t.ex. person:sverker_d_a eller begrepp:ledung; byts aldrig", "typ": "person, plats, grupp, institution, indelning, ambete, handelse, begrepp",
                "namn": "Det namn entiteten visas med", "beskrivning": "Beskrivning", "wikidata_id": "Wikidata-id", "extra": "Övriga uppgifter"},
    "entitet_namnform": {"entitet_id": "Entiteten", "namnform": "Namnformen", "sprak": "Namnformens språk", "passage_id": "Passagen där formen förekommer"},
    "identifiering": {"id": "Identifieringens id", "entitet_id": "Den ena entiteten", "identifierad_med": "Den andra entiteten",
                      "alternativgrupp": "Identifieringar i samma grupp utesluter varandra", "kommentar": "Grunden för identifieringen"},
    "term": {"id": "Termens id", "entitet_id": "Begreppet", "term": "Termen", "sprak": "Språk, ISO 639-3; fsv för fornsvenska",
             "termtyp": "Termens typ (vokabulär termtyp)", "sokform": "Normaliserad form för sökning", "artikel_id": "Ordboksartikeln om termen",
             "registrerad_av": "Vem som registrerade termen", "granskad": "Om termen är granskad"},
    "begreppsrelation": {"fran_id": "Begreppet", "till_id": "Det andra begreppet", "relation": "bredare, smalare eller relaterat (vokabulär begreppsrelation)"},
    "ordboksartikel": {"id": "Artikelns id", "kallsamling_id": "Ordboken", "lemma": "Uppslagsordet", "lemgram": "Gemensam nyckel för samma ord i ordböckerna",
                       "ordklass": "Ordklass", "betydelse_nr": "Betydelsens nummer", "definition": "Ordbokens definition", "former": "Ordets former",
                       "sokform": "Normaliserad form för sökning", "sokvektor": "Fulltextindex"},
    "pastaende": {"id": "Påståendets id, bildat av passage, predikat, subjekt och objekt", "passage_id": "Passagen som hävdar påståendet",
                  "subjekt_id": "Subjektet", "predikat": "Vad som hävdas (vokabulär predikat)", "objekt_id": "Objektet när det är en entitet",
                  "objekt_varde": "Objektet när det är ett värde, t.ex. ett bötesbelopp eller ett verks id", "plats_id": "Platsen",
                  "tid_edtf": "Tid i EDTF", "tid_fran": "Tidigaste datum, ÅÅÅÅMMDD", "tid_till": "Senaste datum, ÅÅÅÅMMDD",
                  "citat": "Ordagrant citat ur passagens originaltext", "extraktion": "manuell, regel eller modell", "extraherad_av": "Skript eller modell som extraherade",
                  "granskad": "Om påståendet är granskat", "granskad_av": "Vem som granskade", "skapad": "När påståendet registrerades"},
    "pastaende_relation": {"fran_id": "Påståendet", "till_id": "Det andra påståendet", "relation": "stoder, motsager eller beroende_av",
                           "kommentar": "Kommentar"},
    "bedomning": {"id": "Bedömningens id", "pastaende_id": "Målet, om det är ett påstående", "verk_id": "Målet, om det är ett verk",
                  "vittne_id": "Målet, om det är ett vittne", "identifiering_id": "Målet, om det är en identifiering",
                  "aspekt": "Vad som bedöms: historicitet, akthet, datering, identifiering, titulatur m.m.", "varde": "Bedömningen, ur vokabulären för aspekten",
                  "sakerhet": "Hur säker bedömningen är", "bedomare": "Forskaren eller källan som bedömer", "publikation": "Publikationen",
                  "publikation_id": "DOI, Libris-id eller liknande", "sidor": "Sidor i publikationen", "motivering": "Motivering",
                  "ar": "Publikationsår", "registrerad_av": "Vem som förde in bedömningen", "granskad": "Om bedömningen är kontrollerad mot publikationen",
                  "skapad": "När bedömningen registrerades"},
    "auktoritetslangd": {"id": "regenter, biskopar eller pavar", "namn": "Längdens namn", "beskrivning": "Beskrivning ur källfilen",
                         "licens": "Licens", "kalla": "Ursprung", "hamtad": "När längden hämtades"},
    "auktoritet": {"langd_id": "Längden", "person_id": "Personens entitets-id", "namn": "Namn", "fodd": "Födelseår", "dod": "Dödsår",
                   "ordningstal": "Ordningstal, t.ex. för påvar", "anm": "Anmärkning, t.ex. motpåve", "wikidata_id": "Wikidata-id",
                   "wikipedia": "Artikel på svenska Wikipedia"},
    "auktoritet_titel": {"langd_id": "Längden", "person_id": "Personen", "nr": "Titelns nummer för personen", "titel": "kung, biskop, arkebiskop, pave m.m.",
                         "sate": "Rike eller stift som i längden", "sate_id": "Platsen som entitet", "fran": "Första år", "till": "Sista år", "ar_text": "Längdens ursprungliga årsuttryck"},
    "vokabular": {"schema": "Klassificeringen värdet hör till, t.ex. genre", "kod": "Värdets kod", "etikett": "Värdets namn",
                  "beskrivning": "Förklaring", "ordning": "Ordning i listor"},
    "leverans": {"id": "Tidpunkt som ÅÅÅÅMMDD-TTMMSS", "tidpunkt": "När leveransen registrerades", "anmarkning": "Vad leveransen innehåller",
                 "antal": "Antal rader per tabell och verk per källsamling", "andringar": "Skillnaden mot förra leveransen"},
    "pastaende_oversikt": {"id": "Påståendet", "subjekt_id": "Subjektet", "predikat": "Predikatet", "objekt_id": "Objektet som entitet",
                           "objekt_varde": "Objektet som värde", "tid_edtf": "Påståendets tid", "verk_id": "Källans verk",
                           "tidsavstand_ar": "Minsta möjliga antal år mellan händelse och källa", "antal_bedomningar": "Antal bedömningar",
                           "omstridd": "Om bedömningarna av historiciteten går isär", "verk_titel": "Källans titel", "genre": "Källans genre",
                           "verk_datering": "Källans datering"},
    "omstridda": {"mal_id": "Målets id", "maltyp": "pastaende, verk, vittne eller identifiering", "aspekt": "Aspekten",
                  "antal_bedomningar": "Antal bedömningar", "varden": "De olika värdena"},
    "konkurrerande_identifieringar": {"alternativgrupp": "Gruppen av uteslutande identifieringar", "entitet_id": "Entiteten",
                                      "antal_alternativ": "Antal alternativ som bedömts som säkra eller sannolika", "alternativ": "Alternativen med bedömare"},
}

# Kopplingar som inte är främmande nycklar i databasen men följs av koden
LOGISKA = [
    ("auktoritet", "person_id", "entitet", "id", "Personen i längden är en entitet med samma id"),
    ("sdhk_brev", "sdhk_nr", "verk", "id", "Brevet blir verket sdhk:{sdhk_nr}"),
    ("pastaende", "objekt_varde", "verk", "id", "För predikatet utfardar är värdet brevets verk-id"),
]

TYPER = {"text": "text", "int4": "heltal", "int8": "heltal (stort)", "bool": "sant/falskt", "jsonb": "JSON", "timestamptz": "tidpunkt",
         "_text": "textlista", "vector": "vektor(768)", "tsvector": "sökindex"}


# -----------------------------------------------------------------------------
# Läsning ur databasen
# -----------------------------------------------------------------------------

def las_schema() -> dict:
    kolumner = _rader("""
        SELECT c.table_name, c.column_name, c.udt_name, c.is_nullable, c.column_default, c.is_generated,
               t.table_type
        FROM information_schema.columns c
        JOIN information_schema.tables t ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = 'fornmed' ORDER BY c.table_name, c.ordinal_position
    """)
    nycklar = _rader("""
        SELECT con.conrelid::regclass::text AS tabell, con.contype AS typ,
               array_to_string(ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY k(n, i)
                                     JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.n
                                     ORDER BY k.i), ',') AS kolumner,
               con.confrelid::regclass::text AS mal,
               array_to_string(ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY k(n, i)
                                     JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.n
                                     ORDER BY k.i), ',') AS malkolumner,
               con.confdeltype AS vid_borttagning, pg_get_constraintdef(con.oid) AS definition
        FROM pg_constraint con
        WHERE con.connamespace = 'fornmed'::regnamespace
    """)
    antal = {r["relname"]: r["n"] for r in _rader("""
        SELECT c.relname, c.reltuples::bigint AS n FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'fornmed' AND c.relkind = 'r'
    """)}
    # reltuples är en uppskattning och -1 för tabeller som aldrig analyserats
    for tabell, n in list(antal.items()):
        if n < 0 or n < 1000:
            antal[tabell] = _rader(f"SELECT count(*) AS n FROM fornmed.{tabell}")[0]["n"]

    schema: dict[str, dict] = {}
    for r in kolumner:
        t = schema.setdefault(r["table_name"], {"vy": r["table_type"] == "VIEW", "kolumner": [], "pk": [], "fk": [],
                                                "unik": [], "villkor": []})
        t["kolumner"].append(r)
    for n in nycklar:
        tabell = n["tabell"].removeprefix("fornmed.")
        mal = (n["mal"] or "").removeprefix("fornmed.")
        if tabell not in schema:
            continue
        if n["typ"] == "p":
            schema[tabell]["pk"] = n["kolumner"].split(",")
        elif n["typ"] == "f":
            schema[tabell]["fk"].append({"kolumner": n["kolumner"].split(","), "mal": mal,
                                         "malkolumner": n["malkolumner"].split(","), "vid_borttagning": n["vid_borttagning"]})
        elif n["typ"] == "u":
            schema[tabell]["unik"].append(n["kolumner"].split(","))
        elif n["typ"] == "c":
            schema[tabell]["villkor"].append(n["definition"])
    for tabell, t in schema.items():
        t["antal"] = antal.get(tabell)
    return schema


# -----------------------------------------------------------------------------
# Översiktsdiagram
# -----------------------------------------------------------------------------

# Rutornas läge i diagrammet (x, y); bredd och höjd är gemensamma
PLATSER = {
    "kallsamling": (20, 30), "verk": (210, 30), "verk_plats": (20, 170), "vittne": (400, 0), "utgava": (400, 75), "passage": (590, 30),
    "chunk": (780, 30), "embedding": (960, 30), "sdhk_brev": (210, 130),
    "bedomning": (400, 200), "pastaende": (590, 200), "pastaende_relation": (780, 150),
    "entitet_namnform": (780, 260), "identifiering": (400, 340), "entitet": (590, 340), "plats_uppgift": (590, 430),
    "begreppsrelation": (780, 360), "ordboksartikel": (20, 300), "term": (210, 400),
    "auktoritetslangd": (20, 490), "auktoritet": (210, 490), "auktoritet_titel": (400, 490),
    "vokabular": (960, 470), "leverans": (960, 540), "sokpost": (780, 470), "sokpost_plats": (780, 540),
}
BREDD, HOJD = 150, 40
FARGER = {"Källor": "#244A63", "Entiteter och begrepp": "#426C62", "Påståenden och bedömningar": "#93483E",
          "Auktoriteter": "#8B641E", "Register och drift": "#536166"}


def _kant(x1, y1, x2, y2) -> tuple[float, float]:
    """Punkten där linjen från rutans mitt (x1, y1) mot (x2, y2) lämnar rutan."""
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return x1, y1
    sx = (BREDD / 2) / abs(dx) if dx else math.inf
    sy = (HOJD / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return x1 + dx * s, y1 + dy * s


def diagram(schema: dict) -> str:
    grupp_av = {t: g for g, _, tabeller in GRUPPER for t in tabeller}
    linjer, rutor = [], []

    def linje(fran, till, streckad, etikett):
        (fx, fy), (tx, ty) = PLATSER[fran], PLATSER[till]
        cx1, cy1, cx2, cy2 = fx + BREDD / 2, fy + HOJD / 2, tx + BREDD / 2, ty + HOJD / 2
        if fran == till:
            # Självreferens (begreppsrelation, identifiering) ritas som en ögla
            x, y = fx + BREDD, fy + 8
            linjer.append(f'<path d="M{x},{y} c 28,-6 28,30 0,24" class="fk" marker-end="url(#pil)"/>')
            return
        x1, y1 = _kant(cx1, cy1, cx2, cy2)
        x2, y2 = _kant(cx2, cy2, cx1, cy1)
        klass = "logisk" if streckad else "fk"
        linjer.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{klass}" '
                      f'marker-end="url(#pil)"><title>{html.escape(etikett)}</title></line>')

    ritade = set()
    for tabell, t in schema.items():
        if tabell not in PLATSER:
            continue
        for fk in t["fk"]:
            if fk["mal"] in PLATSER and (tabell, fk["mal"]) not in ritade:
                ritade.add((tabell, fk["mal"]))
                linje(tabell, fk["mal"], False, f"{tabell}.{','.join(fk['kolumner'])} → {fk['mal']}")
    for tabell, kolumn, mal, malkolumn, forklaring in LOGISKA:
        linje(tabell, mal, True, f"{tabell}.{kolumn} → {mal}.{malkolumn}: {forklaring}")

    for tabell, (x, y) in PLATSER.items():
        if tabell not in schema:
            continue
        farg = FARGER.get(grupp_av.get(tabell), "#536166")
        antal = schema[tabell]["antal"]
        rutor.append(
            f'<g><rect x="{x}" y="{y}" width="{BREDD}" height="{HOJD}" rx="3" fill="#FFFDFC" stroke="{farg}" stroke-width="1.6"/>'
            f'<rect x="{x}" y="{y}" width="5" height="{HOJD}" fill="{farg}"/>'
            f'<text x="{x + 12}" y="{y + 17}" class="namn">{tabell}</text>'
            f'<text x="{x + 12}" y="{y + 32}" class="antal">{_tal(antal)} rader</text></g>')

    return f"""<svg viewBox="-5 -10 1125 600" class="diagram" role="img" aria-label="Tabellerna och deras kopplingar">
<defs><marker id="pil" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="#536166"/></marker></defs>
{''.join(linjer)}
{''.join(rutor)}
</svg>"""


# -----------------------------------------------------------------------------
# Tabellerna
# -----------------------------------------------------------------------------

def _tal(n) -> str:
    return f"{n:,}".replace(",", " ") if isinstance(n, int) else "–"


def _typ(k: dict) -> str:
    return TYPER.get(k["udt_name"], k["udt_name"])


def _krav(k: dict, t: dict) -> tuple[str, str]:
    """(text, klass) för om kolumnen alltid har ett värde."""
    if t["vy"]:
        return "beräknas", "berakn"
    if k["is_generated"] == "ALWAYS":
        return "beräknas", "berakn"
    if k["is_nullable"] == "NO":
        standard = k["column_default"]
        if standard and "nextval" in standard:
            return "obligatorisk, löpnummer", "oblig"
        if standard:
            varde = standard.split("::")[0].strip("'")
            return f"obligatorisk (standard {varde})", "oblig"
        return "obligatorisk", "oblig"
    return "frivillig", "friv"


VID_BORTTAGNING = {"c": "tas bort med", "n": "töms", "a": "hindrar", "r": "hindrar", "d": "standardvärde"}


def tabellkort(tabell: str, t: dict) -> str:
    fk_per_kolumn = {}
    for fk in t["fk"]:
        for kolumn, malkolumn in zip(fk["kolumner"], fk["malkolumner"]):
            fk_per_kolumn[kolumn] = (fk["mal"], malkolumn, fk["vid_borttagning"])
    logiska = {k: (m, mk, f) for tt, k, m, mk, f in LOGISKA if tt == tabell}
    unika = {k for u in t["unik"] for k in u}
    rader = []
    for k in t["kolumner"]:
        namn = k["column_name"]
        nyckel = []
        if namn in t["pk"]:
            nyckel.append('<span class="pk">PK</span>' + (" (del av)" if len(t["pk"]) > 1 else ""))
        if namn in unika:
            nyckel.append('<span class="unik">UNIK</span>' + (" (tillsammans)" if any(len(u) > 1 and namn in u for u in t["unik"]) else ""))
        if namn in fk_per_kolumn:
            mal, malkolumn, regel = fk_per_kolumn[namn]
            nyckel.append(f'<span class="fk">FK</span> → {mal}.{malkolumn}')
        if namn in logiska:
            mal, malkolumn, _ = logiska[namn]
            nyckel.append(f'<span class="logisk">koppling</span> → {mal}.{malkolumn}')
        krav, klass = _krav(k, t)
        beskrivning = KOLUMNER.get(tabell, {}).get(namn, "")
        rader.append(f"<tr><td class='kol'>{namn}</td><td>{_typ(k)}</td><td class='{klass}'>{krav}</td>"
                     f"<td>{' · '.join(nyckel)}</td><td>{html.escape(beskrivning)}</td></tr>")

    noter = []
    for fk in t["fk"]:
        regel = VID_BORTTAGNING.get(fk["vid_borttagning"], "")
        if regel:
            noter.append(f"{','.join(fk['kolumner'])} → {fk['mal']}: när raden i {fk['mal']} tas bort {regel} "
                         f"{'raden' if fk['vid_borttagning'] == 'c' else 'kolumnen' if fk['vid_borttagning'] == 'n' else 'borttagningen'}")
    for v in t["villkor"]:
        noter.append("Villkor: <code>" + html.escape(v.removeprefix("CHECK ")) + "</code>")
    for tt, k, m, mk, f in LOGISKA:
        if tt == tabell:
            noter.append(f"{k} → {m}.{mk}: {html.escape(f)} (ingen främmande nyckel i databasen)")

    rubrik = f"{tabell} <span class='slag'>{'vy' if t['vy'] else _tal(t['antal']) + ' rader'}</span>"
    return f"""<section class="kort">
<h3>{rubrik}</h3>
<p class="tabellbeskrivning">{html.escape(TABELLER.get(tabell, ''))}</p>
<table><thead><tr><th>Kolumn</th><th>Typ</th><th>Värde</th><th>Nyckel</th><th>Innehåll</th></tr></thead>
<tbody>{''.join(rader)}</tbody></table>
{('<ul class="noter">' + ''.join(f'<li>{n}</li>' for n in noter) + '</ul>') if noter else ''}
</section>"""


# -----------------------------------------------------------------------------
# Sidan
# -----------------------------------------------------------------------------

CSS = """
@page { size: A4 landscape; margin: 11mm 12mm 12mm; }
:root { --pergament: #F7F2E6; --yta: #FFFDFC; --black: #1E2C30; --dampad: #536166; --sten: #D9D1C4;
        --run: #93483E; --blå: #244A63; --grön: #426C62; --guld: #8B641E; }
* { box-sizing: border-box; }
body { margin: 0; font: 9pt/1.35 "Source Sans 3", "Helvetica Neue", Arial, sans-serif; color: var(--black); background: #fff; }
h1, h2 { font-family: "EB Garamond", Georgia, serif; color: var(--blå); font-weight: 600; margin: 0; }
h1 { font-size: 22pt; }
h2 { font-size: 14pt; margin: 0 0 2mm; border-bottom: 1px solid var(--sten); padding-bottom: 1mm; }
h3 { font-size: 10.5pt; margin: 0 0 1mm; font-family: "SFMono-Regular", Menlo, Consolas, monospace; color: var(--blå); }
.slag { font-family: "Source Sans 3", Arial, sans-serif; font-weight: 400; color: var(--dampad); font-size: 8.5pt; margin-left: 2mm; }
.sida { page-break-after: always; break-after: page; }
.sida:last-child { page-break-after: auto; break-after: auto; }
.huvud { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2mm; }
.huvud p { margin: 0; color: var(--dampad); }
.ingress { margin: 0 0 2mm; max-width: 240mm; }
.diagram { width: 100%; height: 148mm; display: block; }
.diagram .namn { font: 600 12.5px "SFMono-Regular", Menlo, Consolas, monospace; fill: #1E2C30; }
.diagram .antal { font: 10.5px "Source Sans 3", Arial, sans-serif; fill: #536166; }
.diagram line.fk, .diagram path.fk { stroke: #536166; stroke-width: 1.1; fill: none; }
.diagram line.logisk { stroke: #8B641E; stroke-width: 1.1; stroke-dasharray: 4 3; }
.teckenforklaring { display: flex; flex-wrap: wrap; gap: 1mm 6mm; font-size: 8pt; color: var(--dampad); margin-top: 1mm; }
.teckenforklaring span::before { content: ""; display: inline-block; width: 3mm; height: 3mm; margin-right: 1.2mm; vertical-align: -0.4mm; background: var(--f); }
.grupp { margin: 0 0 2mm; }
.grupp > p { margin: 0 0 2mm; color: var(--dampad); }
.kortlista { columns: 2; column-gap: 7mm; }
.kort { break-inside: avoid; page-break-inside: avoid; margin: 0 0 4mm; display: block; }
.tabellbeskrivning { margin: 0 0 1.2mm; }
table { width: 100%; border-collapse: collapse; font-size: 7.6pt; }
th { text-align: left; font-weight: 600; color: var(--dampad); border-bottom: 1px solid var(--black); padding: .6mm 1mm; }
td { border-bottom: 1px solid var(--sten); padding: .5mm 1mm; vertical-align: top; }
td.kol { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 7.3pt; white-space: nowrap; }
td.oblig { font-weight: 600; }
td.friv { color: var(--dampad); }
td.berakn { color: var(--grön); font-style: italic; }
.pk, .fk, .unik, .logisk { display: inline-block; font-size: 6.5pt; font-weight: 700; padding: 0 1mm; border-radius: 1mm; color: #fff; }
.pk { background: var(--blå); } .fk { background: var(--dampad); } .unik { background: var(--grön); } .logisk { background: var(--guld); }
.noter { margin: 1mm 0 0; padding-left: 4mm; font-size: 7.4pt; color: var(--dampad); }
code { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 7pt; }
.forklaring { columns: 2; column-gap: 8mm; font-size: 8.5pt; }
.forklaring div { break-inside: avoid; page-break-inside: avoid; margin: 0 0 1.5mm; }
.forklaring dt { font-weight: 600; } .forklaring dd { margin: 0; }
@media screen { body { background: #e9e4d8; } .sida { background: #fff; width: 297mm; min-height: 210mm; margin: 6mm auto; padding: 11mm 12mm; box-shadow: 0 1px 4px rgba(0,0,0,.2); } }
"""


def sida(schema: dict) -> str:
    idag = date.today().isoformat()
    teckenforklaring = "".join(f'<span style="--f:{f}">{g}</span>' for g, f in FARGER.items())
    sidor = [f"""<section class="sida">
<div class="huvud"><h1>Fornmeds databas</h1><p>Schemat <code>fornmed</code> i PostgreSQL · läst ur databasen {idag}</p></div>
<p class="ingress">{len([t for t in schema.values() if not t['vy']])} tabeller och {len([t for t in schema.values() if t['vy']])} vyer. Pilarna går från tabellen som har den främmande nyckeln till tabellen den pekar på; en rad i den första hör till en rad i den andra. Streckade pilar är kopplingar som koden följer men som inte är främmande nycklar i databasen.</p>
{diagram(schema)}
<div class="teckenforklaring">{teckenforklaring}<span style="--f:#536166">heldragen pil: främmande nyckel</span><span style="--f:#8B641E">streckad pil: koppling utan nyckel</span></div>
</section>""",
             """<section class="sida">
<h2>Så läses tabellerna</h2>
<dl class="forklaring">
<div><dt>Värde: obligatorisk</dt><dd>Kolumnen har alltid ett värde (NOT NULL). Med standardvärde fylls det i om inget anges.</dd></div>
<div><dt>Värde: frivillig</dt><dd>Kolumnen kan sakna värde (NULL).</dd></div>
<div><dt>Värde: beräknas</dt><dd>Värdet räknas fram av databasen, som fulltextindexen, eller av en vy, och skrivs aldrig direkt.</dd></div>
<div><dt><span class="pk">PK</span> primärnyckel</dt><dd>Radens unika identifierare. Är nyckeln sammansatt av flera kolumner är det kombinationen som är unik.</dd></div>
<div><dt><span class="unik">UNIK</span> unik</dt><dd>Värdet, eller kombinationen av värden, förekommer bara en gång.</dd></div>
<div><dt><span class="fk">FK</span> främmande nyckel</dt><dd>Värdet måste finnas som nyckel i den tabell pilen pekar på. Noterna under tabellen anger vad som händer när den raden tas bort.</dd></div>
<div><dt><span class="logisk">koppling</span></dt><dd>Värdet motsvarar en nyckel i en annan tabell enligt projektets konventioner, utan att databasen kontrollerar det.</dd></div>
<div><dt>Kontrollerade värden</dt><dd>Kolumner som genre, typ, predikat, aspekt och varde tar sina koder ur tabellen vokabular, med schemat angivet i beskrivningen. Databasen kontrollerar inte kopplingen; vokabular.py och inläsningsskripten gör det.</dd></div>
<div><dt>Datering</dt><dd>Lagras som EDTF-text för visning och som två heltal ÅÅÅÅMMDD för sökning. Datumen är julianska som i källorna och omräknas inte, därför används inte datumtypen.</dd></div>
<div><dt>Id:n</dt><dd>Text med prefix efter slag, t.ex. verk:, utgava:, person:, begrepp:. Entiteternas id:n byts aldrig, så att länkar mellan källor och versioner av databasen håller.</dd></div>
<div><dt>Språk</dt><dd>ISO 639-3: swe svenska, fsv fornsvenska, non fornvästnordiska, lat latin, dan danska, eng engelska m.fl.</dd></div>
<div><dt>Antal rader</dt><dd>Avser databasen vid läsningen; för stora tabeller är det Postgres uppskattning.</dd></div>
</dl>
</section>"""]

    for gruppnamn, beskrivning, tabeller in GRUPPER:
        kort = "".join(tabellkort(t, schema[t]) for t in tabeller if t in schema)
        sidor.append(f"""<section class="sida grupp">
<h2>{gruppnamn}</h2>
<p>{html.escape(beskrivning)}</p>
<div class="kortlista">{kort}</div>
</section>""")

    return f"""<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<title>Fornmeds databas – schema</title>
<style>{CSS}</style>
</head>
<body>
{''.join(sidor)}
</body>
</html>
"""


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("fil", help="HTML-filen som skrivs")
    argument = tolk.parse_args()
    if not db._ar_postgres():
        tolk.error("schemat läses ur Postgres; DATABASE_URL pekar mot en annan databas")
    with open(argument.fil, "w", encoding="utf-8") as f:
        f.write(sida(las_schema()))
    print(f"Skrev {argument.fil}")


if __name__ == "__main__":
    main()

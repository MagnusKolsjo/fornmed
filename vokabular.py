"""
Kontrollerade vokabulär för klassificeringsaxlarna.

Varje post är (schema, kod, etikett, beskrivning). `schema` anger axeln.
För bedömningar gäller att `bedomning.aspekt` namnger det schema som
`bedomning.varde` hämtas ur (t.ex. aspekt 'historicitet' → schema
'historicitet'). Listan läses in idempotent vid varje uppstart, så nya
värden läggs till här och syns efter omstart.
"""

VOKABULAR: list[tuple[str, str, str, str | None]] = [
    # Källgenre — avgör hur ett påstående i källan ska läsas
    ("genre", "diplom", "Diplom/brev", "Rättsligt eller administrativt dokument, oftast samtida med det det reglerar"),
    ("genre", "lag", "Lag", "Landskaps-, lands- eller stadslag"),
    ("genre", "stadga", "Stadga/förordning", "Kunglig eller kyrklig förordning"),
    ("genre", "rakenskap", "Räkenskap/jordebok", "Ekonomisk förteckning"),
    ("genre", "kronika", "Krönika", "Berättande historieskrivning"),
    ("genre", "annal", "Annal", "Årsvis anteckning av händelser"),
    ("genre", "legend", "Helgonlegend/mirakel", "Hagiografi med uppbyggligt syfte"),
    ("genre", "saga", "Saga", "Isländsk eller norsk prosaberättelse"),
    ("genre", "skaldedikt", "Skaldedikt", "Fornnordisk hovdiktning, ofta äldre än prosan som citerar den"),
    ("genre", "eddadikt", "Eddadikt", "Mytologisk eller heroisk eddisk diktning"),
    ("genre", "hjaltedikt", "Hjältedikt/epos", "T.ex. Beowulf"),
    ("genre", "runinskrift", "Runinskrift", "Samtida epigrafisk källa"),
    ("genre", "geografi", "Geografisk/etnografisk beskrivning", "T.ex. Adam av Bremen, Ottars berättelse"),
    ("genre", "arkeologi", "Arkeologiskt material", "Fynd, anläggningar och dateringar"),
    ("genre", "undersamling", "Undersamling", "Katalog över monster och under, t.ex. Liber monstrorum"),
    ("genre", "furstespegel", "Furstespegel", "Lärd framställning om hur en furste ska styra, t.ex. Konungastyrelsen"),

    # Vittnestyp — fysisk eller registrerad överlevnad av ett verk
    ("vittnestyp", "original", "Original", None),
    ("vittnestyp", "medeltida_avskrift", "Medeltida avskrift", None),
    ("vittnestyp", "eftermedeltida_avskrift", "Eftermedeltida avskrift", None),
    ("vittnestyp", "medeltida_registratur", "Medeltida registratur/regest", None),
    ("vittnestyp", "eftermedeltida_registratur", "Eftermedeltida registratur/regest", None),
    ("vittnestyp", "fotokopia", "Fotokopia", None),
    ("vittnestyp", "tryck", "Tryck", None),
    ("vittnestyp", "tryckt_regest", "Tryckt regest", None),
    ("vittnestyp", "faksimil", "Faksimil", None),
    ("vittnestyp", "oversattning", "Översättning", None),
    ("vittnestyp", "handskrift", "Handskrift", "Kodex eller fragment med litterär text"),

    # Passagetyp — styr indexering och sökning
    ("passagetyp", "originaltext", "Originaltext", "Källans text i utgåva eller transkription"),
    ("passagetyp", "regest", "Regest", "Modern sammanfattning av innehållet"),
    ("passagetyp", "oversattning", "Översättning", None),
    ("passagetyp", "normaliserad", "Normaliserad text", "Normaliserad stavning av originaltexten"),
    ("passagetyp", "skolion", "Skolion", "Tillägg i handskrifternas marginal; kan ha annan upphovsman och datering än huvudtexten"),

    # Utgåvetyp — hur utgåvans text förhåller sig till källan
    ("utgavetyp", "original", "Originalspråk", "Källans text i utgåva eller transkription"),
    ("utgavetyp", "oversattning", "Översättning", "Tryckt eller publicerad översättning av en namngiven översättare"),
    ("utgavetyp", "maskinoversattning", "Maskinöversättning", "Översättning gjord av språkmodell; ogranskad och inte citerbar som översättning"),
    ("utgavetyp", "maskintranskription", "Maskintranskription", "Originaltext som språkmodell läst av från sidbilder; ogranskad"),

    # Utgåveroll — vad i verket utgåvan återger
    ("utgaveroll", "huvudtext", "Huvudtext", None),
    ("utgaveroll", "skolier", "Skolier", "Marginaltillägg i handskrifterna, utgivna för sig"),

    # Deltyp — den indelning av ett verk som passagens del avser
    ("deltyp", "bok", "Bok", "Bok i en krönika eller ett lärt verk (liber)"),
    ("deltyp", "del", "Del", "Del av en annalserie"),
    ("deltyp", "balk", "Balk", "Balk i en landskaps-, lands- eller stadslag"),
    ("deltyp", "saga", "Saga", "Saga eller tåt i en kungasagesamling"),
    ("deltyp", "avsnitt", "Avsnitt", "Namngivet avsnitt, t.ex. Gylfaginning i Snorres Edda"),
    ("deltyp", "volym", "Volym", "Band i en utgåva i flera volymer"),

    # Platsroll — hur en geografisk plats hör till ett verk
    ("platsroll", "utfardandeort", "Utfärdandeort", "Där ett brev utfärdades"),
    ("platsroll", "fyndplats", "Fyndplats", "Där en runinskrift har hittats eller står"),
    ("platsroll", "socken", "Socken", "Socken eller stad där en runinskrift finns"),
    ("platsroll", "harad", "Härad", "Härad eller motsvarande indelning, t.ex. norskt fylke"),
    ("platsroll", "kommun", "Kommun", "Nutida kommun"),
    ("platsroll", "omrade", "Område", "Landskap eller land"),
    ("platsroll", "forvaring", "Förvaring", "Där en runinskrift finns i dag, om den uppgiften skiljer sig från fyndplatsen"),

    # Sökplatsroll — platsens roll för ett objekt i sökindexet
    ("sokplatsroll", "handelse", "Händelse", "Där det som ett påstående beskriver ägde rum"),
    ("sokplatsroll", "tillkomst", "Tillkomst", "Där källan skrevs: brevets utfärdandeort, runinskriftens fyndplats"),
    ("sokplatsroll", "forvaring", "Förvaring", "Där källan förvaras i dag"),
    ("sokplatsroll", "lage", "Läge", "Platsentitetens eget läge"),

    # Platsslag
    ("platsslag", "land", "Land", "Nutida land eller medeltida rike"),
    ("platsslag", "landskap", "Landskap", None),
    ("platsslag", "lan", "Län", "Nutida län"),
    ("platsslag", "kommun", "Kommun", "Nutida kommun"),
    ("platsslag", "harad", "Härad", "Härad eller motsvarande indelning"),
    ("platsslag", "socken", "Socken", None),
    ("platsslag", "stad", "Stad", None),
    ("platsslag", "by", "By", None),
    ("platsslag", "gard", "Gård", None),
    ("platsslag", "slott", "Slott eller borg", None),
    ("platsslag", "kloster", "Kloster", None),
    ("platsslag", "kyrka", "Kyrka", None),
    ("platsslag", "museum", "Museum", None),
    ("platsslag", "omrade", "Område", "Geografiskt område utan fast indelning"),
    ("platsslag", "annat", "Annat", None),
    ("platsslag", "ej_plats", "Inte en plats", "Text som tolkats som plats men anger något annat, t.ex. 'på kung Eriks vägnar'"),

    # Entitetstyp
    ("entitetstyp", "person", "Person", None),
    ("entitetstyp", "grupp", "Grupp/släkt/folk", None),
    ("entitetstyp", "plats", "Plats", None),
    ("entitetstyp", "institution", "Institution", "Kloster, stift, kapitel, stad, rike"),
    ("entitetstyp", "indelning", "Administrativ indelning", "Land, härad, hundare, socken, län"),
    ("entitetstyp", "ambete", "Ämbete/roll", "Lagman, drots, marsk, biskop, fogde"),
    ("entitetstyp", "handelse", "Händelse", None),
    ("entitetstyp", "begrepp", "Begrepp", "Samhällsbegrepp, t.ex. ledung, tionde, frälse"),
    ("entitetstyp", "vasen", "Gud/väsen", "Gudar och mytologiska väsen, t.ex. Oden, Frö, diser"),

    # Predikat — vad ett påstående säger om sitt subjekt
    ("predikat", "innehar_ambete", "innehar ämbete", None),
    ("predikat", "utfardar", "utfärdar", None),
    ("predikat", "overlater", "överlåter egendom till", None),
    ("predikat", "ager", "äger", None),
    ("predikat", "forlaner", "förlänar", None),
    ("predikat", "beslutar", "beslutar", None),
    ("predikat", "deltar_i", "deltar i", None),
    ("predikat", "styr_over", "styr över", None),
    ("predikat", "ar_del_av", "är del av", "Indelning eller institution inom en större"),
    ("predikat", "ar_belagen_i", "är belägen i", None),
    ("predikat", "foralder_till", "förälder till", None),
    ("predikat", "gift_med", "gift med", None),
    ("predikat", "dor", "dör", None),
    ("predikat", "dodar", "dödar", None),
    ("predikat", "besegrar", "besegrar", None),
    ("predikat", "fodd", "föds", None),
    ("predikat", "har_stand", "tillhör ståndet", "Riddare eller väpnare"),
    ("predikat", "eftertrader", "efterträder", "I ett ämbete; i en längd följer det längdens ordning"),
    ("predikat", "syskon_till", "syskon till", None),
    ("predikat", "begravd_i", "begravd i", "Objektet är gravplatsen"),
    # Gärningar. Predikaten är aktiva, med den som handlar som subjekt; när
    # källan inte namnger den som handlar används ett tillståndspredikat för
    # den drabbade (som 'dor'). Ett påstående kan ha både objekt och fritt
    # värde: 'utnamner' har den utnämnde som objekt och ämbetet som värde.
    # Kyrka och kristnande
    ("predikat", "grundar", "grundar", "Kloster, stift, kapitel, skola, hospital, gille, stad eller borg"),
    ("predikat", "later_bygga", "låter bygga", "Kyrka, bro, väg, borg; objektet är byggnaden eller platsen"),
    ("predikat", "viger", "viger", "Kyrka, kyrkogård eller person (biskop, präst)"),
    ("predikat", "dops_av", "döps av", "Subjektet är den döpte, objektet den som döper"),
    # Hedniska riter
    ("predikat", "offrar", "offrar till", "Objektet är guden eller väsendet, värdet offret, platsen kultplatsen"),
    ("predikat", "forrattar_rit", "förrättar rit", "Värdet är riten (blot, gravöl, sejd, edgång); återkommande riter är händelser"),
    # Lag och förvaltning
    ("predikat", "stiftar_lag", "stiftar lag", "Gör, ändrar eller förkunnar lag"),
    ("predikat", "faststaller_grans", "fastställer gräns", "Gräns mellan riken eller länder; objektet är det andra riket"),
    ("predikat", "indelar", "delar in", "Delar ett rike eller land i områden; resultatet beskrivs med 'ar_del_av'"),
    ("predikat", "infor_palaga", "inför pålaga", "Skatt, tionde eller avgift; värdet anger pålagan"),
    ("predikat", "utnamner", "utnämner", "Objektet är den utnämnde, värdet ämbetet eller titeln, platsen ansvarsområdet"),
    ("predikat", "mister_ambete", "mister ämbete", "Avsätts eller förlorar ämbete eller titel"),
    # Rättskipning
    ("predikat", "domer", "dömer", "Objektet är den dömda parten, värdet utfallet"),
    ("predikat", "avrattar", "avrättar", None),
    ("predikat", "fangslar", "fängslar", None),
    ("predikat", "landsforvisar", "landsförvisar", None),
    ("predikat", "benadar", "benådar", "Nåd, lejd eller upphävt straff"),
    # Makt och konflikt
    ("predikat", "erovrar", "erövrar", "Riket, ett land, en borg eller en stad"),
    ("predikat", "forlorar", "förlorar", "Riket, ett land, en borg eller ett slag; slag är händelser"),
    ("predikat", "flyr_till", "flyr till", None),
    # Gåvor och ursprung
    ("predikat", "skanker", "skänker", "Objektet är mottagaren, värdet gåvan"),
    # Överlåtelser: objektet är motparten, värdet egendomen och priset, platsen orten
    ("predikat", "saljer", "säljer", "Objektet är köparen, värdet egendom och pris"),
    ("predikat", "pantsatter", "pantsätter", "Objektet är panthavaren, värdet egendom och lånesumma"),
    ("predikat", "byter", "byter med", "Objektet är motparten, värdet det som byts"),
    ("predikat", "testamenterar", "testamenterar", "Objektet är mottagaren, värdet egendomen"),
    ("predikat", "upplater", "upplåter", "Arrende, landbo- eller nyttjanderätt; objektet är den som får nyttja"),
    ("predikat", "stadfaster", "stadfäster", "Bekräftar en annans överlåtelse, dom eller privilegium; värdet anger vad"),
    ("predikat", "harkomst", "härstammar från", "Ort, land eller folk"),
    # Normer i lagtexter: subjektet är ett begrepp (ett brott, en påföljd,
    # ett ämbete), och passagen anger vilken lag som säger det
    ("predikat", "paforljd", "har påföljden", "Subjektet är brottet, objektet påföljden, värdet belopp eller villkor"),
    ("predikat", "tillfaller", "tillfaller", "Subjektet är boten eller egendomen, objektet mottagaren, värdet andelen"),
    ("predikat", "handlaggs_vid", "handläggs vid", "Subjektet är målet eller brottet, objektet tinget eller domaren"),
    ("predikat", "utses_av", "utses av", "Subjektet är ämbetet eller uppdraget, objektet den som utser"),
    ("predikat", "kraver", "kräver", "Subjektet är målet eller avgörandet, objektet bevismedlet eller förfarandet"),
    ("predikat", "diskvalificerar", "diskvalificerar", "Jäv: subjektet är grunden (frändskap, muta), objektet rollen (nämndeman, vittne, domare)"),
    ("predikat", "definieras_som", "definieras som", "Lagens egen definition av begreppet; värdet sammanfattar den"),
    ("predikat", "omnamns", "omnämns", "Endast belagd förekomst"),

    # Bedömningsaspekter
    ("bedomningsaspekt", "historicitet", "Historicitet", "Gäller påståenden"),
    ("bedomningsaspekt", "akthet", "Äkthet", "Gäller verk och vittnen"),
    ("bedomningsaspekt", "korroboration", "Korroboration", "Gäller påståenden"),
    ("bedomningsaspekt", "datering", "Datering", "Värdet är ett EDTF-uttryck, inte vokabulär"),
    ("bedomningsaspekt", "identifiering", "Identifiering", "Gäller identifieringar mellan entiteter"),
    ("bedomningsaspekt", "titulatur", "Titulatur", "Gäller påståenden om titel: om titeln stämmer med dateringen"),

    # Identifiering — hur säkert två entiteter är desamma
    ("identifiering", "saker", "Säker", None),
    ("identifiering", "sannolik", "Sannolik", None),
    ("identifiering", "mojlig", "Möjlig", None),
    ("identifiering", "osannolik", "Osannolik", None),
    ("identifiering", "avvisad", "Avvisad", None),

    # Titulatur — hur brevets datering förhåller sig till titelinnehavet och
    # livet hos den som brevet ger titeln. Koderna används också som
    # kommentar på identifieringar mellan en utfärdare och dess kandidater.
    ("titulatur", "under_titeln", "Under titeln", "Bar titeln vid dateringen"),
    ("titulatur", "fore_titeln", "Före titeln", "Levde men hade ännu inte titeln, t.ex. utvald tronföljare"),
    ("titulatur", "efter_titeln", "Efter titeln", "Levde men hade förlorat eller lämnat titeln, t.ex. avsatt kung"),
    ("titulatur", "efter_dodsfall", "Efter dödsfallet", "Omnämns med titeln efter sin död"),
    ("titulatur", "fore_fodelse", "Före födelsen", "Dateringen eller identifieringen är fel"),

    # Historicitet — ordnad från starkast till svagast belagd
    ("historicitet", "belagd", "Belagd", "Stöds av samtida, oberoende källa"),
    ("historicitet", "sannolik", "Sannolik", None),
    ("historicitet", "mojlig", "Möjlig", None),
    ("historicitet", "osannolik", "Osannolik", None),
    ("historicitet", "legendarisk", "Legendarisk", "Traditionsstoff med möjlig historisk kärna"),
    ("historicitet", "mytisk", "Mytisk", "Mytologiskt stoff utan historisk referent"),
    ("historicitet", "litterar_konstruktion", "Litterär konstruktion", "Skapad av författaren"),
    ("historicitet", "anakronism", "Anakronism", "Senare förhållanden projicerade bakåt"),

    # Äkthet
    ("akthet", "akta", "Äkta", None),
    ("akthet", "misstankt", "Misstänkt förfalskning", None),
    ("akthet", "forfalskning", "Förfalskning", None),
    ("akthet", "interpolerad", "Interpolerad", "Äkta kärna med senare tillägg"),

    # Korroboration
    ("korroboration", "oberoende_samtida", "Oberoende samtida källa", None),
    ("korroboration", "oberoende_senare", "Oberoende senare källa", None),
    ("korroboration", "arkeologisk", "Arkeologiskt stöd", None),
    ("korroboration", "beroende_tradition", "Endast beroende tradition", "Senare källor bygger på samma tradition"),
    ("korroboration", "saknas", "Ingen korroboration", None),

    # Säkerhet i en bedömning
    ("sakerhet", "hog", "Hög", None),
    ("sakerhet", "medel", "Medel", None),
    ("sakerhet", "lag", "Låg", None),

    # Relationer mellan påståenden
    ("pastaenderelation", "stoder", "stöder", None),
    ("pastaenderelation", "motsager", "motsäger", None),
    ("pastaenderelation", "beroende_av", "är beroende av", "Återger samma tradition; räknas inte som korroboration"),
    ("pastaenderelation", "samma_som", "är samma som", None),

    # Termtyp i begreppsregistret
    ("termtyp", "huvudterm", "Huvudterm", "Begreppets namn på modern svenska"),
    ("termtyp", "synonym", "Synonym", "Annan modern benämning"),
    ("termtyp", "historisk_form", "Historisk form", "Uppslagsform eller variant i en medeltida ordbok"),
    ("termtyp", "oversattning", "Motsvarighet", "Term på latin, fornvästnordiska eller annat språk"),

    # Relationer mellan begrepp (SKOS)
    ("begreppsrelation", "bredare", "har bredare begrepp", "till är ett bredare begrepp än fran"),
    ("begreppsrelation", "relaterad", "är relaterat till", None),

    # Hur ett påstående kom in i databasen
    ("extraktion", "manuell", "Manuellt registrerad", None),
    ("extraktion", "modell", "Extraherad av språkmodell", None),
    ("extraktion", "regel", "Extraherad med regel/mönster", None),
]

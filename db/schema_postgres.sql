-- =============================================================================
-- Schema för källor, påståenden och forskningens bedömningar (PostgreSQL)
-- Idempotent: körs vid varje uppstart via db.initiera_schema().
--
-- Filen har tre delar:
-- 1. Bas-schemat, låst vid första publiceringen (v1.0). Ändra det aldrig:
--    nya kolumner, tabeller och index läggs till som migrationer.
-- 2. Migrationerna, i den ordning de tillkommit. Varje migration måste gå att
--    köra många gånger (ADD COLUMN IF NOT EXISTS, CREATE INDEX IF NOT EXISTS,
--    UPDATE … WHERE kolumn IS NULL).
-- 3. Vyerna, som skapas om vid varje uppstart och därför alltid följer
--    tabellerna.
-- =============================================================================

-- =============================================================================
-- 1. Bas-schema (v1.0, låst vid första publiceringen 2026-11-02)
-- Ändra ALDRIG dessa block. Nya kolumner och index läggs som migrationer.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS fornmed;

-- -----------------------------------------------------------------------------
-- Kontrollerade vokabulär
-- -----------------------------------------------------------------------------
-- Ett gemensamt register för alla klassificeringsaxlar så att nya värden kan
-- läggas till utan schemaändring. `schema` anger vilken axel värdet hör till.

CREATE TABLE IF NOT EXISTS fornmed.vokabular (
    schema       TEXT NOT NULL,
    kod          TEXT NOT NULL,
    etikett      TEXT NOT NULL,
    beskrivning  TEXT,
    ordning      INTEGER,
    PRIMARY KEY (schema, kod)
);

-- -----------------------------------------------------------------------------
-- Källsamlingar (dataset som materialet importerats ur)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fornmed.kallsamling (
    id           TEXT PRIMARY KEY,
    namn         TEXT NOT NULL,
    utgivare     TEXT,
    url          TEXT,
    licens       TEXT,
    version      TEXT,
    importerad   TIMESTAMPTZ
);

-- -----------------------------------------------------------------------------
-- Källor i fyra nivåer: verk → vittne → utgåva → passage
-- -----------------------------------------------------------------------------
-- Datering lagras som EDTF-text plus heltalsintervall ÅÅÅÅMMDD. Heltal i
-- stället för DATE eftersom källornas datum är julianska och ofta ogiltiga
-- som gregorianska (t.ex. 1300-02-29), och okänd månad/dag måste kunna
-- uttryckas som ett intervall.

CREATE TABLE IF NOT EXISTS fornmed.verk (
    id               TEXT PRIMARY KEY,
    kallsamling_id   TEXT REFERENCES fornmed.kallsamling (id),
    titel            TEXT NOT NULL,
    upphov           TEXT,
    genre            TEXT,            -- vokabular 'genre'
    sprak            TEXT[],          -- ISO 639-3, t.ex. {swe,lat}
    utfardandeort    TEXT,
    datering_edtf    TEXT,
    datering_fran    INTEGER,
    datering_till    INTEGER,
    datering_anm     TEXT,
    beskrivning      TEXT,
    extern_url       TEXT,
    extra            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS verk_datering_idx ON fornmed.verk (datering_fran, datering_till);
CREATE INDEX IF NOT EXISTS verk_genre_idx ON fornmed.verk (genre);

-- Ett vittne är en fysisk eller registrerad överlevnad av verket: original,
-- avskrift, registratur, tryck. Dess datering är skild från verkets.
CREATE TABLE IF NOT EXISTS fornmed.vittne (
    id               TEXT PRIMARY KEY,
    verk_id          TEXT NOT NULL REFERENCES fornmed.verk (id) ON DELETE CASCADE,
    typ              TEXT NOT NULL,   -- vokabular 'vittnestyp'
    beskrivning      TEXT NOT NULL,
    signum           TEXT,
    datering_edtf    TEXT,
    datering_fran    INTEGER,
    datering_till    INTEGER,
    iiif_manifest    TEXT
);

CREATE INDEX IF NOT EXISTS vittne_verk_idx ON fornmed.vittne (verk_id);

-- En utgåva är också en språkversion av verket. Språket finns dessutom på
-- varje passage, eftersom en utgåva kan ha flera språk (runinskrifternas
-- translitterering, normalisering och översättning); `sprak` här är då NULL.
-- sprak, typ, roll, oversattare och ar fylls i av struktur.py.
CREATE TABLE IF NOT EXISTS fornmed.utgava (
    id               TEXT PRIMARY KEY,
    verk_id          TEXT REFERENCES fornmed.verk (id) ON DELETE CASCADE,
    referens         TEXT NOT NULL,
    licens           TEXT,
    sprak            TEXT,
    typ              TEXT,            -- vokabular 'utgavetyp'
    roll             TEXT,            -- vokabular 'utgaveroll'
    oversattare      TEXT,
    ar               INTEGER
);

-- En passage är den citerbara textenheten. `typ` skiljer originaltext från
-- moderna regester och översättningar, eftersom de söks på olika sätt.
CREATE TABLE IF NOT EXISTS fornmed.passage (
    id               TEXT PRIMARY KEY,
    verk_id          TEXT NOT NULL REFERENCES fornmed.verk (id) ON DELETE CASCADE,
    utgava_id        TEXT REFERENCES fornmed.utgava (id) ON DELETE SET NULL,
    typ              TEXT NOT NULL,   -- vokabular 'passagetyp'
    adress           TEXT,
    ordning          INTEGER NOT NULL DEFAULT 0,
    sprak            TEXT,
    text             TEXT NOT NULL,
    -- Länk till underlaget för just den här passagen: sidbild eller sida i
    -- den digitala utgåvan (verkets extern_url gäller hela verket)
    url              TEXT,
    -- Den del av verket som passagen hör till (bok, balk, saga), så att stora
    -- verk kan hämtas del för del; NULL för verk utan indelning. Fylls i av
    -- struktur.py.
    del              TEXT,
    del_typ          TEXT,            -- vokabular 'deltyp'
    -- Modern svenska indexeras både med svensk stemming (för vanliga
    -- sökord i valfri böjning) och utan (för begreppsregistrets termer,
    -- som stemmingen slår ihop med vardagsord: fastar → fast). Fornsvenska
    -- och latin förstörs av stemmingen och indexeras bara utan.
    sokvektor        TSVECTOR GENERATED ALWAYS AS (
        CASE WHEN typ IN ('regest', 'oversattning') AND sprak = 'swe'
             THEN to_tsvector('swedish', text) || to_tsvector('simple', text)
             ELSE to_tsvector('simple', text)
        END
    ) STORED
);


CREATE INDEX IF NOT EXISTS passage_verk_idx ON fornmed.passage (verk_id);
CREATE INDEX IF NOT EXISTS passage_utgava_ordning_idx ON fornmed.passage (utgava_id, ordning);
CREATE INDEX IF NOT EXISTS utgava_verk_idx ON fornmed.utgava (verk_id);
CREATE INDEX IF NOT EXISTS passage_sokvektor_idx ON fornmed.passage USING GIN (sokvektor);

-- -----------------------------------------------------------------------------
-- Chunks och embeddings för semantisk sökning
-- -----------------------------------------------------------------------------
-- Bara passager på modern svenska (regester, översättningar) embeddas;
-- embedding-modellerna hanterar inte fornsvenska, fornnordiska eller
-- medeltidslatin. Fulltextsökningen sker på passage, vektorsökningen på
-- chunk, och träffarna slås ihop per passage.

CREATE TABLE IF NOT EXISTS fornmed.chunk (
    id               BIGSERIAL PRIMARY KEY,
    passage_id       TEXT NOT NULL REFERENCES fornmed.passage (id) ON DELETE CASCADE,
    chunk_nr         INTEGER NOT NULL,
    text             TEXT NOT NULL,
    UNIQUE (passage_id, chunk_nr)
);

-- `modell` anger vilken embedding-modell som gav vektorn, så att ett byte
-- av EMBEDDING_MODELL upptäcks och vektorerna räknas om
CREATE TABLE IF NOT EXISTS fornmed.embedding (
    chunk_id         BIGINT PRIMARY KEY REFERENCES fornmed.chunk (id) ON DELETE CASCADE,
    modell           TEXT NOT NULL,
    vektor           vector(768) NOT NULL
);

-- HNSW i stället för ivfflat: ivfflat beräknar sina kluster när indexet
-- skapas, och här skapas det på en tom tabell vid första uppstart. Ett
-- partiellt index per embeddingmodell skapas av db.skapa_vektorindex, eftersom
-- modellnamnen kommer från konfigurationen; det gemensamma indexet behövs inte.
DROP INDEX IF EXISTS fornmed.embedding_vektor_idx;
CREATE INDEX IF NOT EXISTS embedding_modell_idx ON fornmed.embedding (modell);

-- -----------------------------------------------------------------------------
-- Entiteter: personer, platser, institutioner, ämbeten, händelser, begrepp
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fornmed.entitet (
    id               TEXT PRIMARY KEY,
    typ              TEXT NOT NULL,   -- vokabular 'entitetstyp'
    namn             TEXT NOT NULL,
    beskrivning      TEXT,
    wikidata_id      TEXT,
    extra            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS entitet_typ_namn_idx ON fornmed.entitet (typ, namn);

CREATE TABLE IF NOT EXISTS fornmed.entitet_namnform (
    entitet_id       TEXT NOT NULL REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    namnform         TEXT NOT NULL,
    sprak            TEXT,
    passage_id       TEXT REFERENCES fornmed.passage (id) ON DELETE SET NULL,
    PRIMARY KEY (entitet_id, namnform)
);

CREATE INDEX IF NOT EXISTS entitet_namnform_idx ON fornmed.entitet_namnform (lower(namnform));

-- -----------------------------------------------------------------------------
-- Ordböcker: Söderwall, Söderwalls supplement och Schlyter
-- -----------------------------------------------------------------------------
-- En rad per betydelse (Sense) i ordbokens LMF-fil. `lemgram` är gemensamt
-- för ordböckerna och binder ihop samma ord, vilket behövs eftersom
-- Söderwall för lagspråkets ord bara hänvisar till Schlyter ("L.").
-- `sokform` är lemmat i den lösa normaliseringen i normalisering.ordform,
-- så att härad, häradh och hæraþ hittas med samma sökord.

CREATE TABLE IF NOT EXISTS fornmed.ordboksartikel (
    id               TEXT PRIMARY KEY,
    kallsamling_id   TEXT NOT NULL REFERENCES fornmed.kallsamling (id),
    lemma            TEXT NOT NULL,
    lemgram          TEXT,
    ordklass         TEXT,
    betydelse_nr     INTEGER NOT NULL,
    definition       TEXT NOT NULL,
    former           JSONB NOT NULL DEFAULT '[]'::jsonb,
    sokform          TEXT NOT NULL,
    sokvektor        TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', lemma || ' ' || definition)
    ) STORED
);

CREATE INDEX IF NOT EXISTS ordboksartikel_sokform_idx ON fornmed.ordboksartikel (sokform);
CREATE INDEX IF NOT EXISTS ordboksartikel_lemgram_idx ON fornmed.ordboksartikel (lemgram);
CREATE INDEX IF NOT EXISTS ordboksartikel_sokvektor_idx
    ON fornmed.ordboksartikel USING GIN (sokvektor);

-- -----------------------------------------------------------------------------
-- Begreppsregister: termformer och relationer för entiteter av typen begrepp
-- -----------------------------------------------------------------------------
-- Ett begrepp (ledung) har termer på flera språk och i flera historiska
-- former (leþunger, ledhunger, leiðangr, expeditio). Sökningen expanderar
-- en fråga med alla termer för de begrepp vars termer frågan innehåller.

CREATE TABLE IF NOT EXISTS fornmed.term (
    id               TEXT PRIMARY KEY,
    entitet_id       TEXT NOT NULL REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    term             TEXT NOT NULL,
    sprak            TEXT NOT NULL,   -- ISO 639-3; 'fsv' för fornsvenska
    termtyp          TEXT NOT NULL,   -- vokabular 'termtyp'
    sokform          TEXT NOT NULL,
    artikel_id       TEXT REFERENCES fornmed.ordboksartikel (id) ON DELETE SET NULL,
    registrerad_av   TEXT,
    granskad         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS term_sokform_idx ON fornmed.term (sokform);
CREATE INDEX IF NOT EXISTS term_entitet_idx ON fornmed.term (entitet_id);

-- Relationerna följer SKOS: (fran, till, 'bredare') betyder att till är
-- ett bredare begrepp än fran
CREATE TABLE IF NOT EXISTS fornmed.begreppsrelation (
    fran_id          TEXT NOT NULL REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    till_id          TEXT NOT NULL REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    relation         TEXT NOT NULL,   -- vokabular 'begreppsrelation'
    PRIMARY KEY (fran_id, till_id, relation),
    CHECK (fran_id <> till_id)
);

-- -----------------------------------------------------------------------------
-- Påståenden: vad en passage hävdar, inte vad som hände
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fornmed.pastaende (
    id               TEXT PRIMARY KEY,
    passage_id       TEXT NOT NULL REFERENCES fornmed.passage (id) ON DELETE CASCADE,
    subjekt_id       TEXT NOT NULL REFERENCES fornmed.entitet (id),
    predikat         TEXT NOT NULL,   -- vokabular 'predikat'
    objekt_id        TEXT REFERENCES fornmed.entitet (id),
    objekt_varde     TEXT,
    plats_id         TEXT REFERENCES fornmed.entitet (id),
    tid_edtf         TEXT,
    tid_fran         INTEGER,
    tid_till         INTEGER,
    citat            TEXT,
    -- Proveniens: maskinellt extraherade påståenden ska gå att skilja från
    -- manuellt registrerade och från granskade
    extraktion       TEXT NOT NULL DEFAULT 'manuell',  -- vokabular 'extraktion'
    extraherad_av    TEXT,
    granskad         BOOLEAN NOT NULL DEFAULT FALSE,
    granskad_av      TEXT,
    skapad           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (objekt_id IS NOT NULL OR objekt_varde IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS pastaende_subjekt_idx ON fornmed.pastaende (subjekt_id);
CREATE INDEX IF NOT EXISTS pastaende_objekt_idx ON fornmed.pastaende (objekt_id);
CREATE INDEX IF NOT EXISTS pastaende_passage_idx ON fornmed.pastaende (passage_id);
CREATE INDEX IF NOT EXISTS pastaende_tid_idx ON fornmed.pastaende (tid_fran, tid_till);

-- Relationer mellan påståenden. 'beroende_av' är lika viktig som 'stöder':
-- två källor som återger samma tradition korroborerar inte varandra.
CREATE TABLE IF NOT EXISTS fornmed.pastaende_relation (
    fran_id          TEXT NOT NULL REFERENCES fornmed.pastaende (id) ON DELETE CASCADE,
    till_id          TEXT NOT NULL REFERENCES fornmed.pastaende (id) ON DELETE CASCADE,
    relation         TEXT NOT NULL,   -- vokabular 'pastaenderelation'
    kommentar        TEXT,
    PRIMARY KEY (fran_id, till_id, relation),
    CHECK (fran_id <> till_id)
);

-- -----------------------------------------------------------------------------
-- Identifieringar: att två entiteter är samma
-- -----------------------------------------------------------------------------
-- Varje källas namnform får en egen entitet när identiteten är en
-- forskningsfråga (Beowulfs Hygelac, Gregorius Chlochilaicus). Att de är
-- samma person är då ett omdöme som kan bedömas och ifrågasättas, inte en
-- sammanslagning som döljer frågan.

CREATE TABLE IF NOT EXISTS fornmed.identifiering (
    id               TEXT PRIMARY KEY,
    entitet_id       TEXT NOT NULL REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    identifierad_med TEXT NOT NULL REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    -- Identifieringar med samma alternativgrupp utesluter varandra (gēatas är
    -- götar eller jutar); utan grupp kan de gälla samtidigt (Hygelac är både
    -- Chlochilaicus och Huiglaucus)
    alternativgrupp  TEXT,
    kommentar        TEXT,
    CHECK (entitet_id <> identifierad_med)
);

CREATE INDEX IF NOT EXISTS identifiering_entitet_idx ON fornmed.identifiering (entitet_id);
CREATE INDEX IF NOT EXISTS identifiering_med_idx ON fornmed.identifiering (identifierad_med);

-- -----------------------------------------------------------------------------
-- Bedömningar: forskningens omdömen, flera per mål
-- -----------------------------------------------------------------------------
-- En bedömning gäller exakt ett av: ett påstående (historicitet), ett verk
-- eller ett vittne (äkthet, datering) eller en identifiering. Flera
-- bedömningar av samma mål gör forskningsdivergens explicit.

CREATE TABLE IF NOT EXISTS fornmed.bedomning (
    id               TEXT PRIMARY KEY,
    pastaende_id     TEXT REFERENCES fornmed.pastaende (id) ON DELETE CASCADE,
    verk_id          TEXT REFERENCES fornmed.verk (id) ON DELETE CASCADE,
    vittne_id        TEXT REFERENCES fornmed.vittne (id) ON DELETE CASCADE,
    identifiering_id TEXT REFERENCES fornmed.identifiering (id) ON DELETE CASCADE,
    aspekt           TEXT NOT NULL,   -- vokabular 'bedomningsaspekt'
    varde            TEXT NOT NULL,   -- vokabular enligt aspekt, t.ex. 'historicitet'
    sakerhet         TEXT,            -- vokabular 'sakerhet'
    bedomare         TEXT NOT NULL,
    publikation      TEXT,
    publikation_id   TEXT,            -- DOI, Libris-id eller liknande
    sidor            TEXT,
    motivering       TEXT,
    ar               INTEGER,
    -- Vem som förde in bedömningen och om någon kontrollerat den mot
    -- publikationen; en referens är inte belagd förrän den granskats
    registrerad_av   TEXT,
    granskad         BOOLEAN NOT NULL DEFAULT FALSE,
    skapad           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(pastaende_id, verk_id, vittne_id, identifiering_id) = 1)
);

CREATE INDEX IF NOT EXISTS bedomning_pastaende_idx ON fornmed.bedomning (pastaende_id);
CREATE INDEX IF NOT EXISTS bedomning_verk_idx ON fornmed.bedomning (verk_id);
CREATE INDEX IF NOT EXISTS bedomning_identifiering_idx ON fornmed.bedomning (identifiering_id);

-- -----------------------------------------------------------------------------
-- SDHK: råposter exakt som i Riksarkivets CSV
-- -----------------------------------------------------------------------------
-- Råtabellen bevarar källans alla fält oförändrade så att den normaliserade
-- strukturen ovan alltid kan byggas om utan ny nedladdning.

CREATE TABLE IF NOT EXISTS fornmed.sdhk_brev (
    sdhk_nr            INTEGER PRIMARY KEY,
    titel              TEXT,
    utfardare          TEXT,
    datum              TEXT,
    ort                TEXT,
    sprak              TEXT,
    regest             TEXT,
    kommentar          TEXT,
    tillagg            TEXT,
    sigill             TEXT,
    original           TEXT,
    medeltida_avskrift TEXT,
    eftermedeltida_avskrift TEXT,
    medeltida_registratur TEXT,
    eftermedeltida_registratur TEXT,
    fotokopia          TEXT,
    tryck              TEXT,
    tryckt_regest      TEXT,
    faksimil           TEXT,
    oversattning       TEXT,
    edition            TEXT
);

-- -----------------------------------------------------------------------------
-- Auktoriteter: längder över ämbetsinnehavare
-- -----------------------------------------------------------------------------
-- Regent-, biskops- och påvelängderna i data/auktoriteter, inlästa av
-- auktoriteter.py så att de följer med databaskopian. person_id är samma id
-- som personens entitet; samma person har samma id i alla längder.

CREATE TABLE IF NOT EXISTS fornmed.auktoritetslangd (
    id               TEXT PRIMARY KEY,
    namn             TEXT NOT NULL,
    beskrivning      TEXT,
    licens           TEXT,
    kalla            TEXT,
    hamtad           TEXT
);

CREATE TABLE IF NOT EXISTS fornmed.auktoritet (
    langd_id         TEXT NOT NULL REFERENCES fornmed.auktoritetslangd (id) ON DELETE CASCADE,
    person_id        TEXT NOT NULL,
    namn             TEXT NOT NULL,
    fodd             INTEGER,
    dod              INTEGER,
    ordningstal      TEXT,
    anm              TEXT,
    wikidata_id      TEXT,
    wikipedia        TEXT,
    PRIMARY KEY (langd_id, person_id)
);

-- En rad per titel och säte: Stenar var biskop både i Linköping och Växjö.
-- `ar_text` är längdens ursprungliga årsuttryck när åren är ungefärliga.
CREATE TABLE IF NOT EXISTS fornmed.auktoritet_titel (
    langd_id         TEXT NOT NULL,
    person_id        TEXT NOT NULL,
    nr               INTEGER NOT NULL,
    titel            TEXT NOT NULL,
    sate             TEXT,
    fran             INTEGER,
    till             INTEGER,
    ar_text          TEXT,
    PRIMARY KEY (langd_id, person_id, nr),
    FOREIGN KEY (langd_id, person_id) REFERENCES fornmed.auktoritet (langd_id, person_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS auktoritet_titel_sate_idx ON fornmed.auktoritet_titel (langd_id, sate, fran);

-- -----------------------------------------------------------------------------
-- Leveranser: databaskopior som lämnat utvecklingsdatorn
-- -----------------------------------------------------------------------------
-- leverans.py skriver en rad före varje pg_dump, så att historiken följer
-- med kopian till servern. `antal` är antal rader per tabell och verk per
-- källsamling; `andringar` är skillnaden mot förra leveransen.

CREATE TABLE IF NOT EXISTS fornmed.leverans (
    id               TEXT PRIMARY KEY,
    tidpunkt         TIMESTAMPTZ NOT NULL DEFAULT now(),
    anmarkning       TEXT,
    antal            JSONB NOT NULL,
    andringar        JSONB NOT NULL
);

-- =============================================================================
-- 2. Migrationer (varje schemaändring efter v1.0, i kronologisk ordning)
-- =============================================================================

-- 2026-11-03: geografiska platser kopplade till entiteter. Ett verk kan ha
-- flera platser med olika roller (utfärdandeort, fyndplats, socken) och
-- samma roll flera gånger ("Visby eller Riga"). Källans ordalydelse behålls i
-- namnform. Tabellerna fylls av platser.py. plats_id tar inte bort sig självt
-- med entiteten: en plats som något pekar på ska inte kunna försvinna.
CREATE TABLE IF NOT EXISTS fornmed.verk_plats (
    verk_id          TEXT NOT NULL REFERENCES fornmed.verk (id) ON DELETE CASCADE,
    plats_id         TEXT NOT NULL REFERENCES fornmed.entitet (id),
    roll             TEXT NOT NULL,   -- vokabular 'platsroll'
    namnform         TEXT NOT NULL,
    osaker           BOOLEAN NOT NULL DEFAULT FALSE,
    harledd          BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (verk_id, roll, plats_id)
);
CREATE INDEX IF NOT EXISTS verk_plats_plats_idx ON fornmed.verk_plats (plats_id, roll);

ALTER TABLE fornmed.auktoritet_titel ADD COLUMN IF NOT EXISTS sate_id TEXT REFERENCES fornmed.entitet (id);
CREATE INDEX IF NOT EXISTS auktoritet_titel_sate_id_idx ON fornmed.auktoritet_titel (sate_id);

-- Platsregistret: var en plats ligger i dag. Uppgifterna är en bedömning och står
-- därför skilda från entiteten och källans namnform. metod säger hur kopplingen
-- gjordes (auktoritet, regel eller sprakmodell) och granskad om en människa har
-- kontrollerat den. Tabellen fylls av platsregister.py och platser.py.
CREATE TABLE IF NOT EXISTS fornmed.plats_uppgift (
    entitet_id       TEXT PRIMARY KEY REFERENCES fornmed.entitet (id) ON DELETE CASCADE,
    slag             TEXT,            -- vokabular 'platsslag'
    nutida_namn      TEXT,
    land_id          TEXT REFERENCES fornmed.entitet (id),
    landskap_id      TEXT REFERENCES fornmed.entitet (id),
    lan_id           TEXT REFERENCES fornmed.entitet (id),
    kommun_id        TEXT REFERENCES fornmed.entitet (id),
    socken_id        TEXT REFERENCES fornmed.entitet (id),
    ingar_i_id       TEXT REFERENCES fornmed.entitet (id),
    latitud          DOUBLE PRECISION,
    longitud         DOUBLE PRECISION,
    kalla            TEXT,
    metod            TEXT NOT NULL,
    granskad         BOOLEAN NOT NULL DEFAULT FALSE,
    anm              TEXT
);
CREATE INDEX IF NOT EXISTS plats_uppgift_kommun_idx ON fornmed.plats_uppgift (kommun_id);
CREATE INDEX IF NOT EXISTS plats_uppgift_socken_idx ON fornmed.plats_uppgift (socken_id);
CREATE INDEX IF NOT EXISTS plats_uppgift_land_idx ON fornmed.plats_uppgift (land_id);

-- 2026-11-07: sökindex. En rad per sökbart objekt (verk och entitet) med tre
-- tider och platser i tre roller, så att sökningen kan filtrera och räkna
-- fasetter och kartan och tidslinjen kan rita träffarna. Tiderna är
-- tillkomst (när källan skrevs), förlaga (äldsta daterade vittne, eftersom
-- vår text ofta bygger på en senare avskrift) och händelse (när det som
-- påståendena beskriver ägde rum). tid_* är den tid som visas först:
-- händelsen om den är känd, annars tillkomsten, och tid_kalla säger vilken.
-- Tabellerna härleds helt ur övriga tabeller och byggs om av sokindex.py.
CREATE TABLE IF NOT EXISTS fornmed.sokpost (
    id               TEXT PRIMARY KEY,   -- verkets eller entitetens id
    objekttyp        TEXT NOT NULL,      -- verk eller entitet
    undertyp         TEXT,               -- verkets genre eller entitetens typ
    kallsamling_id   TEXT,
    rubrik           TEXT NOT NULL,
    sammanfattning   TEXT,
    sprak            TEXT[],
    -- Rubrik och namnformer i sökform (fragor._sokform), för namnsökning
    soknamn          TEXT NOT NULL,
    tillkomst_edtf   TEXT,
    tillkomst_fran   INTEGER,
    tillkomst_till   INTEGER,
    forlaga_typ      TEXT,               -- vokabular 'vittnestyp'
    forlaga_edtf     TEXT,
    forlaga_fran     INTEGER,
    forlaga_till     INTEGER,
    handelse_fran    INTEGER,
    handelse_till    INTEGER,
    antal_pastaenden INTEGER NOT NULL DEFAULT 0,
    tid_fran         INTEGER,
    tid_till         INTEGER,
    tid_kalla        TEXT                -- handelse eller tillkomst
);
CREATE INDEX IF NOT EXISTS sokpost_typ_idx ON fornmed.sokpost (objekttyp, undertyp);
CREATE INDEX IF NOT EXISTS sokpost_tid_idx ON fornmed.sokpost (tid_fran, tid_till);

-- Platserna i tre roller: handelse (påståendenas plats), tillkomst (brevets
-- utfärdandeort, runinskriftens fyndplats) och forvaring, samt lage för en
-- platsentitets eget läge. primar markerar de platser som visas först på
-- kartan: händelsens om den är känd, annars tillkomstens. antal är hur många
-- påståenden som anger platsen.
CREATE TABLE IF NOT EXISTS fornmed.sokpost_plats (
    sokpost_id       TEXT NOT NULL REFERENCES fornmed.sokpost (id) ON DELETE CASCADE,
    plats_id         TEXT NOT NULL REFERENCES fornmed.entitet (id),
    roll             TEXT NOT NULL,      -- vokabular 'sokplatsroll'
    primar           BOOLEAN NOT NULL DEFAULT FALSE,
    osaker           BOOLEAN NOT NULL DEFAULT FALSE,
    antal            INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (sokpost_id, roll, plats_id)
);
CREATE INDEX IF NOT EXISTS sokpost_plats_plats_idx ON fornmed.sokpost_plats (plats_id, roll);

-- =============================================================================
-- 3. Vyer (skapas om vid varje uppstart)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Vy: påståenden med källans tidsavstånd och antal bedömningar
-- -----------------------------------------------------------------------------
-- Tidsavståndet (år mellan påstådd händelse och verkets tillkomst) är en av
-- de starkaste indikatorerna på trovärdighet och räknas fram i stället för
-- att lagras. Det räknas från verkets tidigaste möjliga datering och
-- händelsens senaste, och är alltså det minsta möjliga avståndet.

DROP VIEW IF EXISTS fornmed.pastaende_oversikt;
CREATE VIEW fornmed.pastaende_oversikt AS
SELECT
    p.id,
    p.subjekt_id,
    p.predikat,
    p.objekt_id,
    p.objekt_varde,
    p.tid_edtf,
    v.id            AS verk_id,
    v.titel         AS verk_titel,
    v.genre,
    v.datering_edtf AS verk_datering,
    CASE WHEN p.tid_till IS NOT NULL AND v.datering_fran IS NOT NULL
         THEN v.datering_fran / 10000 - p.tid_till / 10000
    END             AS tidsavstand_ar,
    (SELECT count(*) FROM fornmed.bedomning b WHERE b.pastaende_id = p.id) AS antal_bedomningar,
    (SELECT count(DISTINCT b.varde) FROM fornmed.bedomning b
      WHERE b.pastaende_id = p.id AND b.aspekt = 'historicitet') > 1 AS omstridd
FROM fornmed.pastaende p
JOIN fornmed.passage pa ON pa.id = p.passage_id
JOIN fornmed.verk v ON v.id = pa.verk_id;

-- -----------------------------------------------------------------------------
-- Vy: mål där bedömningarna går isär
-- -----------------------------------------------------------------------------
-- Ett mål är omstritt inom en aspekt när minst två bedömningar ger olika värden.

DROP VIEW IF EXISTS fornmed.omstridda;
CREATE VIEW fornmed.omstridda AS
SELECT
    coalesce(pastaende_id, verk_id, vittne_id, identifiering_id) AS mal_id,
    CASE WHEN pastaende_id IS NOT NULL THEN 'pastaende'
         WHEN verk_id IS NOT NULL THEN 'verk'
         WHEN vittne_id IS NOT NULL THEN 'vittne'
         ELSE 'identifiering'
    END AS maltyp,
    aspekt,
    count(*) AS antal_bedomningar,
    string_agg(DISTINCT varde, ' | ' ORDER BY varde) AS varden
FROM fornmed.bedomning
GROUP BY 1, 2, 3
HAVING count(DISTINCT varde) > 1;

-- -----------------------------------------------------------------------------
-- Vy: entiteter med konkurrerande identifieringar
-- -----------------------------------------------------------------------------
-- Oenighet om identitet syns inte i `omstridda` när varje forskare bara
-- bedömer sitt eget alternativ (gēatas = götar, jutar eller geter). Här
-- räknas uteslutande alternativ som någon bedömt som säkra eller sannolika.

DROP VIEW IF EXISTS fornmed.konkurrerande_identifieringar;
CREATE VIEW fornmed.konkurrerande_identifieringar AS
SELECT
    i.alternativgrupp,
    i.entitet_id,
    count(DISTINCT i.identifierad_med) AS antal_alternativ,
    string_agg(DISTINCT e.namn || ' (' || b.bedomare || ')', ' | ') AS alternativ
FROM fornmed.identifiering i
JOIN fornmed.bedomning b ON b.identifiering_id = i.id AND b.varde IN ('saker', 'sannolik')
JOIN fornmed.entitet e ON e.id = i.identifierad_med
WHERE i.alternativgrupp IS NOT NULL
GROUP BY i.alternativgrupp, i.entitet_id
HAVING count(DISTINCT i.identifierad_med) > 1;

-- =============================================================================
-- Schema för källor, påståenden och forskningens bedömningar (SQLite)
-- Idempotent: körs vid varje uppstart via db.initiera_schema().
-- Strukturen motsvarar schema_postgres.sql; kommentarer om varför finns där.
-- Listor och JSON lagras som JSON-text, tidsstämplar som ISO-text.
-- Bas-schema v1.0, låst vid första publiceringen 2026-11-02. Ändra det aldrig;
-- migrationer för SQLite görs i db.initiera_schema(), eftersom SQLite saknar
-- ADD COLUMN IF NOT EXISTS.
-- =============================================================================

CREATE TABLE IF NOT EXISTS vokabular (
    schema       TEXT NOT NULL,
    kod          TEXT NOT NULL,
    etikett      TEXT NOT NULL,
    beskrivning  TEXT,
    ordning      INTEGER,
    PRIMARY KEY (schema, kod)
);

CREATE TABLE IF NOT EXISTS kallsamling (
    id           TEXT PRIMARY KEY,
    namn         TEXT NOT NULL,
    utgivare     TEXT,
    url          TEXT,
    licens       TEXT,
    version      TEXT,
    importerad   TEXT
);

CREATE TABLE IF NOT EXISTS verk (
    id               TEXT PRIMARY KEY,
    kallsamling_id   TEXT REFERENCES kallsamling (id),
    titel            TEXT NOT NULL,
    upphov           TEXT,
    genre            TEXT,
    sprak            TEXT,            -- JSON-lista, t.ex. ["swe","lat"]
    utfardandeort    TEXT,
    datering_edtf    TEXT,
    datering_fran    INTEGER,
    datering_till    INTEGER,
    datering_anm     TEXT,
    beskrivning      TEXT,
    extern_url       TEXT,
    extra            TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS verk_datering_idx ON verk (datering_fran, datering_till);
CREATE INDEX IF NOT EXISTS verk_genre_idx ON verk (genre);

CREATE TABLE IF NOT EXISTS vittne (
    id               TEXT PRIMARY KEY,
    verk_id          TEXT NOT NULL REFERENCES verk (id) ON DELETE CASCADE,
    typ              TEXT NOT NULL,
    beskrivning      TEXT NOT NULL,
    signum           TEXT,
    datering_edtf    TEXT,
    datering_fran    INTEGER,
    datering_till    INTEGER,
    iiif_manifest    TEXT
);

CREATE INDEX IF NOT EXISTS vittne_verk_idx ON vittne (verk_id);

CREATE TABLE IF NOT EXISTS utgava (
    id               TEXT PRIMARY KEY,
    verk_id          TEXT REFERENCES verk (id) ON DELETE CASCADE,
    referens         TEXT NOT NULL,
    licens           TEXT,
    sprak            TEXT,
    typ              TEXT,
    roll             TEXT,
    oversattare      TEXT,
    ar               INTEGER
);

CREATE TABLE IF NOT EXISTS passage (
    id               TEXT PRIMARY KEY,
    verk_id          TEXT NOT NULL REFERENCES verk (id) ON DELETE CASCADE,
    utgava_id        TEXT REFERENCES utgava (id) ON DELETE SET NULL,
    typ              TEXT NOT NULL,
    adress           TEXT,
    ordning          INTEGER NOT NULL DEFAULT 0,
    sprak            TEXT,
    text             TEXT NOT NULL,
    url              TEXT,
    del              TEXT,
    del_typ          TEXT
);

CREATE INDEX IF NOT EXISTS passage_verk_idx ON passage (verk_id);
CREATE INDEX IF NOT EXISTS passage_utgava_ordning_idx ON passage (utgava_id, ordning);
CREATE INDEX IF NOT EXISTS utgava_verk_idx ON utgava (verk_id);

-- FTS5 med extern innehållstabell; triggarna håller indexet i takt med
-- passage. remove_diacritics 0 eftersom å/ä/ö är egna bokstäver i svenska.
CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5 (
    text,
    content = 'passage',
    content_rowid = 'rowid',
    tokenize = 'unicode61 remove_diacritics 0'
);

CREATE TRIGGER IF NOT EXISTS passage_fts_ins AFTER INSERT ON passage BEGIN
    INSERT INTO passage_fts (rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TRIGGER IF NOT EXISTS passage_fts_del AFTER DELETE ON passage BEGIN
    INSERT INTO passage_fts (passage_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
END;

CREATE TRIGGER IF NOT EXISTS passage_fts_upd AFTER UPDATE OF text ON passage BEGIN
    INSERT INTO passage_fts (passage_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
    INSERT INTO passage_fts (rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TABLE IF NOT EXISTS chunk (
    id               INTEGER PRIMARY KEY,
    passage_id       TEXT NOT NULL REFERENCES passage (id) ON DELETE CASCADE,
    chunk_nr         INTEGER NOT NULL,
    text             TEXT NOT NULL,
    UNIQUE (passage_id, chunk_nr)
);

-- sqlite-vec; kräver att tillägget laddats i anslutningen (se db._hamta_db)
CREATE VIRTUAL TABLE IF NOT EXISTS embedding USING vec0 (
    chunk_id         INTEGER PRIMARY KEY,
    vektor           FLOAT[768] distance_metric=cosine,
    -- Metadatakolumn (utan +) så att grannsökningen kan filtrera på modell
    modell           TEXT
);

-- Virtuella tabeller omfattas inte av ON DELETE CASCADE
CREATE TRIGGER IF NOT EXISTS chunk_embedding_del AFTER DELETE ON chunk BEGIN
    DELETE FROM embedding WHERE chunk_id = old.id;
END;

CREATE TABLE IF NOT EXISTS entitet (
    id               TEXT PRIMARY KEY,
    typ              TEXT NOT NULL,
    namn             TEXT NOT NULL,
    beskrivning      TEXT,
    wikidata_id      TEXT,
    extra            TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS entitet_typ_namn_idx ON entitet (typ, namn);

CREATE TABLE IF NOT EXISTS entitet_namnform (
    entitet_id       TEXT NOT NULL REFERENCES entitet (id) ON DELETE CASCADE,
    namnform         TEXT NOT NULL,
    sprak            TEXT,
    passage_id       TEXT REFERENCES passage (id) ON DELETE SET NULL,
    PRIMARY KEY (entitet_id, namnform)
);

CREATE INDEX IF NOT EXISTS entitet_namnform_idx ON entitet_namnform (lower(namnform));

CREATE TABLE IF NOT EXISTS ordboksartikel (
    id               TEXT PRIMARY KEY,
    kallsamling_id   TEXT NOT NULL REFERENCES kallsamling (id),
    lemma            TEXT NOT NULL,
    lemgram          TEXT,
    ordklass         TEXT,
    betydelse_nr     INTEGER NOT NULL,
    definition       TEXT NOT NULL,
    former           TEXT NOT NULL DEFAULT '[]',
    sokform          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ordboksartikel_sokform_idx ON ordboksartikel (sokform);
CREATE INDEX IF NOT EXISTS ordboksartikel_lemgram_idx ON ordboksartikel (lemgram);

CREATE VIRTUAL TABLE IF NOT EXISTS ordbok_fts USING fts5 (
    lemma,
    definition,
    content = 'ordboksartikel',
    content_rowid = 'rowid',
    tokenize = 'unicode61 remove_diacritics 0'
);

CREATE TRIGGER IF NOT EXISTS ordbok_fts_ins AFTER INSERT ON ordboksartikel BEGIN
    INSERT INTO ordbok_fts (rowid, lemma, definition) VALUES (new.rowid, new.lemma, new.definition);
END;

CREATE TRIGGER IF NOT EXISTS ordbok_fts_del AFTER DELETE ON ordboksartikel BEGIN
    INSERT INTO ordbok_fts (ordbok_fts, rowid, lemma, definition)
    VALUES ('delete', old.rowid, old.lemma, old.definition);
END;

CREATE TRIGGER IF NOT EXISTS ordbok_fts_upd AFTER UPDATE OF lemma, definition ON ordboksartikel BEGIN
    INSERT INTO ordbok_fts (ordbok_fts, rowid, lemma, definition)
    VALUES ('delete', old.rowid, old.lemma, old.definition);
    INSERT INTO ordbok_fts (rowid, lemma, definition) VALUES (new.rowid, new.lemma, new.definition);
END;

CREATE TABLE IF NOT EXISTS term (
    id               TEXT PRIMARY KEY,
    entitet_id       TEXT NOT NULL REFERENCES entitet (id) ON DELETE CASCADE,
    term             TEXT NOT NULL,
    sprak            TEXT NOT NULL,
    termtyp          TEXT NOT NULL,
    sokform          TEXT NOT NULL,
    artikel_id       TEXT REFERENCES ordboksartikel (id) ON DELETE SET NULL,
    registrerad_av   TEXT,
    granskad         INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS term_sokform_idx ON term (sokform);
CREATE INDEX IF NOT EXISTS term_entitet_idx ON term (entitet_id);

CREATE TABLE IF NOT EXISTS begreppsrelation (
    fran_id          TEXT NOT NULL REFERENCES entitet (id) ON DELETE CASCADE,
    till_id          TEXT NOT NULL REFERENCES entitet (id) ON DELETE CASCADE,
    relation         TEXT NOT NULL,
    PRIMARY KEY (fran_id, till_id, relation),
    CHECK (fran_id <> till_id)
);

CREATE TABLE IF NOT EXISTS pastaende (
    id               TEXT PRIMARY KEY,
    passage_id       TEXT NOT NULL REFERENCES passage (id) ON DELETE CASCADE,
    subjekt_id       TEXT NOT NULL REFERENCES entitet (id),
    predikat         TEXT NOT NULL,
    objekt_id        TEXT REFERENCES entitet (id),
    objekt_varde     TEXT,
    plats_id         TEXT REFERENCES entitet (id),
    tid_edtf         TEXT,
    tid_fran         INTEGER,
    tid_till         INTEGER,
    citat            TEXT,
    extraktion       TEXT NOT NULL DEFAULT 'manuell',
    extraherad_av    TEXT,
    granskad         INTEGER NOT NULL DEFAULT 0,
    granskad_av      TEXT,
    skapad           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (objekt_id IS NOT NULL OR objekt_varde IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS pastaende_subjekt_idx ON pastaende (subjekt_id);
CREATE INDEX IF NOT EXISTS pastaende_objekt_idx ON pastaende (objekt_id);
CREATE INDEX IF NOT EXISTS pastaende_passage_idx ON pastaende (passage_id);
CREATE INDEX IF NOT EXISTS pastaende_tid_idx ON pastaende (tid_fran, tid_till);

CREATE TABLE IF NOT EXISTS pastaende_relation (
    fran_id          TEXT NOT NULL REFERENCES pastaende (id) ON DELETE CASCADE,
    till_id          TEXT NOT NULL REFERENCES pastaende (id) ON DELETE CASCADE,
    relation         TEXT NOT NULL,
    kommentar        TEXT,
    PRIMARY KEY (fran_id, till_id, relation),
    CHECK (fran_id <> till_id)
);

CREATE TABLE IF NOT EXISTS identifiering (
    id               TEXT PRIMARY KEY,
    entitet_id       TEXT NOT NULL REFERENCES entitet (id) ON DELETE CASCADE,
    identifierad_med TEXT NOT NULL REFERENCES entitet (id) ON DELETE CASCADE,
    alternativgrupp  TEXT,
    kommentar        TEXT,
    CHECK (entitet_id <> identifierad_med)
);

CREATE INDEX IF NOT EXISTS identifiering_entitet_idx ON identifiering (entitet_id);
CREATE INDEX IF NOT EXISTS identifiering_med_idx ON identifiering (identifierad_med);

CREATE TABLE IF NOT EXISTS bedomning (
    id               TEXT PRIMARY KEY,
    pastaende_id     TEXT REFERENCES pastaende (id) ON DELETE CASCADE,
    verk_id          TEXT REFERENCES verk (id) ON DELETE CASCADE,
    vittne_id        TEXT REFERENCES vittne (id) ON DELETE CASCADE,
    identifiering_id TEXT REFERENCES identifiering (id) ON DELETE CASCADE,
    aspekt           TEXT NOT NULL,
    varde            TEXT NOT NULL,
    sakerhet         TEXT,
    bedomare         TEXT NOT NULL,
    publikation      TEXT,
    publikation_id   TEXT,
    sidor            TEXT,
    motivering       TEXT,
    ar               INTEGER,
    registrerad_av   TEXT,
    granskad         INTEGER NOT NULL DEFAULT 0,
    skapad           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((pastaende_id IS NOT NULL) + (verk_id IS NOT NULL) + (vittne_id IS NOT NULL)
           + (identifiering_id IS NOT NULL) = 1)
);

CREATE INDEX IF NOT EXISTS bedomning_pastaende_idx ON bedomning (pastaende_id);
CREATE INDEX IF NOT EXISTS bedomning_verk_idx ON bedomning (verk_id);
CREATE INDEX IF NOT EXISTS bedomning_identifiering_idx ON bedomning (identifiering_id);

CREATE TABLE IF NOT EXISTS sdhk_brev (
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

-- Vyerna skapas om vid varje uppstart så att ändrade definitioner slår
-- igenom; SQLite saknar CREATE OR REPLACE VIEW
DROP VIEW IF EXISTS pastaende_oversikt;
CREATE VIEW pastaende_oversikt AS
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
    (SELECT count(*) FROM bedomning b WHERE b.pastaende_id = p.id) AS antal_bedomningar,
    (SELECT count(DISTINCT b.varde) FROM bedomning b
      WHERE b.pastaende_id = p.id AND b.aspekt = 'historicitet') > 1 AS omstridd
FROM pastaende p
JOIN passage pa ON pa.id = p.passage_id
JOIN verk v ON v.id = pa.verk_id;

-- SQLite tillåter inte DISTINCT i ett aggregat med avgränsare, så de
-- distinkta värdena tas fram i en delfråga och sätts ihop med ' | ' som i
-- Postgres
DROP VIEW IF EXISTS omstridda;
CREATE VIEW omstridda AS
SELECT mal_id, maltyp, aspekt, sum(n) AS antal_bedomningar,
       group_concat(varde, ' | ') AS varden
FROM (
    SELECT
        coalesce(pastaende_id, verk_id, vittne_id, identifiering_id) AS mal_id,
        CASE WHEN pastaende_id IS NOT NULL THEN 'pastaende'
             WHEN verk_id IS NOT NULL THEN 'verk'
             WHEN vittne_id IS NOT NULL THEN 'vittne'
             ELSE 'identifiering'
        END AS maltyp,
        aspekt,
        varde,
        count(*) AS n
    FROM bedomning
    GROUP BY 1, 2, 3, 4
    ORDER BY varde
)
GROUP BY mal_id, maltyp, aspekt
HAVING count(*) > 1;

DROP VIEW IF EXISTS konkurrerande_identifieringar;
CREATE VIEW konkurrerande_identifieringar AS
SELECT alternativgrupp, entitet_id, count(DISTINCT identifierad_med) AS antal_alternativ,
       group_concat(alternativ, ' | ') AS alternativ
FROM (
    SELECT DISTINCT i.alternativgrupp, i.entitet_id, i.identifierad_med,
           e.namn || ' (' || b.bedomare || ')' AS alternativ
    FROM identifiering i
    JOIN bedomning b ON b.identifiering_id = i.id AND b.varde IN ('saker', 'sannolik')
    JOIN entitet e ON e.id = i.identifierad_med
    WHERE i.alternativgrupp IS NOT NULL
    ORDER BY alternativ
)
GROUP BY alternativgrupp, entitet_id
HAVING count(DISTINCT identifierad_med) > 1;

-- Auktoriteter och leveranser; se schema_postgres.sql
CREATE TABLE IF NOT EXISTS auktoritetslangd (
    id               TEXT PRIMARY KEY,
    namn             TEXT NOT NULL,
    beskrivning      TEXT,
    licens           TEXT,
    kalla            TEXT,
    hamtad           TEXT
);

CREATE TABLE IF NOT EXISTS auktoritet (
    langd_id         TEXT NOT NULL REFERENCES auktoritetslangd (id) ON DELETE CASCADE,
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

CREATE TABLE IF NOT EXISTS auktoritet_titel (
    langd_id         TEXT NOT NULL,
    person_id        TEXT NOT NULL,
    nr               INTEGER NOT NULL,
    titel            TEXT NOT NULL,
    sate             TEXT,
    fran             INTEGER,
    till             INTEGER,
    ar_text          TEXT,
    PRIMARY KEY (langd_id, person_id, nr),
    FOREIGN KEY (langd_id, person_id) REFERENCES auktoritet (langd_id, person_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS auktoritet_titel_sate_idx ON auktoritet_titel (langd_id, sate, fran);

CREATE TABLE IF NOT EXISTS leverans (
    id               TEXT PRIMARY KEY,
    tidpunkt         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    anmarkning       TEXT,
    antal            TEXT NOT NULL,
    andringar        TEXT NOT NULL
);

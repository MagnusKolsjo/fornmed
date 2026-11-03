"""
Databaslager för källor, påståenden och bedömningar.

Backend väljs med DATABASE_URL: postgresql://… eller sqlite:///…
Schemat ligger i db/schema_postgres.sql respektive db/schema_sqlite.sql.
"""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from vokabular import VOKABULAR

# psycopg2 importeras bara om Postgres används — annars är det
# inte ett krav att paketet finns installerat
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

# sqlite-vec behövs bara med SQLite-backend
try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

load_dotenv(Path(__file__).parent / ".env")

log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQL_KATALOG = Path(__file__).parent / "db"


def _ar_postgres() -> bool:
    """Returnerar True om DATABASE_URL pekar mot Postgres, annars False."""
    return DATABASE_URL.startswith(("postgresql://", "postgres://"))


def _anslut_postgres():
    """Ansluter till Postgres och väntar en kort stund om databasen just byts.

    Vid en leverans på servern (deploy/las_in_databas.sh) stängs den gamla
    databasen för nya anslutningar under de millisekunder som namnbytet tar.
    En anslutning som kommer då försöker igen i stället för att misslyckas.
    Andra anslutningsfel visas direkt.
    """
    for forsok in range(30):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as fel:
            if "not currently accepting connections" not in str(fel) or forsok == 29:
                raise
            time.sleep(0.1)


def _hamta_db():
    """Öppnar en ny databasanslutning. Varje anropare ansvarar för att stänga den."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL är inte satt")
    if _ar_postgres():
        if psycopg2 is None:
            raise RuntimeError(
                "DATABASE_URL pekar mot Postgres men psycopg2 är inte installerat. "
                "Kör 'pip install psycopg2-binary' eller välj sqlite:// i DATABASE_URL."
            )
        return _anslut_postgres()
    # sqlite:///relativ.db ger "relativ.db", sqlite:////abs/sökväg.db ger "/abs/sökväg.db"
    sokvag = urlparse(DATABASE_URL).path[1:]
    if not sokvag:
        raise RuntimeError("DATABASE_URL för SQLite saknar filsökväg")
    if sqlite_vec is None:
        raise RuntimeError(
            "DATABASE_URL pekar mot SQLite men sqlite-vec är inte installerat. "
            "Kör 'pip install sqlite-vec' eller välj postgresql:// i DATABASE_URL."
        )
    conn = sqlite3.connect(sokvag)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    # SQLite kontrollerar inte främmande nycklar om det inte slås på per anslutning
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ph() -> str:
    """Platshållare för parameterbindning. Postgres använder %s, SQLite använder ?."""
    return "%s" if _ar_postgres() else "?"


def _prefix() -> str:
    """Schema-prefix för tabellnamn. Postgres får 'fornmed.', SQLite får ''."""
    return "fornmed." if _ar_postgres() else ""


def sprakvarde(koder: list[str]):
    """Anpassar en språklista till kolumntypen: TEXT[] i Postgres, JSON-text i SQLite."""
    return koder if _ar_postgres() else json.dumps(koder)


def initiera_schema() -> None:
    """Skapar tabeller, index och vokabulär om de inte redan finns. Säkert att köra många gånger."""
    sql_fil = SQL_KATALOG / ("schema_postgres.sql" if _ar_postgres() else "schema_sqlite.sql")
    sql = sql_fil.read_text(encoding="utf-8")

    conn = _hamta_db()
    try:
        if _ar_postgres():
            with conn, conn.cursor() as cur:
                cur.execute(sql)
                skapa_vektorindex(cur)
        else:
            conn.executescript(sql)
            # SQLite saknar ADD COLUMN IF NOT EXISTS, så migrationerna efter
            # bas-schemat v1.0 görs här i stället för i schemafilen: kolumner
            # som tillkommit läggs till om de saknas
            tillagda: dict[str, tuple[str, ...]] = {
                "auktoritet_titel": ("sate_id TEXT REFERENCES entitet (id)",),
            }
            for tabell, definitioner in tillagda.items():
                kolumner = {r[1] for r in conn.execute(f"PRAGMA table_info({tabell})")}
                for definition in definitioner:
                    if definition.split()[0] not in kolumner:
                        conn.execute(f"ALTER TABLE {tabell} ADD COLUMN {definition}")
        fyll_vokabular(conn)
    finally:
        conn.close()


def skapa_vektorindex(cur) -> None:
    """
    Ett HNSW-index per embeddingmodell (Postgres). Vektorer från olika
    modeller ligger i samma tabell men går inte att jämföra; ett partiellt
    index per modell låter vektorsökningen hålla sig till en modell utan att
    filtrera bort träffar efter grannsökningen. Modellnamnen tas ur
    konfigurationen, så att ett modellbyte får ett eget index.
    """
    # Importeras här så att .env hunnit läsas in innan modellnamnen läses
    import embeddings

    for roll, modell in embeddings.MODELLER.items():
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS embedding_vektor_{roll}_idx ON fornmed.embedding "
            f"USING hnsw (vektor vector_cosine_ops) WHERE modell = %s",
            (modell,),
        )


def fyll_vokabular(conn) -> None:
    """Skriver in VOKABULAR och uppdaterar etiketter och beskrivningar som ändrats."""
    upsert(
        conn,
        "vokabular",
        ["schema", "kod", "etikett", "beskrivning", "ordning"],
        ["schema", "kod"],
        [(s, k, e, b, i) for i, (s, k, e, b) in enumerate(VOKABULAR)],
    )


def upsert(conn, tabell: str, kolumner: list[str], nyckel: list[str], rader: list[tuple]) -> None:
    """
    Infogar rader eller uppdaterar befintliga vid nyckelkonflikt.

    ON CONFLICT … DO UPDATE har samma syntax i Postgres och SQLite ≥ 3.24,
    så bara platshållare och batchkörning skiljer backenderna åt.
    """
    if not rader:
        return
    uppdatera = [k for k in kolumner if k not in nyckel]
    sql = (
        f"INSERT INTO {_prefix()}{tabell} ({', '.join(kolumner)}) "
        f"VALUES ({', '.join([_ph()] * len(kolumner))}) "
        f"ON CONFLICT ({', '.join(nyckel)}) "
        + (
            f"DO UPDATE SET {', '.join(f'{k} = excluded.{k}' for k in uppdatera)}"
            if uppdatera
            else "DO NOTHING"
        )
    )
    if _ar_postgres():
        with conn, conn.cursor() as cur:
            # execute_batch skickar många rader per nätverksanrop; vanlig
            # executemany i psycopg2 gör ett anrop per rad
            psycopg2.extras.execute_batch(cur, sql, rader, page_size=500)
    else:
        with conn:
            conn.executemany(sql, rader)

"""
Registrerar en leverans av databasen och skriver databaskopian.

Körs på utvecklingsdatorn när databasen ska till servern. Skriptet räknar
rader per tabell och verk per källsamling, jämför med förra leveransen och
skriver en rad i tabellen leverans. Därefter görs kopian med pg_dump, så att
raden följer med: webbplatsens lista över uppdateringar och API:ets
/v1/leveranser bygger på den.

Ändringarna anger nya och borttagna källsamlingar och de tabeller och
källsamlingar vars antal har ändrats. En anmärkning beskriver leveransen med
egna ord, till exempel vilka källor eller påståenden som tillkommit.

Användning:
    python leverans.py --anmarkning "Erikskrönikan och 2 000 nya påståenden" --fil fornmed.pgdump
    python leverans.py --bara-registrera
"""

import argparse
import json
import logging
import os
import subprocess
from datetime import datetime

import db
from fragor import _en, _rader

log = logging.getLogger("leverans")

# Tabellerna som räknas; de motsvarar det en läsare märker som nytt
TABELLER = ("verk", "passage", "utgava", "entitet", "pastaende", "bedomning", "identifiering",
            "term", "ordboksartikel", "auktoritet")


def rakna() -> dict:
    """Antal rader per tabell och verk per källsamling."""
    p = db._prefix()
    return {
        "tabeller": {t: _en(f"SELECT count(*) AS n FROM {p}{t}")["n"] for t in TABELLER},
        "kallsamlingar": {r["id"]: {"namn": r["namn"], "verk": r["verk"]} for r in _rader(
            f"SELECT k.id, k.namn, count(v.id) AS verk FROM {p}kallsamling k "
            f"LEFT JOIN {p}verk v ON v.kallsamling_id = k.id GROUP BY k.id, k.namn"
        )},
    }


def jamfor(fore: dict | None, efter: dict) -> dict:
    """Skillnaden mellan två räkningar."""
    if fore is None:
        return {"forsta_leveransen": True}
    andringar: dict = {"tabeller": {}, "nya_kallsamlingar": [], "borttagna_kallsamlingar": [],
                       "kallsamlingar": {}}
    for tabell, antal in efter["tabeller"].items():
        tidigare = fore["tabeller"].get(tabell, 0)
        if antal != tidigare:
            andringar["tabeller"][tabell] = {"fore": tidigare, "efter": antal, "skillnad": antal - tidigare}
    for k_id, k in efter["kallsamlingar"].items():
        if k_id not in fore["kallsamlingar"]:
            andringar["nya_kallsamlingar"].append({"id": k_id, **k})
        elif k["verk"] != fore["kallsamlingar"][k_id]["verk"]:
            andringar["kallsamlingar"][k_id] = {"namn": k["namn"],
                                                "fore": fore["kallsamlingar"][k_id]["verk"],
                                                "efter": k["verk"]}
    andringar["borttagna_kallsamlingar"] = [
        {"id": k_id, **k} for k_id, k in fore["kallsamlingar"].items() if k_id not in efter["kallsamlingar"]
    ]
    return andringar


def _json(varde):
    """JSON-kolumnerna är JSONB i Postgres och text i SQLite."""
    return varde if isinstance(varde, (dict, list)) else json.loads(varde)


def registrera(anmarkning: str | None) -> dict:
    """Skriver en leveransrad och returnerar den."""
    p, ph = db._prefix(), db._ph()
    forra = _en(f"SELECT antal FROM {p}leverans ORDER BY tidpunkt DESC LIMIT 1")
    antal = rakna()
    andringar = jamfor(_json(forra["antal"]) if forra else None, antal)
    leverans_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {p}leverans (id, anmarkning, antal, andringar) VALUES ({ph}, {ph}, {ph}, {ph})",
            (leverans_id, anmarkning, json.dumps(antal, ensure_ascii=False),
             json.dumps(andringar, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()
    return {"id": leverans_id, "anmarkning": anmarkning, "andringar": andringar}


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--anmarkning", help="vad leveransen innehåller, med egna ord")
    tolk.add_argument("--fil", help="filen som pg_dump skriver (formatet custom, -Fc)")
    tolk.add_argument("--bara-registrera", action="store_true",
                      help="skriv leveransraden men gör ingen kopia")
    tolk.add_argument("--pg-dump", default=os.getenv("FORNMED_PG_DUMP", "pg_dump"),
                      help="pg_dump i serverns huvudversion (standard: FORNMED_PG_DUMP eller pg_dump)")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not argument.bara_registrera and not argument.fil:
        tolk.error("ange --fil för kopian, eller --bara-registrera")
    if not argument.bara_registrera and not db._ar_postgres():
        tolk.error("kopian görs med pg_dump och kräver PostgreSQL; använd --bara-registrera")

    db.initiera_schema()
    leverans = registrera(argument.anmarkning)
    log.info("Leverans %s registrerad: %s", leverans["id"],
             json.dumps(leverans["andringar"], ensure_ascii=False))

    if argument.bara_registrera:
        return
    # pg_dump läser anslutningen ur samma DATABASE_URL som skripten. Det
    # måste vara samma huvudversion som servern kör: en kopia från en nyare
    # pg_dump kan inte läsas av en äldre pg_restore.
    subprocess.run([argument.pg_dump, "-Fc", "--no-owner", "-d", db.DATABASE_URL,
                    "-f", argument.fil], check=True)
    log.info("Kopian skriven till %s", argument.fil)


if __name__ == "__main__":
    main()

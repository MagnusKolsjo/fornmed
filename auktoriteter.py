"""
Läser in auktoritetslängderna i databasen.

Längderna över regenter, biskopar och påvar ligger som filer i
data/auktoriteter och används av importen av SDHK:s utfärdarfält. Här läses
de in i tabellerna auktoritetslangd, auktoritet och auktoritet_titel, så att
de följer med databaskopian till servern och kan hämtas genom API:et.

Personerna får samma id som deras entiteter. Regent- och biskopslängden har
id:n i filerna; påvarnas id bildas av pastaenden_sdhk.pave_id, som importen
av utfärdarfältet också använder.

Inläsningen ersätter hela längden varje gång och kan köras om när filerna
har ändrats.
Kör platser.py efteråt, så att sätena kopplas till sina platser igen.

Användning:
    python auktoriteter.py
"""

import argparse
import json
import logging
from pathlib import Path

import db
from pastaenden_sdhk import pave_id

log = logging.getLogger("auktoriteter")

KATALOG = Path(__file__).parent / "data" / "auktoriteter"

# Längdens namn, licens och ursprung. Regent- och påvelängderna är
# projektets egna sammanställningar och har ingen licens utöver projektets;
# biskopslängden bygger på svenska Wikipedia och måste behålla dess licens.
LANGDER = {
    "regenter": {
        "namn": "Regenter och riksföreståndare",
        "licens": None,
        "kalla": "Sammanställd för projektet ur SDHK:s utfärdare och allmänna uppslagsverk; Wikidata-id ur Wikidata (CC0)",
    },
    "biskopar": {
        "namn": "Biskopar och ärkebiskopar",
        "licens": "CC BY-SA 4.0 (svenska Wikipedia); Wikidata CC0",
        "kalla": "Svenska Wikipedias stiftslistor och Wikidata, via bygg_biskopslista.py",
    },
    "pavar": {
        "namn": "Påvar och motpåvar",
        "licens": None,
        "kalla": "Sammanställd för projektet ur allmänna uppslagsverk; inte kontrollerad mot primärlitteratur; Wikidata-id ur Wikidata (CC0)",
    },
}


def las_langd(langd_id: str) -> tuple[dict, list[dict], list[tuple]]:
    """(längd, personer, titlar) ur längdens fil, i tabellernas form."""
    data = json.loads((KATALOG / f"{langd_id}.json").read_text(encoding="utf-8"))
    langd = {"id": langd_id, "beskrivning": data.get("beskrivning"), "hamtad": data.get("hamtad"),
             **LANGDER[langd_id]}
    personer, titlar = [], []

    if langd_id == "pavar":
        for p in data["pavar"]:
            person_id = pave_id(p)
            personer.append({"person_id": person_id, "namn": f"{p['namn']} {p['nr']}".strip(),
                             "fodd": None, "dod": p.get("dod", p["till"]), "ordningstal": p["nr"],
                             "anm": p.get("anm"), "wikidata_id": p.get("wikidata"), "wikipedia": None})
            titlar.append((person_id, 1, "pave", None, p["fran"], p["till"], None))
        return langd, personer, titlar

    for p in data["personer"]:
        personer.append({"person_id": p["id"], "namn": p["namn"], "fodd": p.get("fodd"),
                         "dod": p.get("dod"), "ordningstal": p.get("ordningstal"),
                         "anm": p.get("anm"), "wikidata_id": p.get("wikidata"),
                         "wikipedia": p.get("wikipedia")})
        ar_text = p.get("ar_text") or {}
        for nr, (titel, sate, fran, till) in enumerate(p["titlar"], start=1):
            titlar.append((p["id"], nr, titel, sate, fran, till, ar_text.get(sate)))
    return langd, personer, titlar


def las_in(conn, langd_id: str) -> tuple[int, int]:
    """Ersätter längden i databasen. Returnerar (personer, titlar)."""
    langd, personer, titlar = las_langd(langd_id)
    p, ph = db._prefix(), db._ph()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {p}auktoritet_titel WHERE langd_id = {ph}", (langd_id,))
    cur.execute(f"DELETE FROM {p}auktoritet WHERE langd_id = {ph}", (langd_id,))
    cur.execute(f"DELETE FROM {p}auktoritetslangd WHERE id = {ph}", (langd_id,))
    kolumner = ("id", "namn", "beskrivning", "licens", "kalla", "hamtad")
    cur.execute(f"INSERT INTO {p}auktoritetslangd ({', '.join(kolumner)}) "
                f"VALUES ({', '.join([ph] * len(kolumner))})", [langd[k] for k in kolumner])
    kolumner = ("person_id", "namn", "fodd", "dod", "ordningstal", "anm", "wikidata_id", "wikipedia")
    cur.executemany(
        f"INSERT INTO {p}auktoritet (langd_id, {', '.join(kolumner)}) "
        f"VALUES ({', '.join([ph] * (len(kolumner) + 1))})",
        [(langd_id, *(person[k] for k in kolumner)) for person in personer],
    )
    cur.executemany(
        f"INSERT INTO {p}auktoritet_titel (langd_id, person_id, nr, titel, sate, fran, till, ar_text) "
        f"VALUES ({', '.join([ph] * 8)})",
        [(langd_id, *titel) for titel in titlar],
    )
    conn.commit()
    return len(personer), len(titlar)


def main() -> None:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db.initiera_schema()
    conn = db._hamta_db()
    try:
        for langd_id in LANGDER:
            personer, titlar = las_in(conn, langd_id)
            log.info("%s: %d personer, %d titlar", langd_id, personer, titlar)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

"""
Skriver Fornmeds kopplingar till Wikidata som kommandon för QuickStatements, så att
varje Wikidata-objekt som Fornmed känner till får sitt Fornmed-id.

Med i filen är entiteter som har ett Wikidata-id, i registret eller i
auktoritetslängderna, och som inte har ersatts av en annan entitet. En ersatt
entitet hänvisar redan till den som behålls, och varje Wikidata-objekt ska ha ett
enda Fornmed-id.

Med --kontrollera frågas Wikidata om varje objekt. Objekt som inte finns eller
har omdirigerats tas inte med utan rapporteras, liksom objekt som redan har ett
värde för egenskapen; ett objekt som redan har just det värdet tas inte med igen.

Filformatet är QuickStatements version 1: en rad per påstående, med objekt,
egenskap och värde åtskilda av tabb, och värdet inom citattecken.

    python quickstatements.py --egenskap P1234 -o fornmed_quickstatements.tsv
    python quickstatements.py --egenskap P1234 -o fornmed_quickstatements.tsv --kontrollera
"""

import argparse
import json
import re
import sys
import time
from collections import Counter
import urllib.parse
import urllib.request
from pathlib import Path

import db
from fragor import _rader

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"


def kopplingar() -> list[tuple[str, str]]:
    """(Wikidata-id, Fornmed-id) för entiteter som inte är ersatta, sorterade på Fornmed-id."""
    p = db._prefix()
    rader = _rader(f"""
        SELECT e.id, coalesce(e.wikidata_id, a.wikidata_id) AS q
        FROM {p}entitet e
        LEFT JOIN (SELECT person_id, min(wikidata_id) AS wikidata_id FROM {p}auktoritet
                   WHERE wikidata_id IS NOT NULL GROUP BY person_id) a ON a.person_id = e.id
        WHERE coalesce(e.wikidata_id, a.wikidata_id) IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM {p}identifiering i
                          WHERE i.entitet_id = e.id AND i.kommentar = 'ersatt_av')
        ORDER BY e.id""")
    return [(r["q"], r["id"]) for r in rader]


def _hamta(parametrar: dict) -> dict:
    url = f"{WIKIDATA_API}?{urllib.parse.urlencode(parametrar)}"
    for forsok in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
                                        timeout=60) as svar:
                return json.load(svar)
        except OSError:
            time.sleep(10 * (forsok + 1))
    raise RuntimeError(f"Wikidata svarar inte: {url[:120]}")


def kontrollera(par: list[tuple[str, str]], egenskap: str) -> tuple[list[tuple[str, str]], dict[str, list]]:
    """Behåll de par vars objekt finns och saknar värdet; rapportera resten per orsak."""
    q_id = sorted({q for q, _ in par})
    info: dict[str, dict] = {}
    for i in range(0, len(q_id), 50):
        svar = _hamta({"action": "wbgetentities", "ids": "|".join(q_id[i:i + 50]), "props": "claims|info",
                       "format": "json"})
        for q, ent in svar.get("entities", {}).items():
            varden = [c["mainsnak"].get("datavalue", {}).get("value")
                      for c in ent.get("claims", {}).get(egenskap, [])]
            info[q] = {"saknas": "missing" in ent, "omdirigerad": ent.get("id", q) != q,
                       "varden": [v for v in varden if v]}
        time.sleep(0.5)
    behall, rapport = [], {"saknas": [], "omdirigerad": [], "har värdet redan": [], "har ett annat värde": []}
    for q, fid in par:
        i = info.get(q, {"saknas": True})
        if i["saknas"]:
            rapport["saknas"].append((q, fid))
        elif i["omdirigerad"]:
            rapport["omdirigerad"].append((q, fid))
        elif fid in i["varden"]:
            rapport["har värdet redan"].append((q, fid))
        elif i["varden"]:
            rapport["har ett annat värde"].append((q, fid, i["varden"]))
        else:
            behall.append((q, fid))
    return behall, rapport


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--egenskap", required=True, help="egenskapen för Fornmeds id, t.ex. P1234")
    tolk.add_argument("-o", "--ut", type=Path, required=True, help="filen att skriva")
    tolk.add_argument("--kontrollera", action="store_true", help="fråga Wikidata om varje objekt först")
    args = tolk.parse_args()
    if not re.fullmatch(r"P[1-9]\d*", args.egenskap):
        sys.exit(f"Egenskapen ska anges som P följt av ett nummer, inte {args.egenskap!r}.")

    par = kopplingar()
    antal = Counter(q for q, _ in par)
    dubbla = {q for q, n in antal.items() if n > 1}
    if dubbla:
        sys.exit(f"{len(dubbla)} Wikidata-objekt har flera Fornmed-id, t.ex. {sorted(dubbla)[:5]}. "
                 "Varje objekt ska ha ett enda; slå ihop entiteterna först.")
    if args.kontrollera:
        par, rapport = kontrollera(par, args.egenskap)
        for orsak, fall in rapport.items():
            if fall:
                print(f"{len(fall):>6}  {orsak}, t.ex. {fall[:3]}")
    with args.ut.open("w", encoding="utf-8", newline="") as f:
        for q, fid in par:
            f.write(f'{q}\t{args.egenskap}\t"{fid}"\n')
    print(f"{len(par)} påståenden i {args.ut}")


if __name__ == "__main__":
    main()

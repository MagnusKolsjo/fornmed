"""
Skriver Fornmeds register som en katalog för Mix'n'match, där Wikidatas
redaktörer kopplar poster i andra databaser till Wikidata-objekt.

Med i katalogen är personer, platser, institutioner, grupper och begrepp
som ännu saknar Wikidata-id, varken i registret eller i auktoritetslängderna,
och som inte har ersatts av en annan entitet.
Beskrivningen hjälper redaktören att avgöra vem eller vad som avses: för en
plats nutida namn, socken och landskap eller land, för en person registrets
beskrivning eller de år då personen omnämns, och för alla hur många källor
eller påståenden som nämner entiteten.

Filformatet är det som Mix'n'match importerar: tabbseparerat utan
citattecken, med rubrikraden id, name, desc och type och därefter id,
namn, beskrivning och typ (ett Wikidata-objekt). Id:t är Fornmeds
entitets-id, samma som i egenskapen för Fornmeds id om den skapas.

    python mixnmatch.py -o fornmed_mixnmatch.tsv
"""

import argparse
import re
from pathlib import Path

import db
from fragor import _rader

# Wikidata-objekt för entitetens typ
TYP = {
    "person": "Q5",             # människa
    "plats": "Q2221906",        # geografisk plats
    "indelning": "Q56061",      # administrativ territoriell enhet
    "institution": "Q43229",    # organisation
    "grupp": "Q16334295",       # grupp av människor
    "begrepp": "Q151885",       # begrepp
    "ambete": "Q4164871",       # position
}

_OTILLATET = re.compile(r"[\t\r\n]+")


def _ren(text) -> str:
    return _OTILLATET.sub(" ", str(text or "")).strip()


def _ar(heltal: int | None) -> str:
    return str(heltal // 10000) if heltal else ""


def poster() -> list[tuple[str, str, str, str]]:
    p = db._prefix()
    platser = {r["entitet_id"]: r for r in _rader(f"""
        SELECT u.entitet_id, u.nutida_namn, s.namn AS socken, l.namn AS landskap, la.namn AS land
        FROM {p}plats_uppgift u
        LEFT JOIN {p}entitet s ON s.id = u.socken_id
        LEFT JOIN {p}entitet l ON l.id = u.landskap_id
        LEFT JOIN {p}entitet la ON la.id = u.land_id""")}
    kallor = {r["plats_id"]: r["n"] for r in _rader(
        f"SELECT plats_id, count(DISTINCT verk_id) AS n FROM {p}verk_plats GROUP BY plats_id")}
    omnamnanden = {r["subjekt_id"]: r for r in _rader(f"""
        SELECT subjekt_id, count(*) AS n, min(tid_fran) AS fran, max(tid_till) AS till
        FROM {p}pastaende GROUP BY subjekt_id""")}

    ut = []
    for e in _rader(f"""
            SELECT e.id, e.typ, e.namn, e.beskrivning FROM {p}entitet e
            WHERE e.wikidata_id IS NULL
              -- Regenter, biskopar och påvar har ofta sitt Wikidata-id i längden
              AND NOT EXISTS (SELECT 1 FROM {p}auktoritet a
                              WHERE a.person_id = e.id AND a.wikidata_id IS NOT NULL)
              AND NOT EXISTS (SELECT 1 FROM {p}identifiering i
                              WHERE i.entitet_id = e.id AND i.kommentar = 'ersatt_av')
            ORDER BY e.id"""):
        delar = []
        if e["typ"] in ("plats", "indelning"):
            u = platser.get(e["id"], {})
            if u.get("nutida_namn") and u["nutida_namn"] != e["namn"]:
                delar.append(u["nutida_namn"])
            delar += [x for x in (u.get("socken"), u.get("landskap") or u.get("land")) if x]
            if kallor.get(e["id"]):
                delar.append(f"nämns i {kallor[e['id']]} källor i Fornmed")
        else:
            if e.get("beskrivning"):
                delar.append(e["beskrivning"])
            o = omnamnanden.get(e["id"])
            if o:
                ar = "–".join(dict.fromkeys(x for x in (_ar(o["fran"]), _ar(o["till"])) if x))
                delar.append(f"{o['n']} påståenden i Fornmed" + (f", {ar}" if ar else ""))
        ut.append((e["id"], _ren(e["namn"]), _ren("; ".join(delar)), TYP.get(e["typ"], "")))
    return ut


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("-o", "--ut", type=Path, required=True, help="filen att skriva")
    args = tolk.parse_args()
    rader = poster()
    with args.ut.open("w", encoding="utf-8", newline="") as f:
        # Mix'n'match känner igen kolumnerna på rubrikradens namn
        f.write("id\tname\tdesc\ttype\n")
        for rad in rader:
            f.write("\t".join(rad) + "\n")
    print(f"{len(rader)} poster i {args.ut}")


if __name__ == "__main__":
    main()

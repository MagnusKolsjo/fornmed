"""
Läser in påståenden ur en granskningsbar JSON-fil i data/pastaenden/.

Filen är resultatet av en extraktion, oftast gjord av en språkmodell, och
är det som granskas: varje påstående har ett ordagrant citat ur passagens
originaltext. Laddaren kontrollerar allt innan något skrivs:

- att varje citat finns ordagrant i passagen (blanksteg normaliseras),
- att varje predikat finns i vokabulären,
- att varje entitet antingen finns i databasen eller definieras i filen.

Filens format:

    beskrivning     vad som extraherats och hur
    extraherad_av   modell och fil, sparas i pastaende.extraherad_av
    extraktion      'modell' (standard) eller 'manuell'
    passager        förkortning -> prefix för passage-id ("K": "vastgotalagens_konungalangd:")
    entiteter       [id, typ, namn, beskrivning, wikidata-id]
    identifieringar [entitet, identifierad med, bedömning, motivering]
    pastaenden      [passage, subjekt, predikat, objekt, plats, citat, anmärkning?]

Objektet är ett entitets-id, ett fritt värde inlett med '=' ("=dör
sotdöden") eller båda åtskilda av '|' ("begrepp:mansbot|9 marker"). Påståendenas id bildas av passage, predikat, subjekt och
objekt, så att samma påstående får samma id vid varje inläsning. Entiteter
som filen definierar skrivs bara om de inte redan finns; befintliga
entiteter skrivs aldrig över. Alla påståenden och identifieringar läses in
som ogranskade.

    .venv/bin/python pastaenden_fil.py data/pastaenden/vastgotalagens_langder.json
    .venv/bin/python pastaenden_fil.py --kontrollera data/pastaenden/*.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import db
from vokabular import VOKABULAR

log = logging.getLogger(__name__)


def _blank(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _kort(eid: str) -> str:
    """Den del av ett entitets-id som går in i påståendets id."""
    return _slug(eid.split(":", 1)[-1])


def _slug(text: str) -> str:
    """Ett fritt värde i påståendets id; kolon i värdet klipper det inte."""
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def las(fil: Path) -> dict:
    data = json.loads(fil.read_text(encoding="utf-8"))
    prefix = data.get("passager", {})
    pastaenden = []
    for rad in data["pastaenden"]:
        passage, subjekt, predikat, objekt, plats, citat, *anm = rad
        m = re.match(r"([A-Za-zÅÄÖåäö]+)(.+)", passage)
        if m and m.group(1) in prefix:
            passage = prefix[m.group(1)] + m.group(2)
        if objekt and objekt.startswith("="):
            objekt_id, varde = None, objekt[1:]
        elif objekt and "|" in objekt:
            # "begrepp:mansbot|9 marker": både objekt och värde; värdet går in
            # i id:t så att varianter i samma passage hålls isär
            objekt_id, varde = (x.strip() for x in objekt.split("|", 1))
        else:
            objekt_id, varde = objekt, None
        pid = f"{passage}:{predikat}:{_kort(subjekt)}:{_kort(objekt_id) if objekt_id else _slug(varde or '')}"
        if objekt_id and varde:
            pid += ":" + _slug(varde)[:40]
        pastaenden.append({"id": pid, "passage": passage, "subjekt": subjekt, "predikat": predikat,
                           "objekt_id": objekt_id, "objekt_varde": varde, "plats": plats, "citat": citat,
                           "anm": anm[0] if anm else None})
    data["pastaenden"] = pastaenden
    return data


def kontrollera(conn, data: dict) -> list[str]:
    """Fel som hindrar inläsningen; tom lista när filen är korrekt."""
    p, ph = db._prefix(), db._ph()
    fel = []
    predikat = {kod for kat, kod, *_ in VOKABULAR if kat == "predikat"}
    definierade = {e[0] for e in data["entiteter"]}
    cur = conn.cursor()

    passager = sorted({pt["passage"] for pt in data["pastaenden"]})
    texter = {}
    for pid in passager:
        cur.execute(f"SELECT text FROM {p}passage WHERE id = {ph}", (pid,))
        rad = cur.fetchone()
        if rad is None:
            fel.append(f"passagen {pid} finns inte")
        else:
            texter[pid] = _blank(rad[0])

    refererade = set()
    for pt in data["pastaenden"]:
        refererade |= {x for x in (pt["subjekt"], pt["objekt_id"], pt["plats"]) if x}
    for e, med, *_ in data.get("identifieringar", []):
        refererade |= {e, med}
    saknas = refererade - definierade
    if saknas:
        cur.execute(f"SELECT id FROM {p}entitet WHERE id IN ({', '.join([ph] * len(saknas))})", tuple(saknas))
        for eid in sorted(saknas - {r[0] for r in cur.fetchall()}):
            fel.append(f"entiteten {eid} finns varken i databasen eller i filen")

    sedda = set()
    for pt in data["pastaenden"]:
        var = f"{pt['passage']} ({pt['predikat']} {pt['subjekt']})"
        if pt["predikat"] not in predikat:
            fel.append(f"{var}: predikatet finns inte i vokabulären")
        if pt["passage"] in texter and _blank(pt["citat"]) not in texter[pt["passage"]]:
            fel.append(f"{var}: citatet finns inte i passagen: {pt['citat']!r}")
        if pt["id"] in sedda:
            fel.append(f"{var}: påståendet förekommer två gånger ({pt['id']})")
        sedda.add(pt["id"])
    return fel


def ladda(conn, data: dict, fil: Path) -> None:
    p, ph = db._prefix(), db._ph()
    extraherad_av = data.get("extraherad_av") or str(fil)
    extraktion = data.get("extraktion", "modell")
    cur = conn.cursor()
    finns = set()
    if data["entiteter"]:
        cur.execute(f"SELECT id FROM {p}entitet WHERE id IN ({', '.join([ph] * len(data['entiteter']))})",
                    tuple(e[0] for e in data["entiteter"]))
        finns = {r[0] for r in cur.fetchall()}
    nya = [(eid, typ, namn, beskr, wd) for eid, typ, namn, beskr, wd in data["entiteter"] if eid not in finns]

    identifieringar, bedomningar = [], []
    for e, med, varde, motivering in data.get("identifieringar", []):
        iid = f"identifiering:{_kort(e)}:{_kort(med)}"
        identifieringar.append((iid, e, med, None, None))
        bedomningar.append((f"{iid}:bedomning", None, iid, "identifiering", varde, motivering,
                            extraherad_av, extraherad_av))

    with conn:
        cur = conn.cursor()
        # Filen är sanningen: påståenden som tagits bort ur den försvinner
        cur.execute(f"DELETE FROM {p}pastaende WHERE extraherad_av = {ph}", (extraherad_av,))
        cur.execute(f"DELETE FROM {p}bedomning WHERE registrerad_av = {ph} AND identifiering_id IS NOT NULL",
                    (extraherad_av,))
    db.upsert(conn, "entitet", ["id", "typ", "namn", "beskrivning", "wikidata_id"], ["id"], nya)
    namnformer = [(pt["subjekt"], pt["citat"], "fsv", pt["passage"]) for pt in data["pastaenden"]
                  if pt["predikat"] == "innehar_ambete"]
    db.upsert(conn, "entitet_namnform", ["entitet_id", "namnform", "sprak", "passage_id"],
              ["entitet_id", "namnform"], namnformer)
    db.upsert(conn, "identifiering", ["id", "entitet_id", "identifierad_med", "alternativgrupp", "kommentar"],
              ["id"], identifieringar)
    db.upsert(conn, "bedomning",
              ["id", "pastaende_id", "identifiering_id", "aspekt", "varde", "motivering", "bedomare",
               "registrerad_av"], ["id"], bedomningar)
    db.upsert(conn, "pastaende",
              ["id", "passage_id", "subjekt_id", "predikat", "objekt_id", "objekt_varde", "plats_id", "citat",
               "extraktion", "extraherad_av"], ["id"],
              [(pt["id"], pt["passage"], pt["subjekt"], pt["predikat"], pt["objekt_id"], pt["objekt_varde"],
                pt["plats"], pt["citat"], extraktion, extraherad_av) for pt in data["pastaenden"]])
    log.info("%s: %d nya entiteter, %d påståenden, %d identifieringar", fil.name, len(nya),
             len(data["pastaenden"]), len(identifieringar))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Läser in påståenden ur granskningsbara JSON-filer")
    parser.add_argument("filer", nargs="+", type=Path)
    parser.add_argument("--kontrollera", action="store_true", help="kontrollera bara, skriv inget")
    args = parser.parse_args()

    db.initiera_schema()
    conn = db._hamta_db()
    try:
        utfall = 0
        for fil in args.filer:
            data = las(fil)
            fel = kontrollera(conn, data)
            for f in fel:
                log.error("%s: %s", fil.name, f)
            if fel:
                utfall = 1
                continue
            log.info("%s: %d påståenden kontrollerade", fil.name, len(data["pastaenden"]))
            if not args.kontrollera:
                ladda(conn, data, fil)
    finally:
        conn.close()
    sys.exit(utfall)


if __name__ == "__main__":
    main()

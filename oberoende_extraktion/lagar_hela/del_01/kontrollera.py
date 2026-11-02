"""
Kontrollerar en extraktion mot indatafilen. Kräver bara Pythons standardbibliotek.

    python kontrollera.py indata_lagar_stickprov.json utdata_lagar_stickprov.json

Kontrollerar att varje citat står ordagrant i sin passage (blanksteg
normaliseras), att predikaten finns i listan, att varje entitet är en
kandidat i indata eller definieras i utdata, att platsen är flockens
plats och att inget påstående förekommer två gånger. Skriver ut alla fel
och avslutar med kod 1 om något fel finns.
"""

import json
import re
import sys


def blank(text):
    return re.sub(r"\s+", " ", text).strip()


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    indata = json.load(open(sys.argv[1], encoding="utf-8"))
    utdata = json.load(open(sys.argv[2], encoding="utf-8"))
    fel = []

    for nyckel in ("beskrivning", "extraherad_av", "passager", "entiteter", "identifieringar", "pastaenden"):
        if nyckel not in utdata:
            fel.append(f"nyckeln '{nyckel}' saknas i utdata")
    if fel:
        print("\n".join(fel))
        sys.exit(1)

    texter = {pid: blank(p["text"]) for pid, p in indata["passager"].items()}
    predikat = {p["kod"] for p in indata["predikat"]}
    kandidater = {k["id"] for grupp in indata["kandidater"].values() for k in grupp}
    definierade = set()
    for e in utdata["entiteter"]:
        if not (isinstance(e, list) and len(e) == 5):
            fel.append(f"entitet med fel form (ska vara [id, typ, namn, beskrivning, wikidata]): {e}")
            continue
        if e[0] in kandidater:
            fel.append(f"entiteten {e[0]} finns redan bland kandidaterna och ska inte definieras igen")
        if e[1] not in ("person", "plats", "indelning", "grupp", "institution"):
            fel.append(f"entiteten {e[0]} har okänd typ {e[1]!r}")
        definierade.add(e[0])
    kanda = kandidater | definierade
    prefix = utdata["passager"]

    for i in utdata["identifieringar"]:
        if not (isinstance(i, list) and len(i) == 4):
            fel.append(f"identifiering med fel form (ska vara [entitet, identifierad med, bedömning, motivering]): {i}")
            continue
        for eid in i[:2]:
            if eid not in kanda:
                fel.append(f"identifiering: entiteten {eid} är varken kandidat eller definierad")
        if i[2] not in ("saker", "sannolik", "mojlig"):
            fel.append(f"identifiering {i[0]} = {i[1]}: bedömningen ska vara saker, sannolik eller mojlig")

    sedda = set()
    for rad in utdata["pastaenden"]:
        if not (isinstance(rad, list) and len(rad) in (6, 7)):
            fel.append(f"påstående med fel form (ska vara [passage, subjekt, predikat, objekt, plats, citat, anm?]): {rad}")
            continue
        passage, subjekt, pred, objekt, plats, citat = rad[:6]
        m = re.match(r"([A-Za-z]+)(.+)", passage)
        if m and m.group(1) in prefix:
            passage = prefix[m.group(1)] + m.group(2)
        var = f"{rad[0]} {subjekt} {pred} {objekt}"
        if passage not in texter:
            fel.append(f"{var}: passagen {passage} finns inte i indata")
        elif blank(citat) not in texter[passage]:
            fel.append(f"{var}: citatet står inte ordagrant i passagen: {citat!r}")
        if pred not in predikat:
            fel.append(f"{var}: predikatet {pred!r} finns inte i listan")
        objekt_id = None if (objekt or "").startswith("=") else (objekt or "").split("|", 1)[0].strip() or None
        for eid in (subjekt, objekt_id, plats):
            if eid and eid not in kanda:
                fel.append(f"{var}: entiteten {eid} är varken kandidat eller definierad")
        if passage in indata["passager"] and plats != indata["passager"][passage]["plats"]:
            fel.append(f"{var}: platsen ska vara {indata['passager'][passage]['plats']}, inte {plats}")
        if not objekt:
            fel.append(f"{var}: objekt saknas (entitets-id, '=fritt värde' eller 'id|värde')")
        nyckel = (passage, pred, subjekt, (objekt or "").strip())
        if nyckel in sedda:
            fel.append(f"{var}: påståendet förekommer två gånger")
        sedda.add(nyckel)

    if fel:
        print(f"{len(fel)} fel:")
        print("\n".join(fel))
        sys.exit(1)
    print(f"Inga fel: {len(utdata['pastaenden'])} påståenden, {len(definierade)} nya entiteter, "
          f"{len(utdata['identifieringar'])} identifieringar.")


if __name__ == "__main__":
    main()

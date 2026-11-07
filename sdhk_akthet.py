"""
Äkthetsbedömningar ur SDHK: granskad lista, regler för nya brev och inläsning.

SDHK anger i sina anmärkningar när ett brev är förfalskat, misstänkt eller
interpolerat, men anmärkningarna nämner också förfalskning i andra
sammanhang: ett annat brev som är förfalskat, ett mål om förfalskade brev,
litteratur om förfalskaren Nils Rabenius. Ett ordmönster räcker därför inte.

Bedömningarna kommer ur den granskade listan data/sdhk/akthet_granskning.tsv,
där varje brev som SDHK:s anmärkningar ger anledning att bedöma har ett värde
(akta, misstankt, forfalskning, interpolerad eller ingen) och en motivering.
Där SDHK redovisar att forskare är oense står båda bedömningarna, med var sin
bedömare. Listan är tolkad av en språkmodell ur SDHK:s egna formuleringar och
inte granskad av en människa; bedömningarna har därför granskad = false.

Dessutom läses Per-Axel Wiktorssons utslag i Falskt eller äkta i brev från
Sveriges medeltid (Skara 2026) in ur data/sdhk/akthet_wiktorsson.tsv, som en
egen bedömare med brevets nummer i boken och sida i förhandsversionen. Där han och SDHK är oense står
båda bedömningarna.

För brev som inte finns i listan används bara SDHK:s egen klassificering i
datumfältet ("misstänkt förfalskning", "förfalskning") och uttrycket "med
Rabenius interpol." Övriga brev som nämner förfalskning skrivs ut som
kandidater att granska och lägg till i listan.

Användning:
    python sdhk_akthet.py                 # läser in listan och reglerna i databasen
    python sdhk_akthet.py --kandidater    # brev som nämner förfalskning men saknas i listan
"""

import argparse
import csv
import logging
import re
from pathlib import Path

import db
from fragor import _rader

log = logging.getLogger("sdhk_akthet")

GRANSKNING = Path(__file__).parent / "data" / "sdhk" / "akthet_granskning.tsv"
WIKTORSSON = Path(__file__).parent / "data" / "sdhk" / "akthet_wiktorsson.tsv"
WIKTORSSON_BEDOMARE = "P.-A. Wiktorsson"
# Libris: https://libris.kb.se/vhgjnzrvs23r8ph1. Sidnumren är tagna ur den version som
# ligger på academia.edu (2025) och kan skilja sig från den tryckta bokens; brevens
# nummer i boken är desamma.
WIKTORSSON_PUBLIKATION = ("Falskt eller äkta: i brev från Sveriges medeltid, Skara: Skara stiftshistoriska "
                          "sällskap, 2026 (ISBN 978-91-86681-78-4)")
WIKTORSSON_LIBRIS = "https://libris.kb.se/vhgjnzrvs23r8ph1"
SDHK = "Svenskt Diplomatarium (SDHK)"
SDHK_PUBLIKATION = "SDHK-registret, Riksarkivet"
REGISTRERAD_AV = "sdhk_akthet.py"
TOLKNING = " Tolkat av språkmodell ur SDHK:s anmärkningar."

# SDHK:s klassificering i datumfältet, starkaste först
DATUMKLASSER = (
    (re.compile(r"delvis förfalsk", re.I), "interpolerad", "medel"),
    (re.compile(r"(misstänkt|sannolikt|kanske|möjl\w*|förmodligen)[^;]*förfalsk", re.I), "misstankt", "medel"),
    (re.compile(r"förfalsk", re.I), "forfalskning", "medel"),
)
RABENIUS_INTERPOLATION = re.compile(r"Rabenius[’']? interpol", re.I)
KANDIDATORD = re.compile(r"förfalsk|\bfalsk[ta]?\b|interpol|fingerat", re.I)


def _id(mal: str, bedomare: str) -> str:
    """Bedömningens id: SDHK:s egna har slutet 'sdhk', andra bedömarens namn."""
    namn = "sdhk" if bedomare == SDHK else re.sub(r"\W+", "_", bedomare.lower()).strip("_")
    return f"{mal}:akthet:{namn}"


def las_granskning() -> dict[int, list[dict]]:
    """Den granskade listan per SDHK-nummer."""
    per_nr: dict[int, list[dict]] = {}
    with GRANSKNING.open(encoding="utf-8") as fil:
        for rad in csv.DictReader(fil, delimiter="\t"):
            per_nr.setdefault(int(rad["sdhk_nr"]), []).append(rad)
    return per_nr


def bedomningar(nr: int, brev: dict, granskning: dict[int, list[dict]]) -> list[dict]:
    """
    Brevets äkthetsbedömningar som rader för tabellen bedomning (utan
    tomma fält). brev är raden i sdhk_brev; granskning är las_granskning().
    """
    verk_id = f"sdhk:{nr}"
    if nr in granskning:
        ut = []
        for g in granskning[nr]:
            if g["varde"] == "ingen":
                continue
            mal = verk_id if g["mal"] == "verk" else g["mal"]
            ut.append({
                "id": _id(mal, g["bedomare"]),
                "verk_id": verk_id if g["mal"] == "verk" else None,
                "vittne_id": None if g["mal"] == "verk" else g["mal"],
                "aspekt": "akthet", "varde": g["varde"], "sakerhet": g["sakerhet"] or None,
                "bedomare": g["bedomare"], "publikation": g["publikation"] or None,
                "motivering": g["motivering"] + TOLKNING,
            })
        return ut
    datum = brev.get("datum") or ""
    for monster, varde, sakerhet in DATUMKLASSER:
        if monster.search(datum):
            return [{"id": _id(verk_id, SDHK), "verk_id": verk_id, "vittne_id": None, "aspekt": "akthet",
                     "varde": varde, "sakerhet": sakerhet, "bedomare": SDHK, "publikation": SDHK_PUBLIKATION,
                     "motivering": f"SDHK:s datering: {datum}." + TOLKNING}]
    if RABENIUS_INTERPOLATION.search(" ".join(brev.get(f) or "" for f in ("regest", "kommentar", "datum"))):
        return [{"id": _id(verk_id, SDHK), "verk_id": verk_id, "vittne_id": None, "aspekt": "akthet",
                 "varde": "interpolerad", "sakerhet": "hog", "bedomare": SDHK, "publikation": SDHK_PUBLIKATION,
                 "motivering": "SDHK: med Rabenius interpolation." + TOLKNING}]
    return []


def wiktorsson() -> list[dict]:
    """Wiktorssons utslag som rader för tabellen bedomning."""
    ut = []
    with WIKTORSSON.open(encoding="utf-8") as fil:
        for rad in csv.DictReader(fil, delimiter="\t"):
            verk_id = f"sdhk:{rad['sdhk_nr']}"
            ut.append({
                "id": f"{verk_id}:akthet:wiktorsson", "verk_id": verk_id, "vittne_id": None, "aspekt": "akthet",
                "varde": rad["varde"], "sakerhet": "hog", "bedomare": WIKTORSSON_BEDOMARE,
                "publikation": WIKTORSSON_PUBLIKATION, "publikation_id": WIKTORSSON_LIBRIS,
                "sidor": f"{rad['sida']} (förhandsversionen)" if rad["sida"] else None, "ar": 2026,
                "motivering": rad["motivering"],
            })
    return ut


def kandidater(granskning: dict[int, list[dict]]) -> list[tuple[int, str]]:
    """Brev vars anmärkningar nämner förfalskning men som saknas i listan."""
    p = db._prefix()
    ut = []
    for b in _rader(f"SELECT sdhk_nr, datum, regest, kommentar, original, medeltida_avskrift, "
                    f"eftermedeltida_avskrift FROM {p}sdhk_brev"):
        if b["sdhk_nr"] in granskning:
            continue
        text = " | ".join(b[f] or "" for f in ("datum", "regest", "kommentar", "original",
                                                 "medeltida_avskrift", "eftermedeltida_avskrift"))
        traff = KANDIDATORD.search(text)
        if traff:
            ut.append((b["sdhk_nr"], text[max(0, traff.start() - 120):traff.start() + 120].replace("\n", " ")))
    return ut


def las_in() -> dict[str, int]:
    """Ersätter SDHK:s äkthetsbedömningar i databasen med listans och reglernas."""
    p, ph = db._prefix(), db._ph()
    granskning = las_granskning()
    rader = []
    for b in _rader(f"SELECT * FROM {p}sdhk_brev"):
        rader += [{**r, "publikation_id": None, "sidor": None, "ar": None}
                  for r in bedomningar(b["sdhk_nr"], b, granskning)]
    rader += wiktorsson()
    finns = {r["id"] for r in _rader(f"SELECT id FROM {p}verk WHERE id LIKE {ph}", ["sdhk:%"])}
    vittnen = {r["id"] for r in _rader(f"SELECT id FROM {p}vittne WHERE verk_id LIKE {ph}", ["sdhk:%"])}
    saknas = [r["id"] for r in rader if (r["verk_id"] and r["verk_id"] not in finns)
              or (r["vittne_id"] and r["vittne_id"] not in vittnen)]
    if saknas:
        raise ValueError(f"Bedömningar för verk eller vittnen som saknas: {saknas}")
    kolumner = ["id", "verk_id", "vittne_id", "aspekt", "varde", "sakerhet", "bedomare", "publikation",
                "publikation_id", "sidor", "ar", "motivering", "registrerad_av"]
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        # SDHK-importens tidigare bedömningar och listans egna ersätts; andra
        # bedömningar av samma brev (forskning som registrerats för hand) står kvar
        cur.execute(f"DELETE FROM {p}bedomning WHERE aspekt = 'akthet' "
                    f"AND registrerad_av IN ('importera_sdhk.py', {ph})", (REGISTRERAD_AV,))
        borttagna = cur.rowcount
        conn.commit()
        db.upsert(conn, "bedomning", kolumner, ["id"],
                  [tuple(r[k] for k in kolumner[:-1]) + (REGISTRERAD_AV,) for r in rader])
    finally:
        conn.close()
    return {"borttagna": borttagna, "inlasta": len(rader)}


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--kandidater", action="store_true", help="skriv ut brev att granska i stället för att läsa in")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if argument.kandidater:
        for nr, utdrag in kandidater(las_granskning()):
            print(f"SDHK {nr}\t{utdrag}")
        return
    db.initiera_schema()
    log.info("Äkthetsbedömningar ur SDHK: %(borttagna)d borttagna, %(inlasta)d inlästa", las_in())


if __name__ == "__main__":
    main()

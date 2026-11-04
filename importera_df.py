"""
Importerar Diplomatarium Fennicum ur data/raw/df (hamta_df.py) till databasen.

Datamängden från Kansallisarkisto (CC0) ger brevtext och grunduppgifter, webbplatsen
regester, utfärdare och datum. Regester ur Auctoritate Papae (2012) tas inte med, eftersom
de kommer ur ett nutida verk. Brev som SDHK anger som "FMU nr N" och som har samma år som
DF N får SDHK-numret i verkets extra-fält. Importen kan köras om.

Användning:
    python importera_df.py
"""

import gzip
import json
import logging
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import db
from importera_sdhk import tolka_datum

log = logging.getLogger("importera_df")

KATALOG = Path(__file__).parent / "data" / "raw" / "df"
SIDA = "https://df.kansallisarkisto.fi/document/{}"
SPRAK = {"latina": "lat", "ruotsi": "swe", "saksa": "deu", "venaja": "rus", "islanti": "isl"}
NUTIDA_REGEST = "Auctoritate Papae"
FMU = re.compile(r"FMU\s+(?:nr\s+)?(\d+)")


def _falt(sida: str, namn: str) -> str:
    traff = re.search(rf'id="doc-content-{namn}"[^>]*>(.*?)</div>', sida, re.S)
    if not traff:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<!--.*?-->|<[^>]+>", " ", traff.group(1), flags=re.S))).strip()


def datum(text: str, ar: str) -> tuple:
    """Webbplatsens datum (d.m.åååå, m.åååå, åååå) som SDHK:s form; annat står kvar som anmärkning."""
    if traff := re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text):
        return tolka_datum(f"{traff[3]}{int(traff[2]):02}{int(traff[1]):02}")
    if traff := re.fullmatch(r"(\d{1,2})\.(\d{4})", text):
        return tolka_datum(f"{traff[2]}{int(traff[1]):02}00")
    if re.fullmatch(r"\d{4}", ar or ""):
        edtf, fran, till, _ = tolka_datum(f"{ar}0000")
        return edtf, fran, till, None if text == ar or text.startswith("--") else text
    return None, None, None, text or None


def _sdhk_per_fmu() -> dict[int, list[tuple[int, int | None]]]:
    p = db._prefix()
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(f"""SELECT b.sdhk_nr, b.tryck, v.datering_fran FROM {p}sdhk_brev b
                        JOIN {p}verk v ON v.id = 'sdhk:' || b.sdhk_nr WHERE b.tryck LIKE '%FMU%'""")
        per_fmu: dict[int, list] = {}
        for nr, tryck, fran in cur.fetchall():
            for fmu in FMU.findall(tryck):
                per_fmu.setdefault(int(fmu), []).append((nr, fran // 10000 if fran else None))
        return per_fmu
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db.initiera_schema()
    poster = json.loads((KATALOG / "diplomatarium-fennicum.json").read_text(encoding="utf-8"))
    regester = {r["df"]: r for r in map(json.loads, (KATALOG / "regester.jsonl").open(encoding="utf-8"))}
    per_fmu = _sdhk_per_fmu()
    verk, passager, kopplade, utelamnade = [], [], 0, 0
    for post in poster:
        nr = int(post["df"])
        sida = gzip.decompress((KATALOG / "sidor" / f"{nr}.html.gz").read_bytes()).decode("utf-8", "replace")
        edtf, fran, till, anm = datum(_falt(sida, "date"), post["dating_start_year"])
        sprak = [k for s in post["language"].split(",") if (k := SPRAK.get(s.strip()))]
        ar = fran // 10000 if fran else None
        sdhk = [n for n, a in per_fmu.get(nr, []) if a == ar and ar]
        kopplade += bool(sdhk)
        rad = regester.get(nr) or {}
        verk_id = f"df:{nr}"
        verk.append((verk_id, "df", f"DF {nr}", _falt(sida, "issuer") or None, "diplom", db.sprakvarde(sprak),
                     post["issuingplace"] or None, edtf, fran, till, anm, SIDA.format(nr),
                     json.dumps({"land": post["issuingplacecountry"] or None, "amnesord": post["indexterm"] or None,
                                 "regest_kalla": rad.get("kalla") or None, "sdhk": sdhk}, ensure_ascii=False)))
        if rad.get("regest"):
            if NUTIDA_REGEST in (rad.get("kalla") or ""):
                utelamnade += 1
            else:
                passager.append((f"{verk_id}:regest", verk_id, None, "regest", f"DF {nr}", 0, "swe", rad["regest"]))
        if post["transcript"].strip():
            passager.append((f"{verk_id}:originaltext", verk_id, None, "originaltext", f"DF {nr}", 1,
                             sprak[0] if len(sprak) == 1 else None, post["transcript"]))
    conn = db._hamta_db()
    try:
        db.upsert(conn, "kallsamling", ["id", "namn", "utgivare", "url", "licens", "version", "importerad"], ["id"],
                  [("df", "Diplomatarium Fennicum", "Kansallisarkisto", "https://df.kansallisarkisto.fi/",
                    "CC0 (brevtext och grunduppgifter); regesterna hämtade från webbplatsen, som inte anger licens",
                    datetime.now(timezone.utc).date().isoformat(), datetime.now(timezone.utc).isoformat(timespec="seconds"))])
        db.upsert(conn, "verk", ["id", "kallsamling_id", "titel", "upphov", "genre", "sprak", "utfardandeort", "datering_edtf",
                                 "datering_fran", "datering_till", "datering_anm", "extern_url", "extra"], ["id"], verk)
        db.upsert(conn, "passage", ["id", "verk_id", "utgava_id", "typ", "adress", "ordning", "sprak", "text"], ["id"], passager)
    finally:
        conn.close()
    log.info("%d brev, %d passager, %d kopplade till SDHK, %d regester utelämnade", len(verk), len(passager), kopplade, utelamnade)


if __name__ == "__main__":
    main()

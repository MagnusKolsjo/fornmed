"""
Hämtar Diplomatarium Fennicum till data/raw/df, utan att läsa in något i databasen.

Datamängden från Kansallisarkisto (CC0) ger brevtext och grunduppgifter. Regester och
övriga uppgifter finns bara på webbplatsen, så varje brevsida sparas komprimerad och
kan tolkas om utan att hämtas igen. Hämtningen tar en sida i sekunden och kan avbrytas
och köras om; sidor som redan finns hoppas över.

Användning:
    python hamta_df.py
"""

import gzip
import json
import logging
import re
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

log = logging.getLogger("hamta_df")

KATALOG = Path(__file__).parent / "data" / "raw" / "df"
DATAMANGD = "https://huggingface.co/datasets/Kansallisarkisto/Diplomatarium-Fennicum/resolve/main/diplomatarium-fennicum.json"
SIDA = "https://df.kansallisarkisto.fi/document/{}"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
PAUS = 1.0

REGEST = re.compile(r'<div id="doc-content-regest"([^>]*)>(.*?)</div>', re.S)
TITEL = re.compile(r'title="([^"]*)"')
PLATSSIDA = "https://df.kansallisarkisto.fi/places/"
PLATSRAD = re.compile(r"<tr>(.*?)</tr>", re.S)
PLATSCELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _hamta(url: str) -> bytes:
    begaran = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(begaran, timeout=60) as svar:
        return svar.read()


def regest(sida: str) -> dict | None:
    """Regesten som sidan visar, med uppgiften om varifrån den kommer."""
    traff = REGEST.search(sida)
    if not traff:
        return None
    text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", traff.group(2)))).strip()
    kalla = TITEL.search(traff.group(1))
    return {"regest": text, "kalla": unescape(kalla.group(1)) if kalla else ""}


def platsregister(sida: str) -> list[dict]:
    """Platsregistret: namn, precisering, annat namn, koordinater, land och antal brev."""
    platser = []
    for rad in PLATSRAD.findall(sida):
        celler = [unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in PLATSCELL.findall(rad)]
        if len(celler) == 8 and celler[0].isdigit():
            platser.append({"namn": celler[1], "precisering": celler[2], "annat_namn": celler[3],
                            "lat": float(celler[4]) if celler[4] else None,
                            "lon": float(celler[5]) if celler[5] else None,
                            "land": celler[6], "antal": int(celler[7] or 0)})
    return platser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sidor = KATALOG / "sidor"
    sidor.mkdir(parents=True, exist_ok=True)
    fil = KATALOG / "diplomatarium-fennicum.json"
    if not fil.exists():
        fil.write_bytes(_hamta(DATAMANGD))
    nummer = sorted({int(p["df"]) for p in json.loads(fil.read_text(encoding="utf-8"))})
    log.info("%d brev", len(nummer))

    fel = []
    for i, nr in enumerate(nummer, start=1):
        mal = sidor / f"{nr}.html.gz"
        if mal.exists():
            continue
        try:
            mal.write_bytes(gzip.compress(_hamta(SIDA.format(nr))))
        except (urllib.error.URLError, TimeoutError) as e:
            log.warning("DF %d: %s", nr, e)
            fel.append(nr)
            time.sleep(PAUS * 30)
        time.sleep(PAUS)
        if i % 500 == 0:
            log.info("%d av %d", i, len(nummer))

    with (KATALOG / "regester.jsonl").open("w", encoding="utf-8") as f:
        for nr in nummer:
            mal = sidor / f"{nr}.html.gz"
            if mal.exists():
                rad = regest(gzip.decompress(mal.read_bytes()).decode("utf-8", "replace"))
                f.write(json.dumps({"df": nr, **(rad or {"regest": None, "kalla": None})}, ensure_ascii=False) + "\n")
    platser = platsregister(_hamta(PLATSSIDA).decode("utf-8", "replace"))
    (KATALOG / "platser.json").write_text(json.dumps(platser, ensure_ascii=False, indent=0), encoding="utf-8")
    log.info("%d platser i registret", len(platser))
    log.info("Klart. Misslyckade: %d %s", len(fel), fel[:20])


if __name__ == "__main__":
    main()

"""
Hämtar ortnamnsposterna i Isofs Ortnamnsregister till data/raw/isof, utan att läsa in dem.

API:et stoppar bladningen efter 10 000 poster, så hämtningen delas upp per län och land.
En grupp som är för stor delas vidare efter namnets början. Varje grupp sparas i en egen
komprimerad fil och hoppas över vid omkörning. Poster med samma id kan förekomma flera
gånger och slås ihop när filerna läses. Underlagen (belägg, tolkningar m.m.) hämtas inte här.

Användning:
    python hamta_isof.py
"""

import gzip
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger("hamta_isof")

KATALOG = Path(__file__).parent / "data" / "raw" / "isof"
API = "https://placenameservice.isof.se/v1/"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
SIDSTORLEK = 1000
DJUPGRANS = 10000
# Inga jokertecken: * ger hela gruppen igen
TECKEN = "abcdefghijklmnopqrstuvwxyzåäöæøüé0123456789 -'.,()"
PAUS = 0.3


def _hamta(sokvag: str, **param) -> dict | list:
    url = API + sokvag + ("?" + urllib.parse.urlencode(param) if param else "")
    begaran = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for forsok in range(5):
        try:
            with urllib.request.urlopen(begaran, timeout=120) as svar:
                return json.load(svar)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise
            log.warning("%s: %s", url, e)
            time.sleep(30 * (forsok + 1))
        except (urllib.error.URLError, TimeoutError) as e:
            log.warning("%s: %s", url, e)
            time.sleep(30 * (forsok + 1))
    raise RuntimeError(url)


def _sidor(fil, filter_: dict) -> int:
    antal, sida = 0, 1
    while True:
        svar = _hamta("place-names", **filter_, **{"page-size": SIDSTORLEK, "page-number": sida})
        for rad in svar["place_names"]:
            fil.write(json.dumps(rad, ensure_ascii=False) + "\n")
        antal += len(svar["place_names"])
        if antal >= svar["count"] or not svar["place_names"]:
            return antal
        sida += 1
        time.sleep(PAUS)


def _dela(fil, filter_: dict, borjan: str = "") -> tuple[int, int]:
    """Hämtar en grupp, uppdelad efter namnets början när den är för stor. Returnerar (väntat, hämtat)."""
    urval = {**filter_, **({"place-name": borjan, "place-name-search-type": "BeginsWith"} if borjan else {})}
    vantat = _hamta("place-names", **urval, **{"page-size": 1})["count"]
    time.sleep(PAUS)
    if vantat == 0:
        return 0, 0
    if vantat <= DJUPGRANS or len(borjan) >= 6:
        return vantat, _sidor(fil, urval)
    hamtat = sum(_dela(fil, filter_, borjan + t)[1] for t in TECKEN)
    return vantat, hamtat


def hamta_grupp(namn: str, **filter_) -> int:
    """Alla poster i en grupp till en egen fil. Returnerar antalet."""
    mal = KATALOG / f"{namn}.jsonl.gz"
    if mal.exists():
        return 0
    tillfallig = mal.with_suffix(".tmp")
    with gzip.open(tillfallig, "wt", encoding="utf-8") as f:
        vantat, hamtat = _dela(f, filter_)
    tillfallig.rename(mal)
    log.info("%s: väntat %d, hämtat %d", namn, vantat, hamtat)
    return hamtat


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    KATALOG.mkdir(parents=True, exist_ok=True)
    summa = 0
    for lan in _hamta("geo-reference/counties"):
        summa += hamta_grupp(f"lan_{lan['id']}", **{"county-id": lan["id"]})
    for land in _hamta("place-names/country-area-filters"):
        if land.get("name") != "Sverige":
            summa += hamta_grupp(f"land_{land['id']}", **{"country-area-filter-id": land["id"]})
    log.info("Klart: %d poster i denna körning", summa)


if __name__ == "__main__":
    main()

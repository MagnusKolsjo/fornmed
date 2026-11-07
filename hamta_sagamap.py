"""
Hämtar platserna i Icelandic Saga Map (sagamap.hi.is, Emily Lethbridge m.fl., CC BY-NC 4.0)
till data/raw/sagamap/platser.json, utan att läsa in något.

Kartan visar sagornas platser saga för saga; varje plats har namn, koordinater, typ och sysselkod.
Samma plats förekommer i flera sagor och slås ihop på sitt id.

Användning:
    python hamta_sagamap.py
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger("hamta_sagamap")

FIL = Path(__file__).parent / "data" / "raw" / "sagamap" / "platser.json"
API = "https://sagamap.hi.is/data/data.php"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
TOMMA_I_RAD = 15


def _hamta(saga: int) -> list[dict]:
    url = API + "?" + urllib.parse.urlencode({"a": "getsagaplaces", "saga": saga})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as svar:
        text = svar.read().decode("utf-8")
    return json.loads(text).get("places", []) if text.strip() else []


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    platser: dict[str, dict] = {}
    saga, tomma = 1, 0
    while tomma < TOMMA_I_RAD:
        try:
            lista = _hamta(saga)
        except Exception as e:
            log.warning("saga %d: %s", saga, e)
            lista = []
        tomma = 0 if lista else tomma + 1
        for p in lista:
            if p["id"] in platser:
                platser[p["id"]]["sagas"].update(p.get("sagas") or {})
            else:
                platser[p["id"]] = {**p, "sagas": dict(p.get("sagas") or {})}
        saga += 1
        time.sleep(0.3)
    FIL.parent.mkdir(parents=True, exist_ok=True)
    FIL.write_text(json.dumps(list(platser.values()), ensure_ascii=False), encoding="utf-8")
    log.info("%d platser ur %d sagor", len(platser), saga - TOMMA_I_RAD - 1)


if __name__ == "__main__":
    main()

"""
Hämtar Kartverkets ortnamn (Sentralt stedsnavnregister) för Diplomatarium Norvegicums orter
till data/raw/ssr, utan att läsa in något.

Varje ortnamn hämtas en gång och sparas i ssr.jsonl; en ny körning hämtar bara de namn som
saknas. platser.py använder bara kommuner, socknar, kyrkor, bygder, tätorter och byar.

Användning:
    python hamta_ssr.py
"""

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from fragor import _rader

log = logging.getLogger("hamta_ssr")

FIL = Path(__file__).parent / "data" / "raw" / "ssr" / "ssr.jsonl"
API = "https://ws.geonorge.no/stedsnavn/v1/sted"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
PAUS = 0.25


def sokform(namn: str) -> str | None:
    """Ortnamnet som det slås upp: utan hakparenteser och frågetecken; "uden Sted" är ingen ort."""
    namn = re.sub(r"[\[\]?\"'”“*+<>=]", "", namn or "").strip(" .,:;-")
    if not namn or re.fullmatch(r"(?i)ud?ten sted|uden sted|udat\.?", namn):
        return None
    return namn


def hamta(namn: str) -> list[dict]:
    fraga = urllib.parse.urlencode({"sok": namn, "fuzzy": "false", "treffPerSide": 100, "utkoordsys": 4258})
    begaran = urllib.request.Request(f"{API}?{fraga}", headers={"User-Agent": USER_AGENT})
    for forsok in range(4):
        try:
            with urllib.request.urlopen(begaran, timeout=60) as svar:
                return json.load(svar).get("navn", [])
        except urllib.error.HTTPError as e:
            # Ett namn som tjänsten inte godtar blir inte bättre av fler försök
            if e.code < 500:
                log.warning("%s: %s", namn, e)
                return []
            time.sleep(10 * (forsok + 1))
        except (urllib.error.URLError, TimeoutError) as e:
            log.warning("%s: %s", namn, e)
            time.sleep(10 * (forsok + 1))
    return []


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FIL.parent.mkdir(parents=True, exist_ok=True)
    klara = {json.loads(r)["namn"] for r in FIL.open(encoding="utf-8")} if FIL.exists() else set()
    namn = set()
    for r in _rader("SELECT DISTINCT utfardandeort FROM fornmed.verk WHERE kallsamling_id = 'dn' AND utfardandeort IS NOT NULL"):
        for del_ in re.split(r",|\(|\)| i | paa | på ", r["utfardandeort"]):
            if (s := sokform(del_)):
                namn.add(s)
    att_hamta = sorted(namn - klara)
    log.info("%d namn, %d att hämta", len(namn), len(att_hamta))
    with FIL.open("a", encoding="utf-8") as f:
        for i, n in enumerate(att_hamta, 1):
            f.write(json.dumps({"namn": n, "traffar": hamta(n)}, ensure_ascii=False) + "\n")
            f.flush()
            time.sleep(PAUS)
            if i % 250 == 0:
                log.info("%d av %d", i, len(att_hamta))
                f.flush()


if __name__ == "__main__":
    main()

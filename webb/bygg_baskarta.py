"""
Bygger webbplatsens baskarta ur Natural Earth: länder och sjöar som GeoJSON.

Kartan på söksidan och registrets sidor ritas med Leaflet ur den här filen i
stället för kartbilder från en annan server, så att ett besök inte skickar
något till tredje part. Natural Earth är fri från upphovsrätt (public
domain).

Två filer byggs. baskarta_varld.json är hela jorden i skala 1:50 miljoner,
så att orter som Rom, Jerusalem eller Bagdad syns. baskarta.json är Europa i
skala 1:10 miljoner, som kartan lägger ovanpå när man zoomar in. Linjerna
förenklas (Douglas–Peucker) och koordinaterna rundas, vilket inte syns vid
respektive skala men gör filerna en bråkdel så stora. Europafilen klipps till
en ruta som är större än Europa, så att klippkanten ligger utanför det man
zoomar in på.

Användning (filerna hämtas från github.com/nvkelso/natural-earth-vector):
    python webb/bygg_baskarta.py ne_50m_admin_0_countries.geojson ne_50m_lakes.geojson \
        ne_10m_admin_0_countries.geojson ne_10m_lakes.geojson
"""

import argparse
import json
from pathlib import Path

STATISKT = Path(__file__).parent / "sidor" / "static" / "sidor"
UT_VARLD = STATISKT / "baskarta_varld.json"
UT_EUROPA = STATISKT / "baskarta.json"
HELA_JORDEN = (-180.0, -90.0, 180.0, 90.0)

# Västra längd, södra bredd, östra längd, norra bredd
RUTA = (-40.0, 25.0, 70.0, 76.0)
# (största avvikelse i grader när linjerna förenklas, decimaler) per fil
VARLD = (0.03, 2)
EUROPA = (0.004, 3)

# Sjöar mindre än så här (i kvadratgrader) tas inte med
MINSTA_SJO = 0.002


def _klipp(ring: list, ruta: tuple) -> list:
    """Sutherland–Hodgman: ringen klippt mot rutan."""
    vast, syd, ost, nord = ruta
    kanter = [
        (lambda p: p[0] >= vast, lambda a, b: _skarning_x(a, b, vast)),
        (lambda p: p[0] <= ost, lambda a, b: _skarning_x(a, b, ost)),
        (lambda p: p[1] >= syd, lambda a, b: _skarning_y(a, b, syd)),
        (lambda p: p[1] <= nord, lambda a, b: _skarning_y(a, b, nord)),
    ]
    punkter = ring
    for innanfor, skarning in kanter:
        if not punkter:
            break
        ut = []
        for i, p in enumerate(punkter):
            foregaende = punkter[i - 1]
            if innanfor(p):
                if not innanfor(foregaende):
                    ut.append(skarning(foregaende, p))
                ut.append(p)
            elif innanfor(foregaende):
                ut.append(skarning(foregaende, p))
        punkter = ut
    return punkter


def _skarning_x(a: list, b: list, x: float) -> list:
    t = (x - a[0]) / (b[0] - a[0])
    return [x, a[1] + t * (b[1] - a[1])]


def _skarning_y(a: list, b: list, y: float) -> list:
    t = (y - a[1]) / (b[1] - a[1])
    return [a[0] + t * (b[0] - a[0]), y]


def _douglas_peucker(punkter: list, tolerans: float) -> list:
    """Punkterna som behövs för att linjen ska avvika högst tolerans från originalet."""
    if len(punkter) < 3:
        return punkter
    behall = [False] * len(punkter)
    behall[0] = behall[-1] = True
    stack = [(0, len(punkter) - 1)]
    while stack:
        forsta, sista = stack.pop()
        (x1, y1), (x2, y2) = punkter[forsta], punkter[sista]
        dx, dy = x2 - x1, y2 - y1
        langd = (dx * dx + dy * dy) ** 0.5
        storst, index = 0.0, None
        for i in range(forsta + 1, sista):
            x, y = punkter[i]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / langd if langd else ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
            if d > storst:
                storst, index = d, i
        if index is not None and storst > tolerans:
            behall[index] = True
            stack += [(forsta, index), (index, sista)]
    return [p for p, b in zip(punkter, behall) if b]


def _avrunda(ring: list, decimaler: int) -> list:
    ut = []
    for x, y in ring:
        p = [round(x, decimaler), round(y, decimaler)]
        if not ut or p != ut[-1]:
            ut.append(p)
    if ut and ut[0] != ut[-1]:
        ut.append(ut[0])
    return ut


def _area(ring: list) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))) / 2


def _polygoner(geometri: dict) -> list:
    if geometri["type"] == "Polygon":
        return [geometri["coordinates"]]
    if geometri["type"] == "MultiPolygon":
        return geometri["coordinates"]
    return []


def forenkla(sokvag: Path, ruta: tuple, noggrannhet: tuple, minsta_area: float = 0.0) -> list:
    """Varje polygon klippt, förenklad, avrundad och utan ringar som blir för små."""
    tolerans, decimaler = noggrannhet
    polygoner = []
    for feature in json.loads(sokvag.read_text(encoding="utf-8"))["features"]:
        if not feature.get("geometry"):
            continue
        for polygon in _polygoner(feature["geometry"]):
            ringar = []
            for nr, ring in enumerate(polygon):
                klippt = _avrunda(_douglas_peucker(_klipp(ring, ruta), tolerans), decimaler)
                if len(klippt) >= 4 and _area(klippt) > minsta_area:
                    ringar.append(klippt)
                elif nr == 0:
                    # Utan yttre ring skulle hålen bli egna ytor
                    break
            if ringar:
                polygoner.append(ringar)
    return polygoner


def _skriv(sokvag: Path, lander: list, sjoar: list) -> None:
    karta = {"kalla": "Natural Earth (public domain), naturalearthdata.com",
             "land": {"type": "MultiPolygon", "coordinates": lander},
             "sjoar": {"type": "MultiPolygon", "coordinates": sjoar}}
    sokvag.write_text(json.dumps(karta, separators=(",", ":")), encoding="utf-8")
    print(f"{sokvag}: {sokvag.stat().st_size // 1024} kB, {len(lander)} landpolygoner, {len(sjoar)} sjöar")


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("lander50", type=Path, help="ne_50m_admin_0_countries.geojson")
    tolk.add_argument("sjoar50", type=Path, help="ne_50m_lakes.geojson")
    tolk.add_argument("lander10", type=Path, help="ne_10m_admin_0_countries.geojson")
    tolk.add_argument("sjoar10", type=Path, help="ne_10m_lakes.geojson")
    argument = tolk.parse_args()
    _skriv(UT_VARLD, forenkla(argument.lander50, HELA_JORDEN, VARLD),
           forenkla(argument.sjoar50, HELA_JORDEN, VARLD, MINSTA_SJO * 50))
    _skriv(UT_EUROPA, forenkla(argument.lander10, RUTA, EUROPA),
           forenkla(argument.sjoar10, RUTA, EUROPA, MINSTA_SJO))


if __name__ == "__main__":
    main()

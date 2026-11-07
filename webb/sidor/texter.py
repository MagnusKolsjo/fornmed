"""
Källtexterna som webbsidor, hämtade från Fornmeds API.

Texterna läggs inte in i Wagtail. Källförteckningens sida svarar också på
/kallor/verk/<verk_id>/, hämtar verkets versioner, delar och text som JSON
från söktjänstens API och ritar dem med mallen sidor/verk.html. Webbplatsen
visar alltså samma text, med samma språkversioner och samma märkning av
maskinöversättningar, som API:et och MCP-servern.

API:et nås på servern direkt, utan nginx (WEBB_API_INTERN_URL). Svaren
cachas en stund; datan ändras bara vid leveranser.

Stora verk visas del för del, så att en sida inte blir flera megabyte.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

# Över så här många tecken visas ett verk med delar en del i taget
MAX_TECKEN_PA_SIDAN = 300_000
CACHE_SEKUNDER = 300


class TextFel(Exception):
    """API:et svarade med fel. `kod` är HTTP-statusen, `detaljer` svaret."""

    def __init__(self, kod: int, detaljer: dict) -> None:
        super().__init__(detaljer.get("fel", f"HTTP {kod}"))
        self.kod = kod
        self.detaljer = detaljer


# Brevsamlingar vars verk har id utan verk: framför, t.ex. sdhk:1000 och dn:1:1
BREVSAMLINGAR = ("sdhk", "df", "dn")


def adress(verk_id: str) -> str:
    """Verkets id som del av en webbadress: verk:lag:aldre_vastgotalagen blir lag-aldre_vastgotalagen.

    Wagtail släpper bara igenom bokstäver, siffror, understreck och bindestreck
    i adressens delar. Verkens id har inga bindestreck, så kolon kan skrivas
    som bindestreck och adressen göras om till id. Breven har id som sdhk:1000
    utan verk: och får adresser som sdhk-1000.
    """
    return verk_id.removeprefix("verk:").replace(":", "-")


def verk_id(adress_: str) -> str:
    """Motsatsen till adress()."""
    id_ = adress_.replace("-", ":")
    return id_ if id_.split(":", 1)[0] in BREVSAMLINGAR else "verk:" + id_


def _hamta(sokvag: str, **param) -> dict | list:
    param = {k: v for k, v in param.items() if v not in (None, "")}
    url = settings.API_INTERN_URL.rstrip("/") + sokvag
    if param:
        url += "?" + urllib.parse.urlencode(param)
    nyckel = "api:" + url
    svar = cache.get(nyckel)
    if svar is not None:
        return svar
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            svar = json.load(r)
    except urllib.error.HTTPError as fel:
        try:
            detaljer = json.load(fel)
        except Exception:
            detaljer = {}
        raise TextFel(fel.code, detaljer) from fel
    except (urllib.error.URLError, TimeoutError) as fel:
        log.warning("API:et svarar inte: %s", fel)
        raise TextFel(503, {"fel": "Texten kan inte hämtas just nu."}) from fel
    cache.set(nyckel, svar, CACHE_SEKUNDER)
    return svar


def _vag(verk_id: str) -> str:
    return "/v1/verk/" + urllib.parse.quote(verk_id, safe=":")


def verkets_sida(verk_id: str, utgava: str | None, del_: str | None, parallellt: str | None) -> dict:
    """Allt som mallen behöver för ett verk: versioner, delar och text."""
    versioner = _hamta(_vag(verk_id) + "/versioner")
    if not versioner:
        raise TextFel(404, {"fel": "Verket har ingen text."})
    vald = next((v for v in versioner if v["utgava"] == utgava), None) or versioner[0]

    delar = _hamta(_vag(verk_id) + "/delar", utgava=vald["utgava"])["delar"]
    stort = sum(v["tecken"] for v in versioner if v["utgava"] == vald["utgava"]) > MAX_TECKEN_PA_SIDAN
    # Ett stort verk med delar visas en del i taget; utan delar visas det helt
    if delar and stort and not del_:
        del_ = delar[0]["del"]
    if del_ and del_ not in {d["del"] for d in delar}:
        del_ = None

    # Parallell text: valt språk mot en annan version, t.ex. fornsvenska och svenska
    parallell = None
    if parallellt:
        andra = next((v for v in versioner if v["utgava"] == parallellt), None)
        if andra and _sprak(andra) != _sprak(vald):
            try:
                parallell = _hamta(
                    _vag(verk_id) + (f"/delar/{urllib.parse.quote(del_)}/text" if del_ else "/text"),
                    sprak=f"{_sprak(vald)},{_sprak(andra)}", parallellt="true")
            except TextFel as fel:
                if fel.kod not in (404, 406):
                    raise

    if parallell is None:
        if del_:
            text = _hamta(_vag(verk_id) + f"/delar/{urllib.parse.quote(del_)}/text", utgava=vald["utgava"])
        else:
            text = _hamta(_vag(verk_id) + "/text", utgava=vald["utgava"])
    else:
        text = None

    namn = [d["del"] for d in delar]
    plats = namn.index(del_) if del_ in namn else None
    return {
        "foregaende": namn[plats - 1] if plats else None,
        "nasta": namn[plats + 1] if plats is not None and plats + 1 < len(namn) else None,
        "verk": (text or parallell)["verk"],
        "versioner": versioner,
        "vald": vald,
        "version": text["version"] if text else parallell["versioner"][_sprak(vald)],
        "delar": delar,
        "del": del_,
        "del_for_del": bool(delar and stort),
        "text": text,
        "parallell": parallell,
        "parallella_versioner": [v for v in versioner if _sprak(v) and _sprak(v) != _sprak(vald)
                                 and v["roll"] == vald["roll"]],
        "parallellt": parallellt if parallell else None,
    }


def _sprak(version: dict) -> str | None:
    sprak = version.get("sprak")
    return sprak if isinstance(sprak, str) else None

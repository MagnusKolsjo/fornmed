"""
Uppgifter ur Fornmeds databas: källförteckningen, leveranserna och omfånget.

Databasen läses med söktjänstens skrivskyddade roll genom anslutningen
"fornmed". Svaren cachas per leverans: de ändras bara när en ny kopia av
databasen har lästs in, och då har leveranstabellen fått en ny rad.

Går databasen inte att nå visas sidorna ändå, med tomma listor, så att ett
fel i söktjänstens databas inte tar ner webbplatsen.
"""

import json
import logging
import re
import unicodedata

from django.core.cache import cache
from django.db import connections

log = logging.getLogger(__name__)

SPRAK = {
    "lat": "latin", "fsv": "fornsvenska", "non": "fornvästnordiska", "swe": "svenska",
    "dan": "danska", "eng": "engelska", "deu": "tyska", "nor": "norska", "isl": "isländska",
    "ara": "arabiska", "ang": "fornengelska", "fra": "franska", "ita": "italienska",
    "grc": "grekiska", "gml": "medellågtyska", "fin": "finska", "nld": "nederländska",
}

TYPER = {
    "original": "original",
    "oversattning": "översättning",
    "maskinoversattning": "maskinöversättning",
    "maskintranskription": "maskintranskription",
    "regest": "regest",
}

# Rubriker för leveransernas ändringar per tabell
TABELLER = {
    "verk": "verk", "passage": "passager", "utgava": "utgåvor", "entitet": "entiteter",
    "pastaende": "påståenden", "bedomning": "bedömningar", "identifiering": "identifieringar",
    "term": "termer", "ordboksartikel": "ordboksartiklar", "auktoritet": "personer i auktoritetslängderna",
}

# Brev och runinskrifter är tusentals verk var och redovisas som en källa var
SAMLADE = {
    "sdhk": "Medeltidsbrev i Svenskt Diplomatariums huvudkartotek (SDHK)",
    "rundata": "Runinskrifter i Rundata",
}

# Hänvisningen som källan kräver varje gång dess uppgifter visas. Samnordisk
# runtextdatabas ska anges med namn och med just den här adressen.
HANVISNINGAR = {
    "rundata": [
        ("Rundata.info, Stockholms universitet", "https://www.rundata.info/"),
        ("Samnordisk runtextdatabas, Uppsala universitet", "http://www.nordiska.uu.se/forskn/samnord.htm"),
    ],
    "sdhk": [
        ("Svenskt Diplomatariums huvudkartotek, Riksarkivet", "https://sok.riksarkivet.se/sdhk"),
    ],
}


class FornmedRouter:
    """Webbplatsens modeller hör till webbplatsens databas, aldrig till Fornmeds."""

    def db_for_read(self, model, **hints):
        return "default"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_migrate(self, db, app_label, **hints):
        return db == "default"


def _rader(sql: str, param: tuple = ()) -> list[dict]:
    with connections["fornmed"].cursor() as cur:
        cur.execute(sql, param)
        kolumner = [k[0] for k in cur.description]
        return [dict(zip(kolumner, r)) for r in cur.fetchall()]


def _senaste_leverans() -> str:
    try:
        rader = _rader("SELECT id FROM fornmed.leverans ORDER BY tidpunkt DESC LIMIT 1")
    except Exception as fel:
        log.warning("Fornmeds databas svarar inte: %s", fel)
        return "otillganglig"
    return rader[0]["id"] if rader else "ingen"


def _cachad(namn: str, berakna, tom):
    """Värdet för den senaste leveransen; beräknas en gång per leverans och process.

    `tom` returneras när databasen inte går att nå.
    """
    leverans = _senaste_leverans()
    if leverans == "otillganglig":
        return tom
    nyckel = f"fornmed:{namn}:{leverans}"
    varde = cache.get(nyckel)
    if varde is None:
        try:
            varde = berakna()
        except Exception as fel:
            log.warning("Kunde inte läsa %s ur Fornmeds databas: %s", namn, fel)
            return tom
        cache.set(nyckel, varde, timeout=None)
    return varde


# -----------------------------------------------------------------------------
# Sortering
# -----------------------------------------------------------------------------

def sorteringsnyckel(text: str) -> str:
    """Svensk bokstavsordning: å, ä och ö sist; isländska och latinska tecken som i svenska."""
    text = text.lower().strip().lstrip("«»\"'(")
    for tecken, ersattning in (("þ", "th"), ("ð", "d"), ("æ", "ä"), ("ø", "ö"), ("ǫ", "ö"), ("œ", "ö")):
        text = text.replace(tecken, ersattning)
    # å, ä och ö sorteras efter z och ska inte förlora sina prickar och ringar
    for tecken, ersattning in (("å", "{"), ("ä", "|"), ("ö", "}")):
        text = text.replace(tecken, ersattning)
    text = unicodedata.normalize("NFD", text)
    return "".join(t for t in text if not unicodedata.combining(t))


def _bokstav(titel: str) -> str:
    nyckel = sorteringsnyckel(titel)
    forsta = nyckel[:1]
    return {"{": "Å", "|": "Ä", "}": "Ö"}.get(forsta, forsta.upper() if forsta.isalpha() else "#")


# -----------------------------------------------------------------------------
# Källförteckningen
# -----------------------------------------------------------------------------

def datering(edtf: str | None) -> str | None:
    """En EDTF-datering i läsbar form: 0830/0882 blir 830–882 och 1373~ omkring 1373."""
    if not edtf:
        return None
    delar = []
    for del_ in edtf.split("/"):
        ungefar = del_.endswith("~") or del_.endswith("%")
        osaker = del_.endswith("?") or del_.endswith("%")
        del_ = del_.rstrip("~?%")
        ar, *rest = del_.split("-")
        text = (ar.lstrip("0") or "0") + ("-" + "-".join(rest) if rest else "")
        delar.append(("omkring " if ungefar else "") + text + ("?" if osaker else ""))
    return "–".join(delar)


def _sprakord(kod: str | None) -> str:
    return SPRAK.get(kod or "", kod or "okänt språk")


def _version(typ: str, sprak: str | None, roll: str | None, oversattare: str | None, ar: int | None,
             licens: str | None, passager: int, utgava: str | None) -> dict:
    beskrivning = TYPER.get(typ, typ)
    if typ == "oversattning" and oversattare:
        beskrivning += f" av {oversattare}" + (f" {ar}" if ar else "")
    if roll == "skolier":
        beskrivning += ", skolier"
    return {
        "sprak": _sprakord(sprak),
        "sprakkod": sprak,
        "ar": ar,
        "typ": typ,
        "beskrivning": beskrivning,
        "ogranskad": typ in ("maskinoversattning", "maskintranskription"),
        "licens": licens,
        "passager": passager,
        "utgava": utgava,
    }


def _berakna_kallforteckning() -> list[dict]:
    rader = _rader(
        """
        SELECT v.id, v.titel, v.upphov, v.datering_edtf, v.genre, k.namn AS kallsamling,
               u.id AS utgava_id, u.sprak, u.typ, u.roll, u.oversattare, u.ar,
               COALESCE(u.licens, k.licens) AS licens, pa.typ AS passagetyp,
               min(pa.sprak) AS passagesprak, count(*) AS passager, min(pa.ordning) AS forsta
        FROM fornmed.verk v
        JOIN fornmed.passage pa ON pa.verk_id = v.id
        LEFT JOIN fornmed.utgava u ON u.id = pa.utgava_id
        LEFT JOIN fornmed.kallsamling k ON k.id = v.kallsamling_id
        WHERE v.kallsamling_id NOT IN ('sdhk', 'rundata')
        GROUP BY v.id, v.titel, v.upphov, v.datering_edtf, v.genre, k.namn, u.id, u.sprak, u.typ,
                 u.roll, u.oversattare, u.ar, COALESCE(u.licens, k.licens), pa.typ
        """
    )
    verk: dict[str, dict] = {}
    for r in rader:
        post = verk.setdefault(r["id"], {
            "id": r["id"], "titel": r["titel"], "upphov": r["upphov"], "datering": r["datering_edtf"],
            "genre": r["genre"], "kallsamling": r["kallsamling"], "versioner": [], "antal": None,
        })
        typ = r["typ"] or ("regest" if r["passagetyp"] == "regest" else
                           "oversattning" if r["passagetyp"] == "oversattning" else "original")
        version = _version(typ, r["sprak"] or r["passagesprak"], r["roll"], r["oversattare"], r["ar"],
                           r["licens"], r["passager"], r["utgava_id"])
        version["forsta"] = r["forsta"]
        post["versioner"].append(version)

    ordning = {"original": 0, "oversattning": 1, "maskintranskription": 2, "maskinoversattning": 3, "regest": 4}
    for post in verk.values():
        post["versioner"].sort(key=lambda v: (ordning.get(v["typ"], 9), v["forsta"] or 0))
        post["datering"] = datering(post["datering"])
        # Flera utgåvor med samma språk och typ (Adam av Bremens skolier efter
        # Lappenberg och Schmeidler) skiljs åt med utgåvans år
        lika: dict[tuple, int] = {}
        for v in post["versioner"]:
            lika[(v["sprak"], v["beskrivning"])] = lika.get((v["sprak"], v["beskrivning"]), 0) + 1
        for v in post["versioner"]:
            # En maskinöversättning saknar eget år; årtalet i utgåvans id är originalets
            ar = v["ar"] or (re.search(r"(1[4-9]\d\d)", v["utgava"] or "") or [None, None])[1]
            if lika[(v["sprak"], v["beskrivning"])] > 1 and ar:
                if v["typ"] == "original":
                    v["beskrivning"] += f", {ar}"
                elif "transkription" in (v["utgava"] or ""):
                    v["beskrivning"] += f", efter maskintranskriptionen av utgåvan {ar}"
                else:
                    v["beskrivning"] += f", efter utgåvan {ar}"

    kallor = list(verk.values())
    kallor += [_samlad("sdhk"), _samlad("rundata")]
    for post in kallor:
        post["bokstav"] = _bokstav(post["titel"])
        licenser = {v["licens"] for v in post["versioner"] if v["licens"]}
        post["gemensam_licens"] = licenser.pop() if len(licenser) == 1 else None
        post["ogranskad"] = any(v["ogranskad"] for v in post["versioner"])
    kallor.sort(key=lambda k: sorteringsnyckel(k["titel"]))
    return kallor


def _samlad(kallsamling: str) -> dict:
    """Brevsamlingen eller runinskrifterna som en post, med språkversionerna sammanräknade."""
    rader = _rader(
        """
        SELECT pa.typ AS passagetyp, pa.sprak, COALESCE(u.licens, k.licens) AS licens, count(*) AS passager
        FROM fornmed.passage pa
        JOIN fornmed.verk v ON v.id = pa.verk_id
        LEFT JOIN fornmed.utgava u ON u.id = pa.utgava_id
        LEFT JOIN fornmed.kallsamling k ON k.id = v.kallsamling_id
        WHERE v.kallsamling_id = %s
        GROUP BY 1, 2, 3
        ORDER BY 4 DESC
        """,
        (kallsamling,),
    )
    antal = _rader("SELECT count(*) AS n FROM fornmed.verk WHERE kallsamling_id = %s", (kallsamling,))[0]["n"]
    namn = {"originaltext": "original", "normaliserad": "original", "oversattning": "oversattning",
            "regest": "regest", "skolion": "original"}
    versioner = []
    for r in rader:
        version = _version(namn.get(r["passagetyp"], "original"), r["sprak"], None, None, None,
                           r["licens"], r["passager"], None)
        if kallsamling == "rundata":
            version["beskrivning"] = {"originaltext": "translitterering", "normaliserad": "normalisering",
                                      "oversattning": "översättning"}.get(r["passagetyp"], version["beskrivning"])
        versioner.append(version)
    return {"id": None, "titel": SAMLADE[kallsamling], "upphov": None, "datering": None,
            "genre": "diplom" if kallsamling == "sdhk" else "runinskrift", "kallsamling": None,
            "versioner": versioner, "antal": antal, "samlad": kallsamling,
            "hanvisningar": HANVISNINGAR.get(kallsamling, [])}


def kallforteckning() -> list[dict]:
    """Alla källor i bokstavsordning med språkversioner och licens."""
    return _cachad("kallforteckning", _berakna_kallforteckning, [])


# -----------------------------------------------------------------------------
# Leveranser och omfång
# -----------------------------------------------------------------------------

def _json(varde):
    return varde if isinstance(varde, (dict, list)) or varde is None else json.loads(varde)


def _sammanfattning(andringar: dict) -> list[str]:
    if andringar.get("forsta_leveransen"):
        return ["Den första versionen av databasen."]
    rader = []
    for k in andringar.get("nya_kallsamlingar", []):
        rader.append(f"Ny källsamling: {k['namn']} ({k['verk']:,} verk)".replace(",", " "))
    for k in andringar.get("borttagna_kallsamlingar", []):
        rader.append(f"Borttagen källsamling: {k['namn']}")
    for k in andringar.get("kallsamlingar", {}).values():
        skillnad = k["efter"] - k["fore"]
        rader.append(f"{k['namn']}: {skillnad:+,} verk".replace(",", " "))
    for tabell, varden in andringar.get("tabeller", {}).items():
        rader.append(f"{varden['skillnad']:+,} {TABELLER.get(tabell, tabell)}".replace(",", " "))
    return rader


def _berakna_leveranser() -> list[dict]:
    rader = _rader("SELECT id, tidpunkt, anmarkning, andringar FROM fornmed.leverans ORDER BY tidpunkt DESC")
    for r in rader:
        r["andringar"] = _sammanfattning(_json(r["andringar"]) or {})
    return rader


def leveranser() -> list[dict]:
    """Leveranserna, senaste först, med en sammanfattning av vad som ändrats."""
    return _cachad("leveranser", _berakna_leveranser, [])


def _berakna_omfang() -> dict:
    rader = _rader(
        """
        SELECT (SELECT count(*) FROM fornmed.verk WHERE kallsamling_id = 'sdhk') AS brev,
               (SELECT count(*) FROM fornmed.verk WHERE kallsamling_id = 'rundata') AS runinskrifter,
               (SELECT count(*) FROM fornmed.verk WHERE kallsamling_id NOT IN ('sdhk', 'rundata')) AS ovriga_verk,
               (SELECT count(*) FROM fornmed.verk) AS verk,
               (SELECT count(*) FROM fornmed.passage) AS passager,
               (SELECT count(*) FROM fornmed.pastaende) AS pastaenden,
               (SELECT count(*) FROM fornmed.kallsamling) AS kallsamlingar
        """
    )
    return rader[0]


def omfang() -> dict:
    """Antal brev, runinskrifter, övriga verk, passager, påståenden och källsamlingar."""
    return _cachad("omfang", _berakna_omfang, {})

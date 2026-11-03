"""
Listor med filter och sidindelning: påståenden, bedömningar, utgåvor,
entiteternas namnformer och identifieringar, auktoritetslängder och
leveranser.

Varje listfunktion returnerar (rader, totalt antal). Sidindelningen är
sida och per_sida, som i API:et.
"""

import json

import db
from dokument import DokumentFel
from fragor import _en, _rader


def _sida(sql: str, param: list, ordning: str, sida: int, per_sida: int) -> tuple[list[dict], int]:
    """Kör en fråga sidvis och räknar totalen med samma villkor."""
    ph = db._ph()
    total = _en(f"SELECT count(*) AS n FROM ({sql}) t", param)["n"]
    rader = _rader(f"{sql} ORDER BY {ordning} LIMIT {ph} OFFSET {ph}",
                   [*param, per_sida, (sida - 1) * per_sida])
    return rader, total


def _villkor(par: list[tuple[str, object]]) -> tuple[str, list]:
    """WHERE-sats av (villkor, värde) där värdet inte är None.

    Villkoren skrivs med ? som platshållare. Ett villkor med flera ? får
    samma värde på varje plats ("subjekt = ? OR objekt = ?").
    """
    ph = db._ph()
    aktiva = [(v, varde) for v, varde in par if varde is not None]
    if not aktiva:
        return "", []
    param = [varde for v, varde in aktiva for _ in range(v.count("?"))]
    return "WHERE " + " AND ".join(v.replace("?", ph) for v, _ in aktiva), param


def _json(varde):
    return varde if varde is None or isinstance(varde, (dict, list)) else json.loads(varde)


# -----------------------------------------------------------------------------
# Påståenden och bedömningar
# -----------------------------------------------------------------------------

def lista_pastaenden(entitet: str | None = None, predikat: str | None = None,
                     verk: str | None = None, kallsamling: str | None = None,
                     extraktion: str | None = None, granskad: bool | None = None,
                     ar_fran: int | None = None, ar_till: int | None = None,
                     sida: int = 1, per_sida: int = 100) -> tuple[list[dict], int]:
    """Påståenden med källans verk, genre och tidsavstånd.

    entitet gäller som subjekt, objekt eller plats. Åren filtreras på
    påståendets tid med överlappande intervall.
    """
    p, ph = db._prefix(), db._ph()
    where, param = _villkor([
        ("(pt.subjekt_id = ? OR pt.objekt_id = ? OR pt.plats_id = ?)", entitet),
        ("pt.predikat = ?", predikat),
        ("pa.verk_id = ?", verk),
        ("v.kallsamling_id = ?", kallsamling),
        ("pt.extraktion = ?", extraktion),
        ("pt.granskad = ?", granskad),
        ("pt.tid_till >= ?", ar_fran * 10000 if ar_fran is not None else None),
        ("pt.tid_fran <= ?", ar_till * 10000 + 1231 if ar_till is not None else None),
    ])
    sql = f"""
        SELECT pt.id, pt.subjekt_id, s.namn AS subjekt, pt.predikat, pt.objekt_id,
               o.namn AS objekt, pt.objekt_varde, pt.plats_id, pt.tid_edtf, pt.passage_id,
               pa.verk_id, v.titel AS verk_titel, v.genre, v.kallsamling_id,
               pt.extraktion, pt.granskad, pt.tid_fran
        FROM {p}pastaende pt
        JOIN {p}passage pa ON pa.id = pt.passage_id
        JOIN {p}verk v ON v.id = pa.verk_id
        JOIN {p}entitet s ON s.id = pt.subjekt_id
        LEFT JOIN {p}entitet o ON o.id = pt.objekt_id
        {where}
    """
    rader, total = _sida(sql, param, "tid_fran NULLS LAST, id", sida, per_sida)
    for r in rader:
        r["granskad"] = bool(r["granskad"])
        r.pop("tid_fran")
    return rader, total


def lista_bedomningar(pastaende: str | None = None, verk: str | None = None,
                      aspekt: str | None = None, bedomare: str | None = None,
                      granskad: bool | None = None, sida: int = 1,
                      per_sida: int = 100) -> tuple[list[dict], int]:
    """Bedömningar av påståenden, verk, vittnen och identifieringar."""
    p = db._prefix()
    where, param = _villkor([
        ("b.pastaende_id = ?", pastaende),
        ("b.verk_id = ?", verk),
        ("b.aspekt = ?", aspekt),
        ("lower(b.bedomare) LIKE ?", f"%{bedomare.lower()}%" if bedomare else None),
        ("b.granskad = ?", granskad),
    ])
    sql = f"""
        SELECT b.id,
               CASE WHEN b.pastaende_id IS NOT NULL THEN 'pastaende'
                    WHEN b.verk_id IS NOT NULL THEN 'verk'
                    WHEN b.vittne_id IS NOT NULL THEN 'vittne'
                    ELSE 'identifiering' END AS maltyp,
               COALESCE(b.pastaende_id, b.verk_id, b.vittne_id, b.identifiering_id) AS mal_id,
               b.aspekt, b.varde, b.sakerhet, b.bedomare, b.publikation, b.sidor, b.ar,
               b.motivering, b.registrerad_av, b.granskad
        FROM {p}bedomning b
        {where}
    """
    rader, total = _sida(sql, param, "maltyp, mal_id, aspekt, ar", sida, per_sida)
    for r in rader:
        r["granskad"] = bool(r["granskad"])
    return rader, total


# -----------------------------------------------------------------------------
# Entiteter
# -----------------------------------------------------------------------------

def _entitet_finns(entitet_id: str) -> None:
    p, ph = db._prefix(), db._ph()
    if _en(f"SELECT id FROM {p}entitet WHERE id = {ph}", (entitet_id,)) is None:
        raise DokumentFel(404, f"Entiteten '{entitet_id}' finns inte.")


def namnformer(entitet_id: str, sida: int = 1, per_sida: int = 100) -> tuple[list[dict], int]:
    """Entitetens namnformer i källorna, med språk och passage."""
    _entitet_finns(entitet_id)
    p, ph = db._prefix(), db._ph()
    return _sida(f"SELECT namnform, sprak, passage_id FROM {p}entitet_namnform "
                 f"WHERE entitet_id = {ph}", [entitet_id], "namnform, passage_id", sida, per_sida)


def identifieringar(entitet_id: str) -> list[dict]:
    """Identifieringar åt båda håll, en rad per bedömning (eller en rad utan)."""
    _entitet_finns(entitet_id)
    p, ph = db._prefix(), db._ph()
    rader = _rader(
        f"""
        SELECT i.id, i.alternativgrupp,
               CASE WHEN i.entitet_id = {ph} THEN i.identifierad_med ELSE i.entitet_id END
                   AS annan_entitet_id,
               e.namn AS annan_entitet, i.kommentar,
               b.varde AS bedomning, b.bedomare, b.publikation, b.ar, b.granskad
        FROM {p}identifiering i
        JOIN {p}entitet e ON e.id = CASE WHEN i.entitet_id = {ph} THEN i.identifierad_med
                                         ELSE i.entitet_id END
        LEFT JOIN {p}bedomning b ON b.identifiering_id = i.id
        WHERE i.entitet_id = {ph} OR i.identifierad_med = {ph}
        ORDER BY i.alternativgrupp, i.id, b.ar
        """,
        (entitet_id,) * 4,
    )
    for r in rader:
        if r["granskad"] is not None:
            r["granskad"] = bool(r["granskad"])
    return rader


# -----------------------------------------------------------------------------
# Utgåvor och SDHK
# -----------------------------------------------------------------------------

UTGAVEKOLUMNER = "u.id, u.verk_id, u.referens, u.sprak, u.typ, u.roll, u.oversattare, u.ar, u.licens"


def utgavor(verk_id: str) -> list[dict]:
    """Verkets utgåvor med antal passager, också de utan text (SDHK:s tryck)."""
    p, ph = db._prefix(), db._ph()
    if _en(f"SELECT id FROM {p}verk WHERE id = {ph}", (verk_id,)) is None:
        raise DokumentFel(404, f"Verket '{verk_id}' finns inte.")
    return _rader(
        f"""
        SELECT {UTGAVEKOLUMNER}, count(pa.id) AS antal_passager
        FROM {p}utgava u LEFT JOIN {p}passage pa ON pa.utgava_id = u.id
        WHERE u.verk_id = {ph}
        GROUP BY {UTGAVEKOLUMNER}
        ORDER BY u.id
        """,
        (verk_id,),
    )


def hamta_utgava(utgava_id: str) -> dict:
    """En utgåva med verk och omfång."""
    p, ph = db._prefix(), db._ph()
    utgava = _en(
        f"""
        SELECT {UTGAVEKOLUMNER}, v.titel AS verk_titel, count(pa.id) AS antal_passager,
               sum(length(pa.text)) AS tecken
        FROM {p}utgava u
        JOIN {p}verk v ON v.id = u.verk_id
        LEFT JOIN {p}passage pa ON pa.utgava_id = u.id
        WHERE u.id = {ph}
        GROUP BY {UTGAVEKOLUMNER}, v.titel
        """,
        (utgava_id,),
    )
    if utgava is None:
        raise DokumentFel(404, f"Utgåvan '{utgava_id}' finns inte.")
    utgava["delar"] = _rader(
        f"SELECT del, del_typ, count(*) AS antal_passager FROM {p}passage "
        f"WHERE utgava_id = {ph} AND del IS NOT NULL GROUP BY del, del_typ ORDER BY min(ordning)",
        (utgava_id,),
    )
    return utgava


def sdhk_verk_id(nummer: int) -> str:
    """Verkets id för ett SDHK-nummer."""
    p, ph = db._prefix(), db._ph()
    verk_id = f"sdhk:{nummer}"
    if _en(f"SELECT id FROM {p}verk WHERE id = {ph}", (verk_id,)) is None:
        raise DokumentFel(404, f"SDHK {nummer} finns inte.")
    return verk_id


# -----------------------------------------------------------------------------
# Auktoriteter
# -----------------------------------------------------------------------------

def auktoritetslangder() -> list[dict]:
    """Längderna med licens och antal personer."""
    p = db._prefix()
    return _rader(
        f"""
        SELECT l.id, l.namn, l.licens, l.kalla, l.hamtad, l.beskrivning, count(a.person_id) AS antal
        FROM {p}auktoritetslangd l LEFT JOIN {p}auktoritet a ON a.langd_id = l.id
        GROUP BY l.id, l.namn, l.licens, l.kalla, l.hamtad, l.beskrivning
        ORDER BY l.id
        """
    )


def _langd(langd_id: str) -> dict:
    p, ph = db._prefix(), db._ph()
    langd = _en(f"SELECT id, namn, licens, kalla, hamtad, beskrivning FROM {p}auktoritetslangd "
                f"WHERE id = {ph}", (langd_id,))
    if langd is None:
        raise DokumentFel(404, f"Längden '{langd_id}' finns inte.",
                          langder=[r["id"] for r in auktoritetslangder()])
    return langd


def auktoritet(langd_id: str, titel: str | None = None, sate: str | None = None,
               ar: int | None = None, sida: int = 1,
               per_sida: int = 100) -> tuple[dict, list[dict], int]:
    """(längden, en rad per titel, totalt antal) i tillträdesordning.

    En person med flera titlar eller säten får en rad för varje. ar ger dem
    som bar titeln det året.
    """
    langd = _langd(langd_id)
    p = db._prefix()
    where, param = _villkor([
        ("t.langd_id = ?", langd_id),
        ("t.titel = ?", titel),
        ("t.sate = ?", sate),
        ("t.fran <= ?", ar),
        ("t.till >= ?", ar),
    ])
    sql = f"""
        SELECT a.person_id, a.namn, a.ordningstal, t.titel, t.sate, t.sate_id, t.fran, t.till, t.ar_text,
               a.fodd, a.dod, a.anm, a.wikidata_id, a.wikipedia
        FROM {p}auktoritet_titel t
        JOIN {p}auktoritet a ON a.langd_id = t.langd_id AND a.person_id = t.person_id
        {where}
    """
    rader, total = _sida(sql, param, "sate NULLS FIRST, fran, person_id", sida, per_sida)
    return langd, rader, total


def hamta_auktoritet(langd_id: str, person_id: str) -> dict:
    """En person i en längd med alla titlar."""
    langd = _langd(langd_id)
    p, ph = db._prefix(), db._ph()
    person = _en(
        f"SELECT person_id, namn, ordningstal, fodd, dod, anm, wikidata_id, wikipedia "
        f"FROM {p}auktoritet WHERE langd_id = {ph} AND person_id = {ph}",
        (langd_id, person_id),
    )
    if person is None:
        raise DokumentFel(404, f"'{person_id}' finns inte i längden '{langd_id}'.")
    person["titlar"] = _rader(
        f"SELECT titel, sate, sate_id, fran, till, ar_text FROM {p}auktoritet_titel "
        f"WHERE langd_id = {ph} AND person_id = {ph} ORDER BY nr",
        (langd_id, person_id),
    )
    person["langd"] = {k: langd[k] for k in ("id", "namn", "licens", "kalla")}
    return person


# -----------------------------------------------------------------------------
# Leveranser
# -----------------------------------------------------------------------------

def leveranser(sida: int = 1, per_sida: int = 50) -> tuple[list[dict], int]:
    """Leveranserna, senaste först, med anmärkning och ändringar."""
    p = db._prefix()
    rader, total = _sida(f"SELECT id, tidpunkt, anmarkning, andringar FROM {p}leverans", [],
                         "tidpunkt DESC", sida, per_sida)
    for r in rader:
        r["andringar"] = _json(r["andringar"])
    return rader, total


def hamta_leverans(leverans_id: str) -> dict:
    """En leverans med räkningen per tabell och källsamling."""
    p, ph = db._prefix(), db._ph()
    leverans = _en(f"SELECT id, tidpunkt, anmarkning, antal, andringar FROM {p}leverans "
                   f"WHERE id = {ph}", (leverans_id,))
    if leverans is None:
        raise DokumentFel(404, f"Leveransen '{leverans_id}' finns inte.")
    leverans["antal"] = _json(leverans["antal"])
    leverans["andringar"] = _json(leverans["andringar"])
    return leverans

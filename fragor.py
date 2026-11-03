"""
Läsfrågor mot källor, entiteter, påståenden och bedömningar.

Funktionerna returnerar vanliga dict och listor och är oberoende av MCP, så
att de kan användas från skript lika väl som från servern.
"""

import json
import re
import unicodedata

import db
import sok
from normalisering import ordform

# Standardlängd för texter i svaren; långa editionstexter läses vidare med
# fran_tecken
MAX_TECKEN = 8000


def _rader(sql: str, param: tuple | list = ()) -> list[dict]:
    """Kör en fråga och returnerar raderna som dict med kolumnnamn som nycklar."""
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, param)
        kolumner = [k[0] for k in cur.description]
        return [dict(zip(kolumner, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def _en(sql: str, param: tuple | list = ()) -> dict | None:
    rader = _rader(sql, param)
    return rader[0] if rader else None


def _sprak(varde) -> list[str]:
    """Språkkolumnen är TEXT[] i Postgres och JSON-text i SQLite."""
    if varde is None:
        return []
    return list(varde) if isinstance(varde, list) else json.loads(varde)


def kapa_text(text: str, max_tecken: int = MAX_TECKEN, fran_tecken: int = 0) -> dict:
    """Ett utsnitt av en text med uppgift om var det börjar och om mer finns."""
    utsnitt = text[fran_tecken : fran_tecken + max_tecken]
    slut = fran_tecken + len(utsnitt)
    svar = {"text": utsnitt, "tecken_totalt": len(text), "trunkerad": slut < len(text)}
    if svar["trunkerad"]:
        svar["fortsatt_fran_tecken"] = slut
    return svar


def _bedomningar(kolumn: str, mal_id: str) -> list[dict]:
    p, ph = db._prefix(), db._ph()
    rader = _rader(
        f"""
        SELECT id, aspekt, varde, sakerhet, bedomare, publikation, publikation_id, sidor,
               ar, motivering, registrerad_av, granskad
        FROM {p}bedomning WHERE {kolumn} = {ph}
        ORDER BY aspekt, ar
        """,
        (mal_id,),
    )
    for r in rader:
        r["granskad"] = bool(r["granskad"])
    return rader


# -----------------------------------------------------------------------------
# Källor
# -----------------------------------------------------------------------------

def hamta_verk(verk_id: str) -> dict | None:
    """Ett verk med vittnen, utgåvor, passager (utan text) och bedömningar."""
    p, ph = db._prefix(), db._ph()
    verk = _en(
        f"""
        SELECT v.id, v.titel, v.upphov, v.genre, v.sprak, v.utfardandeort, v.datering_edtf,
               v.datering_anm, v.beskrivning, v.extern_url, k.namn AS kallsamling, k.licens, v.extra
        FROM {p}verk v LEFT JOIN {p}kallsamling k ON k.id = v.kallsamling_id
        WHERE v.id = {ph}
        """,
        (verk_id,),
    )
    if verk is None:
        return None
    verk["sprak"] = _sprak(verk["sprak"])
    extra = verk.pop("extra") or {}
    if isinstance(extra, str):
        extra = json.loads(extra)
    # Bildlänkar (t.ex. Rundatas fotografier) för manuell kontroll av texten
    if extra.get("bilder"):
        verk["bilder"] = extra["bilder"]
    verk["vittnen"] = _rader(
        f"SELECT id, typ, beskrivning, signum, datering_edtf FROM {p}vittne "
        f"WHERE verk_id = {ph} ORDER BY id",
        (verk_id,),
    )
    verk["utgavor"] = _rader(
        f"SELECT id, referens, licens FROM {p}utgava WHERE verk_id = {ph} ORDER BY id", (verk_id,)
    )
    verk["passager"] = _rader(
        f"""
        SELECT id, typ, adress, sprak, length(text) AS tecken, url AS underlag_url
        FROM {p}passage WHERE verk_id = {ph} ORDER BY ordning, id
        """,
        (verk_id,),
    )
    verk["platser"] = _rader(
        f"""
        SELECT vp.roll, vp.plats_id, e.namn, vp.namnform, vp.osaker, vp.harledd,
               u.nutida_namn, k.namn AS kommun, l.namn AS land, u.latitud, u.longitud, u.metod, u.granskad
        FROM {p}verk_plats vp JOIN {p}entitet e ON e.id = vp.plats_id
        LEFT JOIN {p}plats_uppgift u ON u.entitet_id = vp.plats_id
        LEFT JOIN {p}entitet k ON k.id = u.kommun_id
        LEFT JOIN {p}entitet l ON l.id = u.land_id
        WHERE vp.verk_id = {ph} ORDER BY vp.roll, e.namn
        """,
        (verk_id,),
    )
    for plats in verk["platser"]:
        plats["osaker"], plats["harledd"] = bool(plats["osaker"]), bool(plats["harledd"])
        plats["granskad"] = None if plats["granskad"] is None else bool(plats["granskad"])
    verk["bedomningar"] = _bedomningar("verk_id", verk_id)
    return verk


def hamta_passage(passage_id: str, max_tecken: int = MAX_TECKEN, fran_tecken: int = 0
                  ) -> dict | None:
    """En passage med text (eventuellt kapad), verk och de påståenden som bygger på den."""
    p, ph = db._prefix(), db._ph()
    passage = _en(
        f"""
        SELECT pa.id, pa.verk_id, v.titel AS verk_titel, v.genre, v.datering_edtf AS verk_datering,
               pa.typ, pa.adress, pa.sprak, u.referens AS utgava,
               COALESCE(u.licens, k.licens) AS licens, k.namn AS kallsamling,
               pa.url AS underlag_url, v.extern_url AS verk_url, pa.text
        FROM {p}passage pa
        JOIN {p}verk v ON v.id = pa.verk_id
        LEFT JOIN {p}utgava u ON u.id = pa.utgava_id
        LEFT JOIN {p}kallsamling k ON k.id = v.kallsamling_id
        WHERE pa.id = {ph}
        """,
        (passage_id,),
    )
    if passage is None:
        return None
    passage.update(kapa_text(passage.pop("text"), max_tecken, fran_tecken))
    passage["pastaenden"] = _rader(
        f"SELECT id, subjekt_id, predikat, objekt_id, objekt_varde, tid_edtf "
        f"FROM {p}pastaende WHERE passage_id = {ph} ORDER BY id",
        (passage_id,),
    )
    return passage


# -----------------------------------------------------------------------------
# Entiteter
# -----------------------------------------------------------------------------

def _sokform(text: str) -> str:
    """
    Gemener utan diakritiska tecken utom svenska å, ä, ö, så att 'gea'
    hittar Gēatas och 'adils' hittar Aðils men 'ar' inte hittar 'år'.
    """
    text = text.casefold().replace("ð", "d").replace("þ", "th").replace("æ", "ae")
    skyddade = {"å": "\x01", "ä": "\x02", "ö": "\x03"}
    for tecken, ersattning in skyddade.items():
        text = text.replace(tecken, ersattning)
    text = "".join(t for t in unicodedata.normalize("NFKD", text) if not unicodedata.combining(t))
    for tecken, ersattning in skyddade.items():
        text = text.replace(ersattning, tecken)
    return text


def sok_entitet(namn: str, typ: str | None = None, antal: int = 20) -> list[dict]:
    """
    Entiteter vars namn eller namnform innehåller söksträngen.

    Jämförelsen görs i Python efter normalisering med _sokform: SQLite:s
    lower() hanterar bara ASCII, och namnformer som Gēatas och Aðils ska
    kunna hittas utan specialtecken.
    """
    p, ph = db._prefix(), db._ph()
    typvillkor = f" WHERE e.typ = {ph}" if typ else ""
    rader = _rader(
        f"""
        SELECT e.id, e.typ, e.namn, e.beskrivning, n.namnform
        FROM {p}entitet e
        LEFT JOIN {p}entitet_namnform n ON n.entitet_id = e.id{typvillkor}
        ORDER BY e.namn
        """,
        (typ,) if typ else (),
    )
    monster = _sokform(namn)
    traffar: dict[str, dict] = {}
    for r in rader:
        if monster in _sokform(r["namn"]) or (r["namnform"] and monster in _sokform(r["namnform"])):
            traffar.setdefault(r["id"], {k: r[k] for k in ("id", "typ", "namn", "beskrivning")})
    return list(traffar.values())[:antal]


def hamta_entitet(entitet_id: str, predikat: str | None = None, antal: int = 50,
                  fran: int = 0) -> dict | None:
    """
    En entitet med namnformer, identifieringar åt båda håll (med bedömningar)
    och de påståenden där den är subjekt, objekt eller plats.

    En kung eller ett ämbete kan förekomma i tusentals påståenden ur SDHK,
    så påståendena returneras sidvis (antal från position fran), föregångna
    av en sammanfattning per predikat med antal och årsspann.
    """
    p, ph = db._prefix(), db._ph()
    entitet = _en(
        f"SELECT id, typ, namn, beskrivning, wikidata_id FROM {p}entitet WHERE id = {ph}",
        (entitet_id,),
    )
    if entitet is None:
        return None
    entitet["namnformer"] = _rader(
        f"SELECT namnform, sprak, passage_id FROM {p}entitet_namnform WHERE entitet_id = {ph} "
        f"ORDER BY namnform LIMIT 100",
        (entitet_id,),
    )
    identifieringar = _rader(
        f"""
        SELECT i.id, i.alternativgrupp, i.kommentar,
               CASE WHEN i.entitet_id = {ph} THEN i.identifierad_med ELSE i.entitet_id END
                   AS annan_entitet_id
        FROM {p}identifiering i
        WHERE i.entitet_id = {ph} OR i.identifierad_med = {ph}
        ORDER BY i.alternativgrupp, i.id
        """,
        (entitet_id, entitet_id, entitet_id),
    )
    for i in identifieringar:
        annan = _en(f"SELECT namn, typ FROM {p}entitet WHERE id = {ph}", (i["annan_entitet_id"],))
        i["annan_entitet"] = annan["namn"] if annan else None
        i["bedomningar"] = _bedomningar("identifiering_id", i["id"])
    entitet["identifieringar"] = identifieringar
    plats = _en(
        f"""
        SELECT u.slag, u.nutida_namn, u.land_id, l.namn AS land, u.landskap_id, ls.namn AS landskap,
               u.lan_id, la.namn AS lan, u.kommun_id, k.namn AS kommun, u.socken_id, s.namn AS socken,
               u.ingar_i_id, i.namn AS ingar_i, u.latitud, u.longitud, u.kalla, u.metod, u.granskad, u.anm
        FROM {p}plats_uppgift u
        LEFT JOIN {p}entitet l ON l.id = u.land_id
        LEFT JOIN {p}entitet ls ON ls.id = u.landskap_id
        LEFT JOIN {p}entitet la ON la.id = u.lan_id
        LEFT JOIN {p}entitet k ON k.id = u.kommun_id
        LEFT JOIN {p}entitet s ON s.id = u.socken_id
        LEFT JOIN {p}entitet i ON i.id = u.ingar_i_id
        WHERE u.entitet_id = {ph}
        """,
        (entitet_id,),
    )
    if plats:
        plats["granskad"] = bool(plats["granskad"])
        entitet["plats_uppgift"] = plats
    villkor = f"(pt.subjekt_id = {ph} OR pt.objekt_id = {ph} OR pt.plats_id = {ph})"
    parametrar: tuple = (entitet_id, entitet_id, entitet_id)
    entitet["sammanfattning"] = _rader(
        f"""
        SELECT pt.predikat,
               CASE WHEN pt.subjekt_id = {ph} THEN 'subjekt'
                    WHEN pt.objekt_id = {ph} THEN 'objekt' ELSE 'plats' END AS roll,
               COUNT(*) AS antal, MIN(pt.tid_fran) / 10000 AS fran_ar, MAX(pt.tid_till) / 10000 AS till_ar
        FROM {p}pastaende pt
        WHERE {villkor}
        GROUP BY 1, 2
        ORDER BY 3 DESC
        """,
        (entitet_id, entitet_id) + parametrar,
    )
    if predikat:
        villkor += f" AND pt.predikat = {ph}"
        parametrar += (predikat,)
    entitet["pastaenden_totalt"] = _en(
        f"SELECT COUNT(*) AS n FROM {p}pastaende pt WHERE {villkor}", parametrar)["n"]
    entitet["pastaenden"] = _rader(
        f"""
        SELECT o.id, o.subjekt_id, o.predikat, o.objekt_id, o.objekt_varde, o.tid_edtf,
               o.verk_titel, o.genre, o.tidsavstand_ar, o.antal_bedomningar, o.omstridd,
               (SELECT b.varde FROM {p}bedomning b
                WHERE b.pastaende_id = o.id AND b.aspekt = 'titulatur' LIMIT 1) AS titulatur
        FROM {p}pastaende_oversikt o
        JOIN {p}pastaende pt ON pt.id = o.id
        WHERE {villkor}
        ORDER BY o.tidsavstand_ar, pt.tid_fran, o.id
        LIMIT {int(antal)} OFFSET {int(fran)}
        """,
        parametrar,
    )
    if fran + len(entitet["pastaenden"]) < entitet["pastaenden_totalt"]:
        entitet["fortsatt_fran"] = fran + len(entitet["pastaenden"])
    for rad in entitet["pastaenden"]:
        rad["omstridd"] = bool(rad["omstridd"])
        if rad["titulatur"] is None:
            del rad["titulatur"]
    return entitet


# -----------------------------------------------------------------------------
# Påståenden och bedömningar
# -----------------------------------------------------------------------------

def hamta_pastaende(pastaende_id: str) -> dict | None:
    """
    Ett påstående med källpassage, tidsavstånd, relationer till andra
    påståenden och forskningens bedömningar.
    """
    p, ph = db._prefix(), db._ph()
    pastaende = _en(
        f"""
        SELECT pt.id, pt.subjekt_id, s.namn AS subjekt, pt.predikat, pt.objekt_id,
               o.namn AS objekt, pt.objekt_varde, pt.plats_id, pl.namn AS plats, pt.tid_edtf,
               pt.citat, pt.passage_id, pa.adress, pa.typ AS passagetyp, pt.extraktion,
               pt.extraherad_av, pt.granskad, ov.verk_id, ov.verk_titel, ov.genre,
               ov.verk_datering, ov.tidsavstand_ar
        FROM {p}pastaende pt
        JOIN {p}pastaende_oversikt ov ON ov.id = pt.id
        JOIN {p}passage pa ON pa.id = pt.passage_id
        JOIN {p}entitet s ON s.id = pt.subjekt_id
        LEFT JOIN {p}entitet o ON o.id = pt.objekt_id
        LEFT JOIN {p}entitet pl ON pl.id = pt.plats_id
        WHERE pt.id = {ph}
        """,
        (pastaende_id,),
    )
    if pastaende is None:
        return None
    pastaende["granskad"] = bool(pastaende["granskad"])
    pastaende["relationer"] = _rader(
        f"""
        SELECT 'utgaende' AS riktning, relation, till_id AS annat_pastaende, kommentar
        FROM {p}pastaende_relation WHERE fran_id = {ph}
        UNION ALL
        SELECT 'inkommande', relation, fran_id, kommentar
        FROM {p}pastaende_relation WHERE till_id = {ph}
        """,
        (pastaende_id, pastaende_id),
    )
    pastaende["bedomningar"] = _bedomningar("pastaende_id", pastaende_id)
    return pastaende


def omstridda(maltyp: str | None = None) -> dict:
    """Mål där bedömningarna går isär, och entiteter med konkurrerande identifieringar."""
    p, ph = db._prefix(), db._ph()
    villkor = f" WHERE maltyp = {ph}" if maltyp else ""
    return {
        "omstridda": _rader(
            f"SELECT mal_id, maltyp, aspekt, antal_bedomningar, varden "
            f"FROM {p}omstridda{villkor} ORDER BY maltyp, mal_id",
            (maltyp,) if maltyp else (),
        ),
        "konkurrerande_identifieringar": _rader(
            f"SELECT alternativgrupp, entitet_id, antal_alternativ, alternativ "
            f"FROM {p}konkurrerande_identifieringar ORDER BY entitet_id"
        ),
    }


# -----------------------------------------------------------------------------
# Begreppsregister och ordböcker
# -----------------------------------------------------------------------------

def _ar_hanvisning_till_lagarna(definition: str) -> bool:
    """Söderwall definierar inte lagspråkets ord utan skriver bara 'L.' (se Schlyter)."""
    return re.fullmatch(r"\W*L\.\W*(Jfr.*)?", definition.strip()) is not None


def _artiklar(villkor: str, param: list, max_tecken: int) -> list[dict]:
    """Ordboksartiklar grupperade per ordbok och uppslagsord, med betydelserna i ordning."""
    p = db._prefix()
    rader = _rader(
        f"""
        SELECT a.id, a.kallsamling_id, k.namn AS ordbok, k.licens, a.lemma, a.lemgram, a.ordklass,
               a.betydelse_nr, a.definition, a.former
        FROM {p}ordboksartikel a JOIN {p}kallsamling k ON k.id = a.kallsamling_id
        WHERE {villkor}
        ORDER BY a.kallsamling_id, a.lemma, a.lemgram, a.betydelse_nr
        """,
        param,
    )
    artiklar: dict[tuple, dict] = {}
    for r in rader:
        nyckel = (r["kallsamling_id"], r["lemgram"] or r["lemma"])
        artikel = artiklar.setdefault(nyckel, {
            "ordbok": r["ordbok"], "ordbok_id": r["kallsamling_id"], "licens": r["licens"],
            "lemma": r["lemma"], "lemgram": r["lemgram"], "ordklass": r["ordklass"],
            "former": _sprak(r["former"])[:30], "betydelser": [],
        })
        artikel["betydelser"].append({"id": r["id"], "nr": r["betydelse_nr"],
                                      **kapa_text(r["definition"], max_tecken)})
    # Söderwall inleder ofta med 'L.' för lagspråkets betydelse och ger sedan
    # egna betydelser ur annan litteratur; en enda hänvisning räcker därför
    for artikel in artiklar.values():
        artikel["hanvisar_till_lagarna"] = artikel["ordbok_id"] != "schlyter" and any(
            _ar_hanvisning_till_lagarna(b["text"]) for b in artikel["betydelser"]
        )
    return list(artiklar.values())


def sok_ordbok(ord_: str, ordbok: str | None = None, antal: int = 10,
               max_tecken: int = 1500) -> list[dict]:
    """
    Uppslag i Schlyter och Söderwall på uppslagsord.

    Ordet normaliseras som i normalisering.ordform, så härad, häradh och
    hæraþ ger samma träffar. Utan exakt träff prövas ordet som början av
    uppslagsordet. När Söderwall hänvisar till lagarna ('L.') tas Schlyters
    artikel om ordet med: via samma lemgram när stavningen är densamma,
    annars via begreppsregistret, eftersom lemgram bygger på uppslagsordets
    stavning och Schlyters frælsi därför inte delar lemgram med Söderwalls frälse.
    """
    p, ph = db._prefix(), db._ph()
    form = ordform(ord_)
    ordboksvillkor = f" AND a.kallsamling_id = {ph}" if ordbok else ""
    extra = [ordbok] if ordbok else []
    artiklar = _artiklar(f"a.sokform = {ph}{ordboksvillkor}", [form, *extra], max_tecken)
    if not artiklar:
        artiklar = _artiklar(f"a.sokform LIKE {ph}{ordboksvillkor}", [form + "%", *extra], max_tecken)
    hanvisande = [a for a in artiklar if a["hanvisar_till_lagarna"]]
    if hanvisande and not any(a["ordbok_id"] == "schlyter" for a in artiklar):
        lemgram = [a["lemgram"] for a in hanvisande if a["lemgram"]]
        sokformer = list({ordform(a["lemma"]) for a in hanvisande})
        villkor = [f"a.lemgram IN ({', '.join([ph] * len(lemgram))})"] if lemgram else []
        villkor.append(
            f"""a.id IN (SELECT t2.artikel_id FROM {p}term t1
                         JOIN {p}term t2 ON t2.entitet_id = t1.entitet_id
                         WHERE t1.sokform IN ({', '.join([ph] * len(sokformer))})
                           AND t2.artikel_id IS NOT NULL)"""
        )
        schlyter = _artiklar(f"a.kallsamling_id = 'schlyter' AND ({' OR '.join(villkor)})",
                             [*lemgram, *sokformer], max_tecken)
        # Hela artikeln, inte bara den betydelse registret pekar på
        if schlyter:
            schlyter = _artiklar(
                f"a.kallsamling_id = 'schlyter' AND a.lemgram IN ({', '.join([ph] * len(schlyter))})",
                [a["lemgram"] for a in schlyter], max_tecken,
            )
        artiklar = schlyter + artiklar
    return artiklar[:antal]


def hamta_begrepp(term_eller_id: str, max_tecken: int = 1500) -> list[dict]:
    """
    Begrepp i registret som matchar en term (i valfri form och böjning)
    eller ett begrepps-id, med definition, termer per språk, relationer
    och ordböckernas artiklar.
    """
    p, ph = db._prefix(), db._ph()
    if term_eller_id.startswith("begrepp:"):
        begrepp_ids = [term_eller_id]
    else:
        begrepp_ids = [b["begrepp_id"] for b in sok.expandera(term_eller_id).begrepp]
    svar = []
    for begrepp_id in begrepp_ids:
        begrepp = _en(f"SELECT id, namn AS huvudterm, beskrivning AS definition FROM {p}entitet "
                      f"WHERE id = {ph} AND typ = 'begrepp'", (begrepp_id,))
        if begrepp is None:
            continue
        termer = _rader(
            f"SELECT term, sprak, termtyp, artikel_id, registrerad_av, granskad FROM {p}term "
            f"WHERE entitet_id = {ph} ORDER BY sprak, termtyp, term",
            (begrepp_id,),
        )
        per_sprak: dict[str, list[dict]] = {}
        for t in termer:
            per_sprak.setdefault(t["sprak"], []).append({"term": t["term"], "termtyp": t["termtyp"]})
        begrepp["termer"] = per_sprak
        begrepp["registrerad_av"] = termer[0]["registrerad_av"] if termer else None
        begrepp["granskad"] = all(bool(t["granskad"]) for t in termer) if termer else False
        begrepp["relationer"] = _rader(
            f"""
            SELECT 'bredare' AS relation, r.till_id AS begrepp_id, e.namn
            FROM {p}begreppsrelation r JOIN {p}entitet e ON e.id = r.till_id
            WHERE r.fran_id = {ph} AND r.relation = 'bredare'
            UNION ALL
            SELECT 'smalare', r.fran_id, e.namn
            FROM {p}begreppsrelation r JOIN {p}entitet e ON e.id = r.fran_id
            WHERE r.till_id = {ph} AND r.relation = 'bredare'
            UNION ALL
            SELECT 'relaterad', CASE WHEN r.fran_id = {ph} THEN r.till_id ELSE r.fran_id END, e.namn
            FROM {p}begreppsrelation r
            JOIN {p}entitet e ON e.id = CASE WHEN r.fran_id = {ph} THEN r.till_id ELSE r.fran_id END
            WHERE r.relation = 'relaterad' AND (r.fran_id = {ph} OR r.till_id = {ph})
            """,
            (begrepp_id,) * 6,
        )
        artikel_ids = sorted({t["artikel_id"] for t in termer if t["artikel_id"]})
        begrepp["ordboksartiklar"] = []
        if artikel_ids:
            # Hela artikeln (alla betydelser) för de uppslagsord termerna kommer från
            begrepp["ordboksartiklar"] = _artiklar(
                f"""(a.kallsamling_id, a.lemgram) IN (
                        SELECT kallsamling_id, lemgram FROM {p}ordboksartikel
                        WHERE id IN ({', '.join([ph] * len(artikel_ids))}))""",
                artikel_ids, max_tecken,
            )
        svar.append(begrepp)
    return svar


def lista_vokabular(schema: str | None = None) -> list[dict]:
    """Kontrollerade värden, ev. avgränsade till ett schema (t.ex. 'historicitet')."""
    p, ph = db._prefix(), db._ph()
    villkor = f" WHERE schema = {ph}" if schema else ""
    return _rader(
        f"SELECT schema, kod, etikett, beskrivning FROM {p}vokabular{villkor} "
        f"ORDER BY schema, ordning",
        (schema,) if schema else (),
    )


def statistik() -> dict:
    """Antal rader per huvudtabell och vilka källsamlingar som finns."""
    p = db._prefix()
    antal = {}
    for tabell in ("verk", "vittne", "passage", "chunk", "entitet", "identifiering",
                   "pastaende", "bedomning", "term", "ordboksartikel"):
        antal[tabell] = _en(f"SELECT count(*) AS n FROM {p}{tabell}")["n"]
    return {
        "antal": antal,
        "kallsamlingar": _rader(
            f"SELECT k.id, k.namn, k.licens, k.version, count(v.id) AS verk "
            f"FROM {p}kallsamling k LEFT JOIN {p}verk v ON v.kallsamling_id = k.id "
            f"GROUP BY k.id, k.namn, k.licens, k.version ORDER BY k.id"
        ),
    }

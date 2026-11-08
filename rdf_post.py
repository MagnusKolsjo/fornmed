"""
En enskild post i Fornmed som RDF, för uppslag av URI:er under /id/.

Beskrivningen byggs direkt ur databasen med samma översättning som
exporten (rdf_mappning.py), så att en uppslagen post alltid stämmer med
dumpfilerna. Utöver postens egna tripler tas länkarna från närliggande
poster med (ett verks vittnen och passager, en entitets termer och
identifieringar) och etiketten för varje Fornmed-post som beskrivningen
pekar på, så att den går att läsa utan fler uppslag.

Formaten är Turtle, JSON-LD, N-Triples och RDF/XML.
"""

import urllib.parse
from collections.abc import Iterator

from rdflib import Graph

import db
import rdf_mappning as m
import rdf_uri
import vokabular_rdf
from rdf_export import _json, _lista

# Format: kod i format= → (media-typ, rdflib-format, filändelse)
FORMAT = {
    "ttl": ("text/turtle", "turtle", "ttl"),
    "jsonld": ("application/ld+json", "json-ld", "jsonld"),
    "nt": ("application/n-triples", "nt", "nt"),
    "rdf": ("application/rdf+xml", "xml", "rdf"),
}
MEDIATYP_TILL_FORMAT = {mediatyp: kod for kod, (mediatyp, _, _) in FORMAT.items()}

PREFIX = {
    "fm": m.FM, "crm": m.CRM, "crminf": m.CRMINF, "lrmoo": m.LRMOO, "rdfs": m.RDFS,
    "skos": m.SKOS, "skosxl": m.SKOSXL, "dcterms": m.DCTERMS, "foaf": m.FOAF, "geo": m.GEO,
    "wgs84": m.WGS84, "xsd": m.XSD, "wd": m.WD,
    "kallsamling": rdf_uri.ID + "kallsamling/", "verk": rdf_uri.ID + "verk/",
    "vittne": rdf_uri.ID + "vittne/", "utgava": rdf_uri.ID + "utgava/",
    "passage": rdf_uri.ID + "passage/", "entitet": rdf_uri.ID + "entitet/",
    "pastaende": rdf_uri.ID + "pastaende/", "identifiering": rdf_uri.ID + "identifiering/",
    "bedomning": rdf_uri.ID + "bedomning/", "term": rdf_uri.ID + "term/",
}


class PostSaknas(LookupError):
    """Det finns ingen post med det id:t."""


# -----------------------------------------------------------------------------
# Läsning
# -----------------------------------------------------------------------------

def _rader(conn, sql: str, *param) -> list[dict]:
    pf, ph = db._prefix(), db._ph()
    sql = sql.replace("{pf}", pf).replace("?", ph)
    if db._ar_postgres():
        cur = conn.cursor(cursor_factory=db.psycopg2.extras.RealDictCursor)
        cur.execute(sql, param)
        rader = [dict(r) for r in cur.fetchall()]
    else:
        cur = conn.cursor()
        cur.execute(sql, param)
        kolumner = [d[0] for d in cur.description]
        rader = [dict(zip(kolumner, r)) for r in cur.fetchall()]
    cur.close()
    return rader


def _en(conn, sql: str, *param) -> dict:
    rader = _rader(conn, sql, *param)
    if not rader:
        raise PostSaknas
    return rader[0]


def _alla_verk_id(conn, verk_id: list[str]) -> frozenset[str]:
    """De av id:na som är verk; behövs för påståenden vars objekt är ett verk."""
    if not verk_id:
        return frozenset()
    platser = ",".join("?" * len(verk_id))
    return frozenset(r["id"] for r in _rader(conn, f"SELECT id FROM {{pf}}verk WHERE id IN ({platser})", *verk_id))


# -----------------------------------------------------------------------------
# Beskrivningar per posttyp
# -----------------------------------------------------------------------------

def _lankar(conn, typ: str, post_id: str) -> Iterator[m.Trippel]:
    for r in _rader(conn, "SELECT * FROM {pf}extern_lank WHERE post_typ = ? AND post_id = ? ORDER BY uri",
                    typ, post_id):
        yield from m.extern_lank(r)


def _verk(conn, verk_id: str) -> Iterator[m.Trippel]:
    rad = _en(conn, "SELECT * FROM {pf}verk WHERE id = ?", verk_id)
    rad["sprak"] = _lista(rad.get("sprak"))
    platser = _rader(conn, "SELECT * FROM {pf}verk_plats WHERE verk_id = ? ORDER BY roll, plats_id", verk_id)
    yield from m.verk(rad, platser)
    yield from _lankar(conn, "verk", verk_id)
    for v in _rader(conn, "SELECT id, beskrivning FROM {pf}vittne WHERE verk_id = ? ORDER BY id", verk_id):
        s = m.post("vittne", v["id"])
        yield s, m.p("crm", "P128_carries"), m.post("verk", verk_id)
        yield s, m.ETIKETT, m.L(v["beskrivning"])
    for u in _rader(conn, "SELECT id, referens FROM {pf}utgava WHERE verk_id = ? ORDER BY id", verk_id):
        s = m.post("utgava", u["id"])
        yield s, m.p("lrmoo", "R4_embodies"), m.post("verk", verk_id)
        yield s, m.ETIKETT, m.L(u["referens"])
    for ps in _rader(conn, "SELECT id, adress FROM {pf}passage WHERE verk_id = ? ORDER BY ordning, id", verk_id):
        s = m.post("passage", ps["id"])
        yield s, m.p("crm", "P106i_forms_part_of"), m.post("verk", verk_id)
        if ps.get("adress"):
            yield s, m.ETIKETT, m.L(ps["adress"])
    for b in _rader(conn, "SELECT * FROM {pf}bedomning WHERE verk_id = ? ORDER BY id", verk_id):
        yield from m.bedomning(b)


def _vittne(conn, vittne_id: str) -> Iterator[m.Trippel]:
    yield from m.vittne(_en(conn, "SELECT * FROM {pf}vittne WHERE id = ?", vittne_id))
    yield from _lankar(conn, "vittne", vittne_id)
    for b in _rader(conn, "SELECT * FROM {pf}bedomning WHERE vittne_id = ? ORDER BY id", vittne_id):
        yield from m.bedomning(b)


def _utgava(conn, utgava_id: str) -> Iterator[m.Trippel]:
    yield from m.utgava(_en(conn, "SELECT * FROM {pf}utgava WHERE id = ?", utgava_id))


def _passage(conn, passage_id: str) -> Iterator[m.Trippel]:
    rad = _en(conn, "SELECT * FROM {pf}passage WHERE id = ?", passage_id)
    maskin = bool(rad.get("utgava_id")) and bool(_rader(
        conn, "SELECT 1 FROM {pf}utgava WHERE id = ? AND typ = 'maskinoversattning'", rad["utgava_id"]))
    yield from m.passage(rad, maskin)
    for p in _rader(conn, "SELECT id FROM {pf}pastaende WHERE passage_id = ? ORDER BY id", passage_id):
        yield m.post("pastaende", p["id"]), m.p("crm", "P70i_is_documented_in"), m.post("passage", passage_id)


def _pastaende(conn, pastaende_id: str) -> Iterator[m.Trippel]:
    rad = _en(conn, "SELECT * FROM {pf}pastaende WHERE id = ?", pastaende_id)
    yield from m.pastaende(rad, _alla_verk_id(conn, [rad["objekt_varde"]] if rad.get("objekt_varde") else []))
    for r in _rader(conn, "SELECT * FROM {pf}pastaende_relation WHERE fran_id = ? OR till_id = ?",
                    pastaende_id, pastaende_id):
        yield from m.pastaende_relation(r)
    for b in _rader(conn, "SELECT * FROM {pf}bedomning WHERE pastaende_id = ? ORDER BY id", pastaende_id):
        yield from m.bedomning(b)


def _entitet(conn, entitet_id: str) -> Iterator[m.Trippel]:
    rad = _en(conn, "SELECT * FROM {pf}entitet WHERE id = ?", entitet_id)
    rad["extra"] = _json(rad.get("extra"))
    namnformer = _rader(conn, "SELECT * FROM {pf}entitet_namnform WHERE entitet_id = ? ORDER BY namnform", entitet_id)
    plats = _rader(conn, "SELECT * FROM {pf}plats_uppgift WHERE entitet_id = ?", entitet_id)
    yield from m.entitet(rad, namnformer, plats[0] if plats else None)
    yield from m.entitetens_lankar(rad, rad.get("wikidata_id"))
    yield from _lankar(conn, "entitet", entitet_id)
    for a in _rader(conn, "SELECT * FROM {pf}auktoritet WHERE person_id = ?", entitet_id):
        yield from m.auktoritetens_lankar(a)
    for t in _rader(conn, "SELECT * FROM {pf}term WHERE entitet_id = ? ORDER BY id", entitet_id):
        yield from m.term(t)
    for r in _rader(conn, "SELECT * FROM {pf}begreppsrelation WHERE fran_id = ?", entitet_id):
        yield from m.begreppsrelation(r)
    for i in _rader(conn, "SELECT * FROM {pf}identifiering WHERE entitet_id = ? OR identifierad_med = ? ORDER BY id",
                    entitet_id, entitet_id):
        yield from m.identifiering(i)


def _identifiering(conn, identifiering_id: str) -> Iterator[m.Trippel]:
    yield from m.identifiering(_en(conn, "SELECT * FROM {pf}identifiering WHERE id = ?", identifiering_id))
    for b in _rader(conn, "SELECT * FROM {pf}bedomning WHERE identifiering_id = ? ORDER BY id", identifiering_id):
        yield from m.bedomning(b)


def _bedomning(conn, bedomning_id: str) -> Iterator[m.Trippel]:
    yield from m.bedomning(_en(conn, "SELECT * FROM {pf}bedomning WHERE id = ?", bedomning_id))


def _term(conn, term_id: str) -> Iterator[m.Trippel]:
    yield from m.term(_en(conn, "SELECT * FROM {pf}term WHERE id = ?", term_id))


def _ordboksartikel(conn, artikel_id: str) -> Iterator[m.Trippel]:
    yield from m.ordboksartikel(_en(conn, "SELECT * FROM {pf}ordboksartikel WHERE id = ?", artikel_id))


def _kallsamling(conn, kallsamling_id: str) -> Iterator[m.Trippel]:
    yield from m.kallsamling(_en(conn, "SELECT * FROM {pf}kallsamling WHERE id = ?", kallsamling_id))


def _langd(conn, langd_id: str) -> Iterator[m.Trippel]:
    yield from m.langd(_en(conn, "SELECT * FROM {pf}auktoritetslangd WHERE id = ?", langd_id))
    for t in _rader(conn, "SELECT * FROM {pf}auktoritet_titel WHERE langd_id = ? ORDER BY person_id, nr", langd_id):
        yield from m.langd_titel(t)


BESKRIVNING = {
    "verk": _verk, "vittne": _vittne, "utgava": _utgava, "passage": _passage,
    "pastaende": _pastaende, "entitet": _entitet, "identifiering": _identifiering,
    "bedomning": _bedomning, "term": _term, "ordboksartikel": _ordboksartikel,
    "kallsamling": _kallsamling, "langd": _langd,
}


def _etiketter(conn, tripler: list[m.Trippel]) -> Iterator[m.Trippel]:
    """rdfs:label för verk och entiteter som beskrivningen pekar på men inte beskriver."""
    beskrivna = {s for s, _, _ in tripler}
    saknade: dict[str, set[str]] = {"verk": set(), "entitet": set()}
    for _, _, o in tripler:
        if o.startswith("<" + rdf_uri.ID) and o not in beskrivna:
            typ, _, kodat_id = o[len(rdf_uri.ID) + 1:-1].partition("/")
            if typ in saknade and "#" not in kodat_id:
                saknade[typ].add(urllib.parse.unquote(kodat_id))
    for typ, kolumn in (("verk", "titel"), ("entitet", "namn")):
        id_ = sorted(saknade[typ])
        for start in range(0, len(id_), 500):
            del_ = id_[start:start + 500]
            platser = ",".join("?" * len(del_))
            for r in _rader(conn, f"SELECT id, {kolumn} AS etikett FROM {{pf}}{typ} WHERE id IN ({platser})", *del_):
                yield m.post(typ, r["id"]), m.ETIKETT, m.L(r["etikett"])


def tripler(typ: str, post_id: str) -> list[m.Trippel]:
    """Postens beskrivning som tripler. PostSaknas om posten inte finns."""
    if typ == "vokabular":
        return _vokabular(post_id)
    if typ == "begreppsregister":
        return _begreppsregister()
    if typ not in BESKRIVNING:
        raise PostSaknas
    conn = db._hamta_db()
    try:
        ut = list(BESKRIVNING[typ](conn, post_id))
        ut.extend(_etiketter(conn, ut))
    finally:
        conn.close()
    return ut


def _vokabular(sokvag: str) -> list[m.Trippel]:
    """Ett vokabulär (axel) eller ett värde i det (axel/kod)."""
    uri = m.I(rdf_uri.ID + "vokabular/" + sokvag)
    g = vokabular_rdf.bygg_graf()
    ut = [(s, p, o) for s, p, o in _ntrader(g) if s == uri or (o == uri and "inScheme" in p)]
    if not ut:
        raise PostSaknas
    return ut


def _begreppsregister() -> list[m.Trippel]:
    """Begreppsregistret som schema. Begreppen själva är entiteter och slås upp under /id/entitet/."""
    uri = m.I(m.BEGREPPSREGISTER)
    return [(s, p, o) for s, p, o in _ntrader(vokabular_rdf.bygg_graf()) if s == uri]


def _ntrader(g: Graph) -> Iterator[m.Trippel]:
    for rad in g.serialize(format="nt", encoding="utf-8").decode("utf-8").splitlines():
        if rad.strip():
            s, p, o = rad.strip()[:-2].split(" ", 2)
            yield s, p, o


# -----------------------------------------------------------------------------
# Serialisering
# -----------------------------------------------------------------------------

def som_graf(trippellista: list[m.Trippel]) -> Graph:
    g = Graph()
    for prefix, namnrum in PREFIX.items():
        g.bind(prefix, namnrum)
    g.parse(data="\n".join(f"{s} {p} {o} ." for s, p, o in trippellista), format="nt")
    return g


def serialisera(trippellista: list[m.Trippel], fmt: str) -> bytes:
    """Tripler i formatet `fmt` (ttl, jsonld, nt eller rdf)."""
    if fmt == "nt":
        return "".join(f"{s} {p} {o} .\n" for s, p, o in trippellista).encode("utf-8")
    g = som_graf(trippellista)
    if fmt == "jsonld":
        return g.serialize(format="json-ld", context=PREFIX, auto_compact=True, encoding="utf-8")
    return g.serialize(format=FORMAT[fmt][1], encoding="utf-8")


def kvalitet(accept: str | None, mediatyp: str) -> float:
    """Accept-huvudets q-värde för just den här media-typen (0 om den inte nämns)."""
    for del_ in (accept or "").lower().split(","):
        delar = [d.strip() for d in del_.split(";")]
        if delar[0] == mediatyp:
            for param in delar[1:]:
                if param.startswith("q="):
                    try:
                        return float(param[2:])
                    except ValueError:
                        return 0.0
            return 1.0
    return 0.0


def valj_format(begart: str | None, accept: str | None, html: bool = True) -> str | None:
    """
    Formatet för svaret: 'html' eller en kod i FORMAT, eller None om inget
    passar. `format=` gäller före Accept-huvudet. Utan någon av dem, och för
    */*, blir det HTML när `html` är sant, annars Turtle.
    """
    if begart:
        return begart if begart in FORMAT or (html and begart == "html") else None
    if not accept:
        return "html" if html else "ttl"
    kandidater: list[tuple[float, int, str]] = []
    for ordning, del_ in enumerate(accept.split(",")):
        delar = [d.strip() for d in del_.split(";")]
        typ, q = delar[0].lower(), 1.0
        for param in delar[1:]:
            if param.startswith("q="):
                try:
                    q = float(param[2:])
                except ValueError:
                    q = 0.0
        if q <= 0:
            continue
        if typ in MEDIATYP_TILL_FORMAT:
            kandidater.append((q, -ordning, MEDIATYP_TILL_FORMAT[typ]))
        elif typ in ("text/html", "application/xhtml+xml") and html:
            kandidater.append((q, -ordning, "html"))
        elif typ in ("*/*", "text/*", "application/*"):
            kandidater.append((q - 0.001, -ordning, "html" if html else "ttl"))
    if not kandidater:
        return None
    return max(kandidater)[2]

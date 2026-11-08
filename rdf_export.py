"""
Skriver hela Fornmed som RDF: en gzippad N-Quads-fil per namngiven graf.

Graferna och deras licenser beskrivs i lankade_data/README.md. Varje
källsamling får en egen graf och fil, så att den som återanvänder data kan
välja efter licens. En metadatagraf beskriver graferna med licens och antal
tripler (VoID), och vokabulärgrafen innehåller Fornmeds klasser, egenskaper
och kontrollerade vokabulär.

Med --kontrollera samlas alla Fornmed-URI:er som förekommer som subjekt och
objekt, och skriptet rapporterar länkar till poster som inte finns. Det
kräver några hundra MB minne.

    python rdf_export.py -o rdf/
    python rdf_export.py -o rdf/ --kontrollera
"""

import argparse
import gzip
import json
import logging
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from rdflib import Graph

import db
import rdf_mappning as m
import rdf_uri
import vokabular_rdf

log = logging.getLogger("rdf_export")

ONTOLOGI = Path(__file__).parent / "lankade_data" / "fornmed.ttl"
VOID = "http://rdfs.org/ns/void#"
EGET_ID = "<" + rdf_uri.ID


# -----------------------------------------------------------------------------
# Läsning ur databasen
# -----------------------------------------------------------------------------

def _strom(conn, sql: str, storlek: int = 5000) -> Iterator[dict]:
    """
    Rader som dict, hämtade i omgångar så att stora tabeller (passagernas
    text) aldrig ligger i minnet på en gång. Postgres behöver en namngiven
    markör för det; SQLite läser lat av sig självt.
    """
    if db._ar_postgres():
        cur = conn.cursor(name=f"export_{time.monotonic_ns()}", cursor_factory=db.psycopg2.extras.RealDictCursor)
        cur.itersize = storlek
        cur.execute(sql)
        yield from cur
        cur.close()
    else:
        cur = conn.cursor()
        cur.execute(sql)
        kolumner = [d[0] for d in cur.description]
        while rader := cur.fetchmany(storlek):
            for rad in rader:
                yield dict(zip(kolumner, rad))


def _json(varde):
    """JSONB i Postgres kommer som dict; i SQLite som text."""
    if isinstance(varde, str):
        return json.loads(varde) if varde else {}
    return varde or {}


def _lista(varde):
    """TEXT[] i Postgres kommer som lista; i SQLite som JSON-text."""
    if isinstance(varde, str):
        return json.loads(varde) if varde.startswith("[") else [varde]
    return varde or []


# -----------------------------------------------------------------------------
# Skrivning
# -----------------------------------------------------------------------------

class Skrivare:
    """Håller en gzippad fil öppen per graf och räknar tripler."""

    def __init__(self, katalog: Path, kontrollera: bool):
        self.katalog = katalog
        self.filer: dict[str, gzip.GzipFile] = {}
        self.antal: Counter[str] = Counter()
        self.kontrollera = kontrollera
        self.subjekt: set[str] = set()
        self.objekt: dict[str, str] = {}

    @staticmethod
    def filnamn(graf: str) -> str:
        return graf.replace("/", "-") + ".nq.gz"

    def skriv(self, graf: str, tripler: Iterable[m.Trippel]) -> None:
        fil = self.filer.get(graf)
        if fil is None:
            fil = self.filer[graf] = gzip.open(self.katalog / self.filnamn(graf), "wt", encoding="utf-8")
        g = m.I(rdf_uri.graf_uri(graf))
        n = 0
        for s, p, o in tripler:
            fil.write(f"{s} {p} {o} {g} .\n")
            n += 1
            if self.kontrollera:
                if s.startswith(EGET_ID):
                    self.subjekt.add(s)
                if o.startswith(EGET_ID):
                    # Spara en förekomst per mål, för felrapporten
                    self.objekt.setdefault(o, s)
        self.antal[graf] += n

    def stang(self) -> None:
        for fil in self.filer.values():
            fil.close()

    def saknade(self) -> dict[str, list[tuple[str, str]]]:
        """Länkade Fornmed-URI:er som inte beskrivs någonstans, per posttyp."""
        ut: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for o, s in self.objekt.items():
            if o not in self.subjekt:
                typ = o[len(EGET_ID):].split("/", 1)[0]
                ut[typ].append((o, s))
        return ut


def _rdflib_tripler(g: Graph) -> Iterator[m.Trippel]:
    """Tripler ur en rdflib-graf i samma N-Triples-form som rdf_mappning."""
    for rad in g.serialize(format="nt", encoding="utf-8").decode("utf-8").splitlines():
        rad = rad.strip()
        if not rad:
            continue
        # Varje rad slutar med " ."; objektet kan innehålla mellanslag
        s, p, o = rad[:-2].split(" ", 2)
        yield s, p, o


# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------

def exportera(katalog: Path, kontrollera: bool) -> Skrivare:
    katalog.mkdir(parents=True, exist_ok=True)
    ut = Skrivare(katalog, kontrollera)
    pf = db._prefix()
    conn = db._hamta_db()
    try:
        # Källsamlingarna styr vilken graf källornas poster hamnar i
        kallsamlingar = list(_strom(conn, f"SELECT * FROM {pf}kallsamling ORDER BY id"))
        verkets_samling: dict[str, str] = {
            r["id"]: r["kallsamling_id"] or "okand"
            for r in _strom(conn, f"SELECT id, kallsamling_id FROM {pf}verk")
        }
        kallgraf = lambda verk_id: f"kallsamling/{verkets_samling.get(verk_id, 'okand')}"  # noqa: E731

        log.info("Vokabulär och klasser")
        vok = vokabular_rdf.bygg_graf()
        vok.parse(ONTOLOGI, format="turtle")
        ut.skriv("vokabular", _rdflib_tripler(vok))
        ut.skriv("vokabular", _extra_vokabular())

        log.info("Verk")
        platser: dict[str, list[dict]] = defaultdict(list)
        for r in _strom(conn, f"SELECT * FROM {pf}verk_plats ORDER BY verk_id, roll, plats_id"):
            platser[r["verk_id"]].append(r)
        for r in _strom(conn, f"SELECT * FROM {pf}verk ORDER BY id"):
            r["sprak"] = _lista(r.get("sprak"))
            ut.skriv(kallgraf(r["id"]), m.verk(r, platser.get(r["id"], ())))
        del platser

        log.info("Vittnen och utgåvor")
        for r in _strom(conn, f"SELECT * FROM {pf}vittne ORDER BY id"):
            ut.skriv(kallgraf(r["verk_id"]), m.vittne(r))
        maskinoversatta: set[str] = set()
        for r in _strom(conn, f"SELECT * FROM {pf}utgava ORDER BY id"):
            if r.get("typ") == "maskinoversattning":
                maskinoversatta.add(r["id"])
            ut.skriv(kallgraf(r["verk_id"]), m.utgava(r))

        log.info("Passager")
        for r in _strom(conn, f"SELECT id, verk_id, utgava_id, typ, adress, ordning, sprak, text, url, del "
                              f"FROM {pf}passage ORDER BY verk_id, ordning, id"):
            ut.skriv(kallgraf(r["verk_id"]), m.passage(r, r.get("utgava_id") in maskinoversatta))

        log.info("Påståenden")
        kanda_verk = frozenset(verkets_samling)
        for r in _strom(conn, f"SELECT p.*, ps.verk_id FROM {pf}pastaende p "
                              f"JOIN {pf}passage ps ON ps.id = p.passage_id ORDER BY p.id"):
            ut.skriv(kallgraf(r["verk_id"]), m.pastaende(r, kanda_verk))
        for r in _strom(conn, f"SELECT r.*, ps.verk_id FROM {pf}pastaende_relation r "
                              f"JOIN {pf}pastaende p ON p.id = r.fran_id "
                              f"JOIN {pf}passage ps ON ps.id = p.passage_id"):
            ut.skriv(kallgraf(r["verk_id"]), m.pastaende_relation(r))

        log.info("Register")
        namnformer: dict[str, list[dict]] = defaultdict(list)
        for r in _strom(conn, f"SELECT * FROM {pf}entitet_namnform ORDER BY entitet_id, namnform"):
            namnformer[r["entitet_id"]].append(r)
        platsuppgifter = {r["entitet_id"]: r for r in _strom(conn, f"SELECT * FROM {pf}plats_uppgift")}
        for r in _strom(conn, f"SELECT * FROM {pf}entitet ORDER BY id"):
            r["extra"] = _json(r.get("extra"))
            ut.skriv("register", m.entitet(r, namnformer.get(r["id"], ()), platsuppgifter.get(r["id"])))
            ut.skriv("lankar", m.entitetens_lankar(r, r.get("wikidata_id")))
        del namnformer, platsuppgifter
        for r in _strom(conn, f"SELECT * FROM {pf}term ORDER BY id"):
            ut.skriv("register", m.term(r))
        for r in _strom(conn, f"SELECT * FROM {pf}begreppsrelation"):
            ut.skriv("register", m.begreppsrelation(r))
        for r in _strom(conn, f"SELECT * FROM {pf}ordboksartikel ORDER BY id"):
            ut.skriv(f"kallsamling/{r['kallsamling_id']}", m.ordboksartikel(r))

        log.info("Identifieringar och bedömningar")
        for r in _strom(conn, f"SELECT * FROM {pf}identifiering ORDER BY id"):
            ut.skriv("bedomningar", m.identifiering(r))
        for r in _strom(conn, f"SELECT * FROM {pf}bedomning ORDER BY id"):
            ut.skriv("bedomningar", m.bedomning(r))

        log.info("Längder")
        langder = list(_strom(conn, f"SELECT * FROM {pf}auktoritetslangd ORDER BY id"))
        for r in langder:
            ut.skriv(f"langd/{r['id']}", m.langd(r))
        for r in _strom(conn, f"SELECT * FROM {pf}auktoritet_titel ORDER BY langd_id, person_id, nr"):
            ut.skriv(f"langd/{r['langd_id']}", m.langd_titel(r))
        for r in _strom(conn, f"SELECT * FROM {pf}auktoritet ORDER BY langd_id, person_id"):
            ut.skriv("lankar", m.auktoritetens_lankar(r))
    finally:
        conn.close()

    log.info("Metadata")
    ut.skriv("metadata", _metadata(ut.antal, kallsamlingar, langder))
    ut.stang()
    return ut


def _extra_vokabular() -> Iterator[m.Trippel]:
    """Det som URI:erna pekar på men som inte står i vokabular.py."""
    register = m.I(m.BEGREPPSREGISTER)
    yield register, m.TYP, m.p("skos", "ConceptScheme")
    yield register, m.p("skos", "prefLabel"), m.L("Fornmeds begreppsregister", "sv")
    sprak = m.I(rdf_uri.vokabular_uri("sprak"))
    fsv = m.vok("sprak", "fsv")
    yield sprak, m.TYP, m.p("skos", "ConceptScheme")
    yield sprak, m.p("skos", "prefLabel"), m.L("Språk utan ISO 639-3-kod", "sv")
    yield fsv, m.TYP, m.p("skos", "Concept")
    yield fsv, m.p("skos", "inScheme"), sprak
    yield fsv, m.p("skos", "prefLabel"), m.L("fornsvenska", "sv")
    yield fsv, m.p("skos", "notation"), m.L("fsv")


def _metadata(antal: Counter, kallsamlingar: list[dict], langder: list[dict]) -> Iterator[m.Trippel]:
    """
    VoID-beskrivning: hela datamängden och en deldatamängd per graf, med
    licens och antal tripler. Källsamlingarna beskrivs också här.
    """
    void = lambda namn: m.I(VOID + namn)  # noqa: E731
    helhet = m.I(rdf_uri.BAS)
    yield helhet, m.TYP, void("Dataset")
    yield helhet, m.p("dcterms", "title"), m.L("Fornmed", "sv")
    yield helhet, m.p("dcterms", "description"), m.L(
        "Källor till Sveriges och Nordens forntid och medeltid, med påståenden och forskningens bedömningar.", "sv")
    yield helhet, m.p("dcterms", "license"), m.I(m.CC0)
    yield helhet, m.p("dcterms", "rights"), m.L(
        "Fornmeds egna uppgifter är CC0. Ange gärna Fornmed som källa. Källsamlingarnas grafer har källsamlingens licens.",
        "sv")
    yield helhet, void("uriSpace"), m.L(rdf_uri.ID)
    yield helhet, void("vocabulary"), m.I(rdf_uri.DEF)
    yield helhet, void("triples"), m.heltal(sum(antal.values()))

    licenstext = {f"kallsamling/{k['id']}": k.get("licens") for k in kallsamlingar}
    licenstext.update({f"langd/{lg['id']}": lg.get("licens") for lg in langder})
    for k in kallsamlingar:
        yield from m.kallsamling(k)

    for graf, n in sorted(antal.items()):
        g = m.I(rdf_uri.graf_uri(graf))
        yield helhet, void("subset"), g
        yield g, m.TYP, void("Dataset")
        yield g, void("triples"), m.heltal(n)
        yield g, void("dataDump"), m.I(f"https://fornmed.se/data/rdf/{Skrivare.filnamn(graf)}")
        if graf.startswith("kallsamling/"):
            yield g, m.p("dcterms", "source"), m.post("kallsamling", graf.split("/", 1)[1])
        if graf.startswith("langd/"):
            yield g, m.p("dcterms", "source"), m.post("langd", graf.split("/", 1)[1])
        text = licenstext.get(graf)
        if text:
            yield g, m.p("dcterms", "rights"), m.L(text, "sv")
            for uri in m.licens_uri(text):
                yield g, m.p("dcterms", "license"), m.I(uri)
        else:
            # Fornmeds egna grafer, och källsamlingar och längder som projektet
            # självt har sammanställt och därför saknar egen licenstext
            yield g, m.p("dcterms", "license"), m.I(m.CC0)


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("-o", "--ut", type=Path, required=True, help="katalog för filerna")
    tolk.add_argument("--kontrollera", action="store_true",
                      help="rapportera länkar till Fornmed-poster som inte finns i exporten")
    args = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    start = time.monotonic()
    ut = exportera(args.ut, args.kontrollera)
    for graf, n in sorted(ut.antal.items()):
        print(f"{n:>10}  {Skrivare.filnamn(graf)}")
    print(f"{sum(ut.antal.values()):>10}  tripler totalt, {time.monotonic() - start:.0f} s")

    if args.kontrollera:
        saknade = ut.saknade()
        if not saknade:
            print("Alla länkar till Fornmed-poster pekar på poster som finns.")
        for typ, fall in sorted(saknade.items()):
            print(f"Saknas: {len(fall)} {typ}, t.ex. {fall[0][0]} (från {fall[0][1]})")
        if saknade:
            sys.exit(1)


if __name__ == "__main__":
    main()

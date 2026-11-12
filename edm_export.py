"""
Skriver Fornmeds verk som Europeana Data Model (EDM): en gzippad RDF/XML-fil per
källsamling, för den som vill skörda Fornmed med Europeanas modell.

Profilen härleds ur samma tabeller som RDF-exporten. Varje verk blir ett
edm:ProvidedCHO med verkets URI och en ore:Aggregation (…#aggregation), och
dateringen, orterna, utfärdaren och genren blir edm:TimeSpan, edm:Place,
edm:Agent och skos:Concept med länkar till Wikidata. Beskrivningar och
överväganden finns i lankade_data/README.md, avsnittet EDM-profil. I korthet:

- Metadatan är Fornmeds egen och CC0, som Europeanas avtal kräver: titel,
  Fornmeds beskrivning, språk, genre, datering, orter, utfärdare och länkar.
  Regester och texter ur källorna tas inte med; de nås genom edm:isShownAt.
- Fornmed är edm:dataProvider och edm:provider; källans utgivare står i dc:source.
- edm:isShownAt är verkets sida på fornmed.se och dc:relation källans egen sida.
- edm:rights följer källsamlingens licens (RATTIGHETER). Rundata, vars villkor
  saknar motsvarighet bland Europeanas rättighetsangivelser, tas inte med.
- edm:type är TEXT för alla verk. Verk utan känt språk tas inte med, eftersom
  Europeana kräver dc:language för TEXT.

Med --kontrollera prövas filerna mot Europeanas XSD (europeana/metis-schema,
version XSD_VERSION, som hämtas till data/raw/edm_xsd/ första gången) och mot
SHACL-formerna i lankade_data/former_edm.ttl, som också uttrycker de
Schematron-regler i Europeanas schema som XSD inte prövar.

    python edm_export.py -o rdf/edm
    python edm_export.py --kontrollera rdf/edm
"""

import argparse
import gzip
import logging
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import db
import rdf_mappning as m
import rdf_uri

log = logging.getLogger("edm_export")

KATALOG = Path(__file__).parent
FORMER = KATALOG / "lankade_data" / "former_edm.ttl"
XSD_VERSION = "v14.1"
XSD_KATALOG = KATALOG / "data" / "raw" / "edm_xsd" / XSD_VERSION
XSD_FILER = (
    "ADMS.xsd", "AS.xsd", "CC.xsd", "CONTEXTS.xsd", "DC.xsd", "DCAT.xsd", "DCTERMS.xsd", "DOAP.xsd",
    "DQV.xsd", "EBUCORE.xsd", "EDM-COMMON-MAIN.xsd", "EDM-EXTERNAL-MAIN.xsd", "EDM-INTERNAL-MAIN.xsd",
    "EDM-INTERNAL.xsd", "EDM.xsd", "ENRICHMENT.xsd", "FOAF.xsd", "OA.xsd", "ODRL.xsd", "ORE.xsd", "OWL.xsd",
    "PROV.xsd", "RDAGR2.xsd", "RDF.xsd", "RDFS.xsd", "SCHEMA.xsd", "SKOS.xsd", "SVCS.xsd", "WDRS.xsd",
    "WGS84.xsd", "xml.xsd",
)
XSD_URL = f"https://raw.githubusercontent.com/europeana/metis-schema/{XSD_VERSION}/src/main/resources/schema_xsds/"

LEVERANTOR = "Fornmed"

# Europeanas rättighetsangivelser skrivs med http, som deras schema kräver
CC_BY = "http://creativecommons.org/licenses/by/4.0/"
CC_BY_SA = "http://creativecommons.org/licenses/by-sa/4.0/"
CC_BY_NC_SA = "http://creativecommons.org/licenses/by-nc-sa/4.0/"
PDM = "http://creativecommons.org/publicdomain/mark/1.0/"
CNE = "http://rightsstatements.org/vocab/CNE/1.0/"

# edm:rights gäller Fornmeds sida med regest, text och översättning, och följer
# därför källsamlingens licens. CNE (upphovsrätten inte bedömd) där regesterna är
# moderna texter utan angiven licens. En samling som saknas här tas inte med.
RATTIGHETER = {
    "sdhk": CC_BY,
    "fornsvenska_lagar": CC_BY,
    "fornsvenska_kronikor": CC_BY,
    "fornsvenska_texter": CC_BY,
    "openmgh": CC_BY,
    "romerska": CC_BY_SA,
    "wikisource": CC_BY_SA,
    "openiti": CC_BY_NC_SA,
    "sagor_heimskringla": PDM,
    "eddan": PDM,
    "heimskringla_no": PDM,
    "storm_mhn": PDM,
    "beowulf": PDM,
    "saxo": PDM,
    "ynglingatal": PDM,
    "liber_monstrorum": PDM,
    "runeberg_olmagnus": PDM,
    "ottar_wulfstan": PDM,
    "dn": CNE,
    "di": CNE,
    "df": CNE,
    "snorres_edda": CNE,
}

# Fornsvenska saknar ISO 639-kod och anges som svenska
SPRAK = {"fsv": "swe"}

NAMNRUM = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "ore": "http://www.openarchives.org/ore/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "wgs84_pos": "http://www.w3.org/2003/01/geo/wgs84_pos#",
}
WD = "http://www.wikidata.org/entity/"


def _text(namn: str, varde, sprak: str | None = None) -> str:
    lang = f" xml:lang={quoteattr(sprak)}" if sprak else ""
    return f"<{namn}{lang}>{escape(str(varde))}</{namn}>"


def _ref(namn: str, uri: str) -> str:
    return f"<{namn} rdf:resource={quoteattr(uri)}/>"


def _dag(heltal: int, slut: bool) -> str:
    """ÅÅÅÅMMDD som ÅÅÅÅ-MM-DD; en dag som inte finns blir månadens sista eller första."""
    a, m, d = heltal // 10000, heltal // 100 % 100, heltal % 100
    m = min(max(m, 1), 12)
    for dag in range(d, 0, -1) if slut else range(max(d, 1), 32):
        try:
            return date(a, m, dag).isoformat() if a > 0 else f"{a:04d}-{m:02d}-{dag:02d}"
        except ValueError:
            continue
    return f"{a:04d}-{m:02d}-01"


class Skrivare:
    """En RDF/XML-fil per källsamling; varje kontextklass skrivs en gång per fil."""

    def __init__(self, katalog: Path):
        self.katalog = katalog
        self.filer: dict[str, gzip.GzipFile] = {}
        self.skrivna: dict[str, set[str]] = defaultdict(set)
        self.antal: Counter[str] = Counter()

    def fil(self, samling: str):
        f = self.filer.get(samling)
        if f is None:
            f = self.filer[samling] = gzip.open(self.katalog / f"{samling}.xml.gz", "wt", encoding="utf-8")
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<rdf:RDF')
            for prefix, uri in NAMNRUM.items():
                f.write(f"\n    xmlns:{prefix}={quoteattr(uri)}")
            f.write(">\n")
        return f

    def kontext(self, samling: str, uri: str, xml: str) -> None:
        if uri not in self.skrivna[samling]:
            self.skrivna[samling].add(uri)
            self.fil(samling).write(xml)

    def stang(self) -> None:
        for f in self.filer.values():
            f.write("</rdf:RDF>\n")
            f.close()


def _rader(cur, sql: str, *param) -> list[dict]:
    cur.execute(sql, param)
    kolumner = [k[0] for k in cur.description]
    return [dict(zip(kolumner, r)) for r in cur.fetchall()]


def exportera(katalog: Path) -> tuple[Counter, Counter]:
    katalog.mkdir(parents=True, exist_ok=True)
    for gammal in katalog.glob("*.xml.gz"):
        gammal.unlink()
    p = db._prefix()
    conn = db._hamta_db()
    ut = Skrivare(katalog)
    utelamnade: Counter[str] = Counter()
    try:
        cur = conn.cursor()
        samlingar = {r["id"]: r for r in _rader(cur, f"SELECT id, namn, utgivare FROM {p}kallsamling")}
        genrer = {r["kod"]: r["etikett"] for r in _rader(cur, f"SELECT kod, etikett FROM {p}vokabular WHERE schema = 'genre'")}
        # Wikidata-id ur registret och ur längderna
        wikidata = {r["id"]: r["wikidata_id"] for r in _rader(
            cur, f"SELECT id, wikidata_id FROM {p}entitet WHERE wikidata_id IS NOT NULL")}
        for r in _rader(cur, f"SELECT person_id, wikidata_id FROM {p}auktoritet WHERE wikidata_id IS NOT NULL"):
            wikidata.setdefault(r["person_id"], r["wikidata_id"])
        platser: dict[str, list[str]] = defaultdict(list)
        for r in _rader(cur, f"""SELECT verk_id, plats_id FROM {p}verk_plats
                                 WHERE roll IN ('utfardandeort', 'fyndplats') AND NOT osaker ORDER BY verk_id, plats_id"""):
            platser[r["verk_id"]].append(r["plats_id"])
        plats_info = {r["id"]: r for r in _rader(cur, f"""SELECT e.id, e.namn, u.latitud, u.longitud FROM {p}entitet e
                                                         LEFT JOIN {p}plats_uppgift u ON u.entitet_id = e.id
                                                         WHERE e.typ IN ('plats', 'indelning')""")}
        utfardare: dict[str, list[str]] = defaultdict(list)
        for r in _rader(cur, f"""SELECT DISTINCT objekt_varde AS verk_id, subjekt_id FROM {p}pastaende
                                 WHERE predikat = 'utfardar' AND objekt_varde IS NOT NULL ORDER BY 1, 2"""):
            utfardare[r["verk_id"]].append(r["subjekt_id"])
        personer = {r["id"]: r["namn"] for r in _rader(cur, f"SELECT id, namn FROM {p}entitet WHERE typ = 'person'")}

        for v in _rader(cur, f"""SELECT id, titel, kallsamling_id, genre, sprak, beskrivning, extern_url,
                                        datering_edtf, datering_fran, datering_till FROM {p}verk ORDER BY id"""):
            samling = v["kallsamling_id"]
            if samling not in RATTIGHETER:
                utelamnade[f"källsamling {samling} (ingen rättighetsangivelse)"] += 1
                continue
            sprak = list(dict.fromkeys(SPRAK.get(s, s) for s in (v["sprak"] or [])))
            if not sprak:
                utelamnade["utan språk"] += 1
                continue
            cho = rdf_uri.uri("verk", v["id"])
            f = ut.fil(samling)
            delar = [_text("dc:title", v["titel"])]
            if v["beskrivning"]:
                delar.append(_text("dc:description", v["beskrivning"], "sv"))
            delar += [_text("dc:language", s) for s in sprak]
            delar.append(_text("dc:identifier", v["id"]))
            if v["genre"]:
                genre_uri = rdf_uri.vokabular_uri("genre", v["genre"])
                delar.append(_ref("dc:type", genre_uri))
                ut.kontext(samling, genre_uri, (
                    f'  <skos:Concept rdf:about={quoteattr(genre_uri)}>'
                    f'{_text("skos:prefLabel", genrer.get(v["genre"], v["genre"]), "sv")}'
                    f'{_text("skos:notation", v["genre"])}'
                    f'{_ref("skos:inScheme", rdf_uri.vokabular_uri("genre"))}</skos:Concept>\n'))
            for person in utfardare.get(v["id"], []):
                if person not in personer:
                    continue
                agent = rdf_uri.uri("entitet", person)
                delar.append(_ref("dc:creator", agent))
                same = _ref("owl:sameAs", WD + wikidata[person]) if person in wikidata else ""
                ut.kontext(samling, agent, f'  <edm:Agent rdf:about={quoteattr(agent)}>'
                                           f'{_text("skos:prefLabel", personer[person])}{same}</edm:Agent>\n')
            info = samlingar.get(samling) or {}
            if info.get("utgivare"):
                delar.append(_text("dc:source", info["utgivare"]))
            if v["extern_url"]:
                delar.append(_ref("dc:relation", m.I(v["extern_url"])[1:-1]))
            if v["datering_fran"] is not None and v["datering_till"] is not None:
                tid = f"{cho}#tid"
                delar.append(_ref("dcterms:created", tid))
                ut.kontext(samling, tid, f'  <edm:TimeSpan rdf:about={quoteattr(tid)}>'
                                         f'{_text("skos:prefLabel", v["datering_edtf"] or "")}'
                                         f'{_text("edm:begin", _dag(v["datering_fran"], False))}'
                                         f'{_text("edm:end", _dag(v["datering_till"], True))}</edm:TimeSpan>\n')
            if info.get("namn"):
                delar.append(_text("dcterms:isPartOf", info["namn"], "sv"))
            for plats in platser.get(v["id"], []):
                pi = plats_info.get(plats)
                if not pi:
                    continue
                puri = rdf_uri.uri("entitet", plats)
                delar.append(_ref("dcterms:spatial", puri))
                lage = (_text("wgs84_pos:lat", pi["latitud"]) + _text("wgs84_pos:long", pi["longitud"])
                        if pi["latitud"] is not None and pi["longitud"] is not None else "")
                same = _ref("owl:sameAs", WD + wikidata[plats]) if plats in wikidata else ""
                ut.kontext(samling, puri, f'  <edm:Place rdf:about={quoteattr(puri)}>{lage}'
                                          f'{_text("skos:prefLabel", pi["namn"])}{same}</edm:Place>\n')
            delar.append(_text("edm:type", "TEXT"))
            f.write(f'  <edm:ProvidedCHO rdf:about={quoteattr(cho)}>{"".join(delar)}</edm:ProvidedCHO>\n')
            f.write(f'  <ore:Aggregation rdf:about={quoteattr(cho + "#aggregation")}>'
                    f'{_ref("edm:aggregatedCHO", cho)}'
                    f'{_text("edm:dataProvider", LEVERANTOR)}'
                    f'{_ref("edm:isShownAt", rdf_uri.WEBB.rstrip("/") + rdf_uri.verkets_sida(v["id"]))}'
                    f'{_text("edm:provider", LEVERANTOR)}'
                    f'{_ref("edm:rights", RATTIGHETER[samling])}</ore:Aggregation>\n')
            ut.antal[samling] += 1
    finally:
        conn.close()
        ut.stang()
    return ut.antal, utelamnade


# -----------------------------------------------------------------------------
# Kontroll
# -----------------------------------------------------------------------------

def hamta_xsd() -> Path:
    """Europeanas XSD i den låsta versionen, hämtad en gång till data/raw/edm_xsd/."""
    XSD_KATALOG.mkdir(parents=True, exist_ok=True)
    for namn in XSD_FILER:
        mal = XSD_KATALOG / namn
        if not mal.exists():
            with urllib.request.urlopen(XSD_URL + namn, timeout=60) as svar:
                mal.write_bytes(svar.read())
    return XSD_KATALOG / "EDM.xsd"


def kontrollera(katalog: Path, bit: int = 2000) -> list[str]:
    """Fel i filerna: brott mot Europeanas XSD och mot SHACL-formerna."""
    from lxml import etree
    from pyshacl import validate
    from rdflib import Graph, Namespace, URIRef

    schema = etree.XMLSchema(etree.parse(str(hamta_xsd())))
    former = Graph().parse(FORMER, format="turtle")
    sh = Namespace("http://www.w3.org/ns/shacl#")
    edm = Namespace(NAMNRUM["edm"])
    rdf_typ = URIRef(NAMNRUM["rdf"] + "type")
    fel: list[str] = []
    filer = sorted(katalog.glob("*.xml.gz"))
    if not filer:
        return [f"inga .xml.gz-filer i {katalog}"]
    for fil in filer:
        start = time.time()
        with gzip.open(fil, "rb") as f:
            dokument = etree.parse(f)
        if not schema.validate(dokument):
            for e in list(schema.error_log)[:10]:
                fel.append(f"{fil.name}: XSD rad {e.line}: {e.message}")
        g = Graph().parse(data=etree.tostring(dokument), format="xml")
        cho = sorted(g.subjects(rdf_typ, edm.ProvidedCHO))
        # Varje bit innehåller verken, deras aggregationer och de kontextklasser de pekar på
        for i in range(0, len(cho), bit):
            del_ = Graph()
            noder = set()
            for c in cho[i:i + bit]:
                noder |= {c, URIRef(str(c) + "#aggregation")}
            for n in list(noder):
                for _, _, o in g.triples((n, None, None)):
                    if isinstance(o, URIRef) and (o, None, None) in g:
                        noder.add(o)
            for n in noder:
                for t in g.triples((n, None, None)):
                    del_.add(t)
            ok, resultat, _ = validate(del_, shacl_graph=former, inference="none")
            if not ok:
                for r in list(resultat.subjects(sh.resultSeverity, None))[:10]:
                    fel.append(f"{fil.name}: {resultat.value(r, sh.focusNode)} {resultat.value(r, sh.resultPath)}: "
                               f"{resultat.value(r, sh.resultMessage)}")
        log.info("%s: %d verk kontrollerade, %.0f s", fil.name, len(cho), time.time() - start)
    return fel


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    grupp = tolk.add_mutually_exclusive_group(required=True)
    grupp.add_argument("-o", "--ut", type=Path, help="katalog för filerna")
    grupp.add_argument("--kontrollera", type=Path, metavar="KATALOG", help="pröva filerna i katalogen")
    args = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    if args.ut:
        start = time.monotonic()
        antal, utelamnade = exportera(args.ut)
        for samling, n in sorted(antal.items()):
            print(f"{n:>8}  {samling}.xml.gz")
        print(f"{sum(antal.values()):>8}  verk i EDM-profilen, {time.monotonic() - start:.0f} s")
        for orsak, n in sorted(utelamnade.items()):
            print(f"{n:>8}  utelämnade: {orsak}")
        return

    fel = kontrollera(args.kontrollera)
    for rad in fel[:50]:
        print(rad)
    print("EDM-profilen klarar Europeanas XSD och SHACL-formerna." if not fel else f"{len(fel)} fel.")
    if fel:
        sys.exit(1)


if __name__ == "__main__":
    main()

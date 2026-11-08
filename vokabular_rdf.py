"""
Skriver ut Fornmeds kontrollerade vokabulär som SKOS i Turtle.

Varje axel i vokabular.py (genre, predikat, historicitet …) blir ett
skos:ConceptScheme och varje värde ett skos:Concept med svensk etikett,
beskrivning och koden som skos:notation. Kopplingarna till andra modellers
egenskaper läses ur lankade_data/vokabular_mappning.ttl och tas med.

Vokabuläret läses ur koden och inte ur databasen, så skriptet kan köras utan
databasanslutning.

    python vokabular_rdf.py                       # till standard ut
    python vokabular_rdf.py -o vokabular.ttl
"""

import argparse
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

import rdf_uri
from vokabular import VOKABULAR

FM = Namespace(rdf_uri.DEF)
MAPPNING = Path(__file__).parent / "lankade_data" / "vokabular_mappning.ttl"
CC0 = URIRef("https://creativecommons.org/publicdomain/zero/1.0/")

# Axlarnas namn som etiketter. Axlar som saknas här får sitt schemanamn.
AXLAR = {
    "akthet": "Äkthet",
    "bedomningsaspekt": "Bedömningsaspekt",
    "begreppsrelation": "Begreppsrelation",
    "brevkoppling": "Brevkoppling",
    "deltyp": "Deltyp",
    "entitetstyp": "Entitetstyp",
    "extraktion": "Extraktion",
    "genre": "Genre",
    "historicitet": "Historicitet",
    "identifiering": "Identifiering",
    "korroboration": "Korroboration",
    "passagetyp": "Passagetyp",
    "pastaenderelation": "Påståenderelation",
    "platsroll": "Platsroll",
    "platsslag": "Platsslag",
    "predikat": "Predikat",
    "sakerhet": "Säkerhet",
    "sokplatsroll": "Platsroll i sökindexet",
    "termtyp": "Termtyp",
    "titulatur": "Titulatur",
    "utgaveroll": "Utgåveroll",
    "utgavetyp": "Utgåvetyp",
    "vittnestyp": "Vittnestyp",
}


BEGREPPSREGISTER = URIRef(rdf_uri.ID + "begreppsregister")


def _utanfor_vokabular(g: Graph) -> None:
    """
    Det som exporten pekar på men som inte står i vokabular.py: begreppsregistret
    som schema för entiteterna av typen begrepp och ämbete, språk utan ISO 639-3-kod
    och bedömningarnas sanningsvärde.
    """
    g.add((BEGREPPSREGISTER, RDF.type, SKOS.ConceptScheme))
    g.add((BEGREPPSREGISTER, SKOS.prefLabel, Literal("Fornmeds begreppsregister", lang="sv")))
    g.add((BEGREPPSREGISTER, DCTERMS.license, CC0))
    for schema, etikett, kod, kod_etikett, definition in (
            ("sprak", "Språk utan ISO 639-3-kod", "fsv", "fornsvenska", None),
            ("sanningsvarde", "Sanningsvärde", "sant", "sant",
             "Bedömaren håller propositionen för sann. Hur säker bedömningen är anges med säkerhet.")):
        schema_uri = URIRef(rdf_uri.vokabular_uri(schema))
        g.add((schema_uri, RDF.type, SKOS.ConceptScheme))
        g.add((schema_uri, SKOS.prefLabel, Literal(etikett, lang="sv")))
        g.add((schema_uri, DCTERMS.license, CC0))
        varde = URIRef(rdf_uri.vokabular_uri(schema, kod))
        g.add((varde, RDF.type, SKOS.Concept))
        g.add((varde, SKOS.inScheme, schema_uri))
        g.add((varde, SKOS.topConceptOf, schema_uri))
        g.add((varde, SKOS.prefLabel, Literal(kod_etikett, lang="sv")))
        g.add((varde, SKOS.notation, Literal(kod)))
        if definition:
            g.add((varde, SKOS.definition, Literal(definition, lang="sv")))


def bygg_graf() -> Graph:
    """Vokabuläret som en rdflib-graf, med kopplingarna till andra modeller."""
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("fm", FM)

    scheman: set[str] = set()
    for ordning, (schema, kod, etikett, beskrivning) in enumerate(VOKABULAR):
        schema_uri = URIRef(rdf_uri.vokabular_uri(schema))
        if schema not in scheman:
            scheman.add(schema)
            g.add((schema_uri, RDF.type, SKOS.ConceptScheme))
            g.add((schema_uri, SKOS.prefLabel, Literal(AXLAR.get(schema, schema), lang="sv")))
            g.add((schema_uri, DCTERMS.license, CC0))
        begrepp = URIRef(rdf_uri.vokabular_uri(schema, kod))
        g.add((begrepp, RDF.type, SKOS.Concept))
        g.add((begrepp, SKOS.inScheme, schema_uri))
        g.add((begrepp, SKOS.topConceptOf, schema_uri))
        g.add((begrepp, SKOS.prefLabel, Literal(etikett, lang="sv")))
        g.add((begrepp, SKOS.notation, Literal(kod)))
        if beskrivning:
            g.add((begrepp, SKOS.definition, Literal(beskrivning, lang="sv")))

    _utanfor_vokabular(g)
    mappning = Graph().parse(MAPPNING, format="turtle")
    okanda = {str(s) for s in mappning.subjects() if (s, RDF.type, SKOS.Concept) not in g}
    if okanda:
        raise ValueError(f"vokabular_mappning.ttl nämner värden som inte finns i vokabular.py: {sorted(okanda)}")
    g += mappning
    return g


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("-o", "--ut", type=Path, help="fil att skriva till (standard ut om den utelämnas)")
    args = tolk.parse_args()

    turtle = bygg_graf().serialize(format="turtle")
    if args.ut:
        args.ut.write_text(turtle, encoding="utf-8")
    else:
        sys.stdout.write(turtle)


if __name__ == "__main__":
    main()

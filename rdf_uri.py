"""
URI:er för Fornmeds länkade data.

Varje post får en beständig URI under https://w3id.org/fornmed/, byggd av
samma id som i databasen, API:et och MCP-servern. w3id.org vidarebefordrar
URI:erna till fornmed.se, som svarar med webbsida eller RDF.

URI:erna skrivs alltid i ASCII. Tecken som inte får stå i en URI-sökväg, och
alla tecken utanför ASCII, procentkodas med UTF-8: mellanslag blir %20 och
härad blir h%C3%A4rad. I RDF jämförs URI:er tecken för tecken, så samma post
måste alltid skrivas på samma sätt.
"""

import urllib.parse

BAS = "https://w3id.org/fornmed/"
# Webbplatsen som w3id.org vidarebefordrar till, med SPARQL-ändpunkten och dumpfilerna
WEBB = "https://fornmed.se/"
SPARQL = WEBB + "sparql"
DUMPAR = WEBB + "data/rdf/"
DEF = BAS + "def/"
ID = BAS + "id/"
GRAF = BAS + "graf/"

# Posttyperna i sökvägen. Typen är generaliserad: personer, platser och
# begrepp är alla `entitet`, eftersom en entitets typ kan ändras när
# forskningen ändras men URI:n aldrig får göra det.
TYPER = (
    "kallsamling", "verk", "vittne", "utgava", "passage", "entitet",
    "pastaende", "identifiering", "bedomning", "term", "ordboksartikel",
    "langd", "omnamnande", "datering", "koppling",
)

# Kolon är tillåtet i en sökväg och ingår i nästan alla id, så det kodas inte.
# Snedstreck kodas, så att ett id aldrig kan läsas som flera sökvägsdelar.
_SAKRA_TECKEN = ":@!$&'()*+,;=-._~"


def koda(del_: str) -> str:
    """Procentkodar en sökvägsdel enligt reglerna ovan."""
    return urllib.parse.quote(del_, safe=_SAKRA_TECKEN)


def uri(typ: str, post_id: str) -> str:
    """URI:n för en post av typen `typ` med databasens id `post_id`."""
    if typ not in TYPER:
        raise ValueError(f"okänd posttyp: {typ}")
    if not post_id:
        raise ValueError("id saknas")
    return f"{ID}{typ}/{koda(post_id)}"


def vokabular_uri(schema: str, kod: str | None = None) -> str:
    """URI:n för ett vokabulär, eller för ett värde i det om `kod` anges."""
    bas = f"{ID}vokabular/{koda(schema)}"
    return bas if kod is None else f"{bas}/{koda(kod)}"


def graf_uri(namn: str) -> str:
    """URI:n för en namngiven graf, till exempel kallsamling/sdhk eller register."""
    return GRAF + "/".join(koda(d) for d in namn.split("/"))

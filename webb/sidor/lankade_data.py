"""
Schema.org-beskrivningar (JSON-LD) för verkens och entiteternas sidor.

Varje sida får en enkel beskrivning i Schema.org, som sökmotorer och andra
tjänster läser, med postens beständiga URI som @id. Den fullständiga
beskrivningen i CIDOC CRM finns under samma URI som Turtle eller JSON-LD; sidan
länkar dit med <link rel="alternate">.

URI-reglerna är desamma som i projektets rdf_uri.py: ASCII, och tecken som
inte får stå i en URI-sökväg procentkodas.
"""

import re
import urllib.parse

ID = "https://w3id.org/fornmed/id/"
_SAKRA_TECKEN = ":@!$&'()*+,;=-._~"

# Schema.org vill ha språk som BCP 47, alltså tvåbokstavskoder där sådana finns
_TVABOKSTAV = {"swe": "sv", "dan": "da", "isl": "is", "lat": "la", "nor": "no", "eng": "en",
               "deu": "de", "rus": "ru", "nld": "nl", "ara": "ar", "fra": "fr", "ita": "it"}

_ENTITETSTYP = {
    "person": "Person", "plats": "Place", "indelning": "AdministrativeArea",
    "institution": "Organization", "grupp": "Organization", "begrepp": "DefinedTerm",
    "ambete": "DefinedTerm", "handelse": "Event",
}

# Schema.org-datum måste vara ISO 8601; EDTF med osäkerhet (1502-01-06?) eller
# intervall utelämnas hellre än att anges fel
_ISO_DATUM = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

FORMAT = (("text/turtle", "ttl"), ("application/ld+json", "jsonld"))


def uri(typ: str, post_id: str) -> str:
    return f"{ID}{typ}/{urllib.parse.quote(post_id, safe=_SAKRA_TECKEN)}"


def alternativ(typ: str, post_id: str) -> list[dict]:
    """Adresserna till postens RDF på den här webbplatsen, för <link rel="alternate">."""
    sokvag = f"/id/{typ}/{urllib.parse.quote(post_id, safe=_SAKRA_TECKEN)}"
    return [{"typ": mediatyp, "url": f"{sokvag}?format={kod}"} for mediatyp, kod in FORMAT]


def verk(v: dict, sidans_url: str) -> dict:
    """Ett verk som schema:CreativeWork."""
    ut = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "@id": uri("verk", v["id"]),
        "name": v.get("titel"),
        "url": sidans_url,
    }
    if v.get("upphov"):
        ut["creditText"] = v["upphov"]
    if v.get("datering_edtf") and _ISO_DATUM.match(v["datering_edtf"]):
        ut["dateCreated"] = v["datering_edtf"]
    sprak = [_TVABOKSTAV.get(k, k) for k in v.get("sprak") or []]
    if sprak:
        ut["inLanguage"] = sprak if len(sprak) > 1 else sprak[0]
    if v.get("utfardandeort"):
        ut["locationCreated"] = {"@type": "Place", "name": v["utfardandeort"]}
    if v.get("kallsamling"):
        ut["isPartOf"] = {"@type": "Collection", "name": v["kallsamling"]}
    if v.get("extern_url"):
        ut["sameAs"] = v["extern_url"]
    if v.get("licens"):
        ut["usageInfo"] = v["licens"]
    return ut


def entitet(e: dict, sidans_url: str) -> dict:
    """En entitet som schema:Person, schema:Place och så vidare."""
    ut = {
        "@context": "https://schema.org",
        "@type": _ENTITETSTYP.get(e.get("typ"), "Thing"),
        "@id": uri("entitet", e["id"]),
        "name": e.get("namn"),
        "url": sidans_url,
    }
    if e.get("beskrivning"):
        ut["description"] = e["beskrivning"]
    namnformer = sorted({n["namnform"] for n in e.get("namnformer") or [] if n.get("namnform") != e.get("namn")})
    if namnformer:
        ut["alternateName"] = namnformer
    if e.get("wikidata_id"):
        ut["sameAs"] = f"http://www.wikidata.org/entity/{e['wikidata_id']}"
    plats = e.get("plats_uppgift") or {}
    if plats.get("latitud") is not None and plats.get("longitud") is not None:
        ut["geo"] = {"@type": "GeoCoordinates", "latitude": plats["latitud"], "longitude": plats["longitud"]}
    return ut

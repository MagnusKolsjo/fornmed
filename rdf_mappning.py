"""
Översättning av Fornmeds tabeller till RDF.

Varje funktion tar en rad ur databasen (som dict) och ger tripler som tupler
(subjekt, predikat, objekt), där varje term redan är skriven i N-Triples-form:
`<https://…>` eller `"text"@sv`. Det gör att hela datamängden kan skrivas
rad för rad utan att byggas upp i minnet, och samma tripler kan läsas in i
rdflib när en enskild post ska visas som Turtle eller JSON-LD.

Modellen beskrivs i lankade_data/README.md. Delnoder som tidsintervall och
platsangivelser får hash-URI:er under postens egen URI (…/verk/sdhk:1#tid) i
stället för blanka noder, så att de är stabila mellan exporter och går att
slå upp.
"""

import urllib.parse
from collections.abc import Iterable, Iterator
from datetime import date

import rdf_uri

Trippel = tuple[str, str, str]

# -----------------------------------------------------------------------------
# Namnrum
# -----------------------------------------------------------------------------

FM = rdf_uri.DEF
CRM = "http://www.cidoc-crm.org/cidoc-crm/"
CRMINF = "http://www.cidoc-crm.org/extensions/crminf/"
LRMOO = "http://iflastandards.info/ns/lrm/lrmoo/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
SKOSXL = "http://www.w3.org/2008/05/skos-xl#"
DCTERMS = "http://purl.org/dc/terms/"
FOAF = "http://xmlns.com/foaf/0.1/"
GEO = "http://www.opengis.net/ont/geosparql#"
WGS84 = "http://www.w3.org/2003/01/geo/wgs84_pos#"
XSD = "http://www.w3.org/2001/XMLSchema#"
WD = "http://www.wikidata.org/entity/"
LEXVO = "http://lexvo.org/id/iso639-3/"
RAA_GEO = "http://kulturarvsdata.se/resurser/aukt/geo/"

BEGREPPSREGISTER = rdf_uri.ID + "begreppsregister"


# -----------------------------------------------------------------------------
# Termer i N-Triples-form
# -----------------------------------------------------------------------------

_OGILTIGA_I_IRI = str.maketrans({c: f"%{ord(c):02X}" for c in ' <>"{}|^`\\\n\r\t'})


def I(uri: str) -> str:  # noqa: E743 – kort namn eftersom det används på varje rad
    """
    En URI. Fornmeds egna URI:er är redan kodade av rdf_uri; externa adresser
    ur källorna (webbsidor, Wikipedia) kan innehålla mellanslag och andra
    tecken som inte får stå i en IRI, och de procentkodas här.
    """
    return f"<{uri.strip().translate(_OGILTIGA_I_IRI)}>"


_FLYKT = str.maketrans({"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"})


def L(text, sprak: str | None = None, typ: str | None = None) -> str:
    """En literal, med språktagg eller datatyp."""
    varde = f'"{str(text).translate(_FLYKT)}"'
    if sprak:
        return f"{varde}@{sprak}"
    if typ:
        return f"{varde}^^<{typ}>"
    return varde


def heltal(n: int) -> str:
    return L(n, typ=XSD + "integer")


def sanning(b: bool) -> str:
    return L("true" if b else "false", typ=XSD + "boolean")


def decimal(x: float) -> str:
    return L(repr(float(x)), typ=XSD + "decimal")


def ar(n: int) -> str:
    return L(f"{n:04d}", typ=XSD + "gYear")


# Prefixen ger kortare kod nedan: p("crm", "P4_has_time-span")
_NAMNRUM = {"fm": FM, "crm": CRM, "crminf": CRMINF, "lrmoo": LRMOO, "rdf": RDF, "rdfs": RDFS,
            "skos": SKOS, "skosxl": SKOSXL, "dcterms": DCTERMS, "foaf": FOAF, "geo": GEO, "wgs84": WGS84}


def p(prefix: str, namn: str) -> str:
    return I(_NAMNRUM[prefix] + namn)


TYP = p("rdf", "type")
ETIKETT = p("rdfs", "label")


def vok(schema: str, kod: str) -> str:
    return I(rdf_uri.vokabular_uri(schema, kod))


def post(typ: str, post_id: str) -> str:
    return I(rdf_uri.uri(typ, post_id))


def del_av(uri: str, fragment: str) -> str:
    """
    En delnod under en post: <…/verk/sdhk:1> och 'tid' ger <…/verk/sdhk:1#tid>.
    En delnod under en delnod förlänger fragmentet med bindestreck, eftersom
    en URI bara får ha ett #: <…/langd/regenter#person:x-1> ger
    <…/langd/regenter#person:x-1-tid>.
    """
    bas = uri[1:-1]
    skiljetecken = "-" if "#" in bas else "#"
    return I(f"{bas}{skiljetecken}{rdf_uri.koda(fragment)}")


# -----------------------------------------------------------------------------
# Språk
# -----------------------------------------------------------------------------
# Fornmed lagrar ISO 639-3. Språktaggar ska enligt BCP 47 vara den kortaste
# koden, så språk med en tvåbokstavskod skrivs med den. Fornsvenska har ingen
# ISO-kod och skrivs med ett privat undertagg.

_TVABOKSTAV = {"swe": "sv", "dan": "da", "isl": "is", "lat": "la", "nor": "no", "eng": "en",
               "deu": "de", "rus": "ru", "nld": "nl", "ara": "ar", "fra": "fr", "ita": "it"}


def spraktagg(kod: str | None) -> str | None:
    if not kod:
        return None
    if kod == "fsv":
        return "sv-x-fsv"
    return _TVABOKSTAV.get(kod, kod)


def sprak_uri(kod: str) -> str:
    return vok("sprak", kod) if kod == "fsv" else I(LEXVO + kod)


# -----------------------------------------------------------------------------
# Tid
# -----------------------------------------------------------------------------

def _datum(heltal_: int, slut: bool) -> str:
    """
    ÅÅÅÅMMDD som xsd:dateTime utan kalenderomräkning. En dag som inte finns
    i den gregorianska kalendern (29 februari 1300) flyttas utåt, så att
    intervallet blir bredare och aldrig smalare.
    """
    a, m, d = heltal_ // 10000, heltal_ // 100 % 100, heltal_ % 100
    try:
        date(a, m, d)
    except ValueError:
        m, d = (3, 1) if slut else (m, 28)
    klocka = "23:59:59" if slut else "00:00:00"
    return L(f"{a:04d}-{m:02d}-{d:02d}T{klocka}", typ=XSD + "dateTime")


def tidsintervall(nod: str, edtf: str | None, fran: int | None, till: int | None) -> Iterator[Trippel]:
    """Ett crm:E52_Time-Span med EDTF, heltalsintervall och CRM:s gränser."""
    yield nod, TYP, p("crm", "E52_Time-Span")
    if edtf:
        yield nod, p("fm", "edtf"), L(edtf)
    if fran is not None:
        yield nod, p("fm", "fran"), heltal(fran)
        yield nod, p("crm", "P82a_begin_of_the_begin"), _datum(fran, slut=False)
    if till is not None:
        yield nod, p("fm", "till"), heltal(till)
        yield nod, p("crm", "P82b_end_of_the_end"), _datum(till, slut=True)


# -----------------------------------------------------------------------------
# Licenser
# -----------------------------------------------------------------------------
# Källsamlingarnas licenser är fritext. De licenser som går att känna igen
# får en URI; texten följer alltid med som dcterms:rights.

_LICENSER = [
    ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("ODbL", "https://opendatacommons.org/licenses/odbl/1-0/"),
    ("Public domain", "https://creativecommons.org/publicdomain/mark/1.0/"),
    ("public domain", "https://creativecommons.org/publicdomain/mark/1.0/"),
]
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


# Formuleringar som säger att en del av samlingen saknar känd licens eller är
# skyddad. En licens-URI skulle då påstå mer än texten, så bara texten anges.
_OKLAR_DEL = ("inte anger", "anger inte", "upphovsrätt för", "okänd")


def licens_uri(text: str | None) -> list[str]:
    """
    Licens-URI:er som går att utläsa ur en licenstext, i den ordning de
    nämns. Tomt om någon del av samlingen har okänd eller skyddad status.
    """
    if not text or any(f in text for f in _OKLAR_DEL):
        return []
    funna: list[tuple[int, str]] = []
    rest = text
    for namn, uri in _LICENSER:
        pos = rest.find(namn)
        if pos >= 0 and uri not in [u for _, u in funna]:
            funna.append((pos, uri))
            # Ta bort träffen så att "CC BY-SA 4.0" inte också räknas som "CC BY 4.0"
            rest = rest[:pos] + " " * len(namn) + rest[pos + len(namn):]
    return [uri for _, uri in sorted(funna)]


# -----------------------------------------------------------------------------
# Källor
# -----------------------------------------------------------------------------

def kallsamling(rad: dict) -> Iterator[Trippel]:
    s = post("kallsamling", rad["id"])
    yield s, TYP, p("fm", "Kallsamling")
    yield s, ETIKETT, L(rad["namn"], "sv")
    yield s, p("dcterms", "title"), L(rad["namn"], "sv")
    if rad.get("utgivare"):
        yield s, p("dcterms", "publisher"), L(rad["utgivare"])
    if rad.get("url"):
        yield s, p("foaf", "page"), I(rad["url"])
    if rad.get("licens"):
        yield s, p("dcterms", "rights"), L(rad["licens"], "sv")
        for uri in licens_uri(rad["licens"]):
            yield s, p("dcterms", "license"), I(uri)
    if rad.get("version"):
        yield s, p("dcterms", "hasVersion"), L(rad["version"])
    if rad.get("importerad"):
        yield s, p("dcterms", "modified"), L(rad["importerad"].isoformat(), typ=XSD + "dateTime")


def verk(rad: dict, platser: Iterable[dict] = ()) -> Iterator[Trippel]:
    """Ett verk med tillkomst och platsangivelser (rader ur verk_plats)."""
    s = post("verk", rad["id"])
    yield s, TYP, p("fm", "Verk")
    yield s, ETIKETT, L(rad["titel"])
    yield s, p("dcterms", "title"), L(rad["titel"])
    if rad.get("kallsamling_id"):
        yield s, p("fm", "kallsamling"), post("kallsamling", rad["kallsamling_id"])
    if rad.get("genre"):
        yield s, p("fm", "genre"), vok("genre", rad["genre"])
    if rad.get("upphov"):
        yield s, p("fm", "upphov"), L(rad["upphov"])
    for kod in rad.get("sprak") or []:
        yield s, p("crm", "P72_has_language"), sprak_uri(kod)
    if rad.get("beskrivning"):
        yield s, p("dcterms", "description"), L(rad["beskrivning"], "sv")
    if rad.get("extern_url"):
        yield s, p("foaf", "page"), I(rad["extern_url"])

    platser = list(platser)
    utfardandeorter = [pl for pl in platser if pl["roll"] == "utfardandeort" and not pl["osaker"]]
    if rad.get("datering_edtf") or rad.get("datering_fran") is not None or utfardandeorter:
        tillkomst = del_av(s, "tillkomst")
        yield s, p("lrmoo", "R17i_was_created_by"), tillkomst
        yield tillkomst, TYP, p("lrmoo", "F28_Expression_Creation")
        if rad.get("datering_edtf") or rad.get("datering_fran") is not None:
            tid = del_av(s, "tid")
            yield tillkomst, p("crm", "P4_has_time-span"), tid
            yield from tidsintervall(tid, rad.get("datering_edtf"), rad.get("datering_fran"), rad.get("datering_till"))
        for pl in utfardandeorter:
            yield tillkomst, p("crm", "P7_took_place_at"), post("entitet", pl["plats_id"])
    if rad.get("datering_edtf"):
        yield s, p("dcterms", "date"), L(rad["datering_edtf"])

    for pl in platser:
        nod = del_av(s, f"plats-{pl['roll']}-{pl['plats_id']}")
        plats = post("entitet", pl["plats_id"])
        yield s, p("fm", "plats"), nod
        yield nod, TYP, p("fm", "Platsangivelse")
        yield nod, p("fm", "roll"), vok("platsroll", pl["roll"])
        yield nod, p("fm", "avser"), plats
        yield nod, p("fm", "namnform"), L(pl["namnform"])
        yield nod, p("fm", "osaker"), sanning(pl["osaker"])
        yield nod, p("fm", "harledd"), sanning(pl["harledd"])
        if not pl["osaker"]:
            if pl["roll"] == "utfardandeort":
                yield s, p("fm", "utfardandeort"), plats
            elif pl["roll"] == "fyndplats":
                yield s, p("fm", "fyndplats"), plats


def vittne(rad: dict) -> Iterator[Trippel]:
    s = post("vittne", rad["id"])
    yield s, TYP, p("fm", "Vittne")
    yield s, ETIKETT, L(rad["beskrivning"])
    yield s, p("fm", "vittnestyp"), vok("vittnestyp", rad["typ"])
    yield s, p("crm", "P128_carries"), post("verk", rad["verk_id"])
    if rad.get("signum"):
        yield s, p("fm", "signum"), L(rad["signum"])
    if rad.get("datering_edtf") or rad.get("datering_fran") is not None:
        tid = del_av(s, "tid")
        yield s, p("fm", "tillkomst"), tid
        yield from tidsintervall(tid, rad.get("datering_edtf"), rad.get("datering_fran"), rad.get("datering_till"))
    if rad.get("iiif_manifest"):
        yield s, p("dcterms", "hasFormat"), I(rad["iiif_manifest"])


def utgava(rad: dict) -> Iterator[Trippel]:
    s = post("utgava", rad["id"])
    yield s, TYP, p("fm", "Utgava")
    yield s, ETIKETT, L(rad["referens"])
    yield s, p("dcterms", "bibliographicCitation"), L(rad["referens"])
    if rad.get("verk_id"):
        yield s, p("lrmoo", "R4_embodies"), post("verk", rad["verk_id"])
    if rad.get("typ"):
        yield s, p("fm", "utgavetyp"), vok("utgavetyp", rad["typ"])
    if rad.get("sprak"):
        yield s, p("crm", "P72_has_language"), sprak_uri(rad["sprak"])
    if rad.get("oversattare"):
        yield s, p("fm", "oversattare"), L(rad["oversattare"])
    if rad.get("ar"):
        yield s, p("dcterms", "issued"), ar(rad["ar"])
    if rad.get("licens"):
        yield s, p("dcterms", "rights"), L(rad["licens"])
        for uri in licens_uri(rad["licens"]):
            yield s, p("dcterms", "license"), I(uri)


def passage(rad: dict, maskinoversatt: bool = False) -> Iterator[Trippel]:
    s = post("passage", rad["id"])
    yield s, TYP, p("fm", "Passage")
    yield s, p("crm", "P106i_forms_part_of"), post("verk", rad["verk_id"])
    if rad.get("utgava_id"):
        yield s, p("crm", "P106i_forms_part_of"), post("utgava", rad["utgava_id"])
    yield s, p("fm", "passagetyp"), vok("passagetyp", rad["typ"])
    if rad.get("adress"):
        yield s, p("fm", "adress"), L(rad["adress"])
        yield s, ETIKETT, L(rad["adress"])
    yield s, p("fm", "ordning"), heltal(rad["ordning"])
    if rad.get("sprak"):
        yield s, p("crm", "P72_has_language"), sprak_uri(rad["sprak"])
    yield s, p("crm", "P190_has_symbolic_content"), L(rad["text"], spraktagg(rad.get("sprak")))
    if rad.get("url"):
        yield s, p("foaf", "page"), I(rad["url"])
    if rad.get("del"):
        yield s, p("fm", "del"), L(rad["del"])
    if maskinoversatt:
        yield s, p("fm", "maskinoversatt"), sanning(True)


# -----------------------------------------------------------------------------
# Entiteter
# -----------------------------------------------------------------------------

ENTITETSKLASS = {
    "person": "Person", "grupp": "Grupp", "plats": "Plats", "institution": "Institution",
    "indelning": "Indelning", "ambete": "Ambete", "handelse": "Handelse", "begrepp": "Begrepp",
    "vasen": "Vasen",
}

_HIERARKI = [("land_id", "land"), ("landskap_id", "landskap"), ("lan_id", "lan"),
             ("kommun_id", "kommun"), ("socken_id", "socken")]


def entitet(rad: dict, namnformer: Iterable[dict] = (), plats: dict | None = None) -> Iterator[Trippel]:
    """En entitet med namnformer och, för platser, platsregistrets uppgifter."""
    s = post("entitet", rad["id"])
    yield s, TYP, p("fm", ENTITETSKLASS.get(rad["typ"], "Entitet"))
    yield s, ETIKETT, L(rad["namn"])
    yield s, p("skos", "prefLabel"), L(rad["namn"], "sv")
    if rad.get("beskrivning"):
        yield s, p("dcterms", "description"), L(rad["beskrivning"], "sv")
    if rad["typ"] in ("begrepp", "ambete"):
        yield s, p("skos", "inScheme"), I(BEGREPPSREGISTER)

    for nf in namnformer:
        tagg = spraktagg(nf.get("sprak"))
        nod = del_av(s, f"namn-{nf['namnform']}")
        yield s, p("crm", "P1_is_identified_by"), nod
        yield nod, TYP, p("crm", "E41_Appellation")
        yield nod, p("crm", "P190_has_symbolic_content"), L(nf["namnform"], tagg)
        if nf.get("passage_id"):
            yield nod, p("crm", "P70i_is_documented_in"), post("passage", nf["passage_id"])
        if nf["namnform"] != rad["namn"]:
            yield s, p("skos", "altLabel"), L(nf["namnform"], tagg)

    if plats:
        if plats.get("slag"):
            # Några språkmodellsbedömda platser har slaget stavat 'område';
            # vokabulärets kod är 'omrade'
            slag = "omrade" if plats["slag"] == "område" else plats["slag"]
            yield s, p("fm", "platsslag"), vok("platsslag", slag)
        if plats.get("nutida_namn"):
            yield s, p("fm", "nutidaNamn"), L(plats["nutida_namn"], "sv")
        for kolumn, egenskap in _HIERARKI:
            if plats.get(kolumn):
                yield s, p("fm", egenskap), post("entitet", plats[kolumn])
        if plats.get("ingar_i_id"):
            yield s, p("crm", "P89_falls_within"), post("entitet", plats["ingar_i_id"])
        if plats.get("latitud") is not None and plats.get("longitud") is not None:
            lat, lon = plats["latitud"], plats["longitud"]
            yield s, p("wgs84", "lat"), decimal(lat)
            yield s, p("wgs84", "long"), decimal(lon)
            geometri = del_av(s, "geometri")
            yield s, p("geo", "hasGeometry"), geometri
            yield geometri, p("geo", "asWKT"), L(f"POINT({lon} {lat})", typ=GEO + "wktLiteral")
        if plats.get("kalla"):
            yield s, p("fm", "lageKalla"), L(plats["kalla"])
        if plats.get("metod"):
            yield s, p("fm", "lageMetod"), L(plats["metod"])
        yield s, p("fm", "lageGranskat"), sanning(plats.get("granskad", False))


def entitetens_lankar(rad: dict, wikidata_id: str | None) -> Iterator[Trippel]:
    """
    Länkar till andra datamängder: Wikidata och Riksantikvarieämbetets
    geografiska auktoriteter. Sockenkoden är densamma som numret i RAÄ:s
    sockenauktoritet, och kommun- och länskoderna är SCB:s.
    """
    s = post("entitet", rad["id"])
    if wikidata_id:
        yield s, p("skos", "exactMatch"), I(WD + wikidata_id)
    delar = rad["id"].split(":")
    if len(delar) == 3 and delar[0] == "plats":
        slag, kod = delar[1], delar[2]
        if slag == "socken" and (rad.get("extra") or {}).get("raa_kod") == kod:
            yield s, p("skos", "exactMatch"), I(f"{RAA_GEO}parish#{kod}")
        elif slag == "kommun" and len(kod) == 4 and kod.isdigit():
            yield s, p("skos", "exactMatch"), I(f"{RAA_GEO}municipality#{kod}")
        elif slag == "lan" and len(kod) == 2 and kod.isdigit():
            yield s, p("skos", "exactMatch"), I(f"{RAA_GEO}county#{kod}")


def term(rad: dict) -> Iterator[Trippel]:
    s = post("term", rad["id"])
    begrepp = post("entitet", rad["entitet_id"])
    egenskap = "prefLabel" if rad["termtyp"] == "huvudterm" else "altLabel"
    yield begrepp, p("skosxl", egenskap), s
    yield s, TYP, p("skosxl", "Label")
    yield s, p("skosxl", "literalForm"), L(rad["term"], spraktagg(rad["sprak"]))
    yield s, p("fm", "termtyp"), vok("termtyp", rad["termtyp"])
    if rad.get("artikel_id"):
        yield s, p("fm", "ordboksartikel"), post("ordboksartikel", rad["artikel_id"])
    if rad.get("registrerad_av"):
        yield s, p("fm", "registreradAv"), L(rad["registrerad_av"])
    yield s, p("fm", "granskad"), sanning(rad["granskad"])


def begreppsrelation(rad: dict) -> Iterator[Trippel]:
    egenskap = {"bredare": "broader", "relaterad": "related"}.get(rad["relation"])
    if egenskap:
        yield post("entitet", rad["fran_id"]), p("skos", egenskap), post("entitet", rad["till_id"])


def ordboksartikel(rad: dict) -> Iterator[Trippel]:
    s = post("ordboksartikel", rad["id"])
    yield s, TYP, p("fm", "Ordboksartikel")
    yield s, ETIKETT, L(rad["lemma"], "sv-x-fsv")
    yield s, p("fm", "betydelseNr"), heltal(rad["betydelse_nr"])
    yield s, p("skos", "definition"), L(rad["definition"], "sv")
    if rad.get("lemgram"):
        yield s, p("fm", "lemgram"), L(rad["lemgram"])
    yield s, p("fm", "kallsamling"), post("kallsamling", rad["kallsamling_id"])


# -----------------------------------------------------------------------------
# Påståenden, identifieringar och bedömningar
# -----------------------------------------------------------------------------

def proveniens(s: str, rad: dict) -> Iterator[Trippel]:
    if rad.get("extraktion"):
        yield s, p("fm", "extraktion"), vok("extraktion", rad["extraktion"])
    if rad.get("extraherad_av"):
        yield s, p("fm", "extraheradAv"), L(rad["extraherad_av"])
    if rad.get("granskad") is not None:
        yield s, p("fm", "granskad"), sanning(rad["granskad"])
    if rad.get("granskad_av"):
        yield s, p("fm", "granskadAv"), L(rad["granskad_av"])


def pastaende(rad: dict, verk_id: set[str] | frozenset[str] = frozenset()) -> Iterator[Trippel]:
    """
    Ett påstående. `verk_id` är mängden kända verk: ett objektvärde som är ett
    verks id (utfärdaren utfärdar brevet sdhk:12136) blir en länk till verket.
    """
    s = post("pastaende", rad["id"])
    yield s, TYP, p("fm", "Pastaende")
    yield s, p("crm", "P140_assigned_attribute_to"), post("entitet", rad["subjekt_id"])
    yield s, p("crm", "P177_assigned_property_of_type"), vok("predikat", rad["predikat"])
    if rad.get("objekt_id"):
        yield s, p("crm", "P141_assigned"), post("entitet", rad["objekt_id"])
    if rad.get("objekt_varde"):
        if rad["objekt_varde"] in verk_id:
            yield s, p("crm", "P141_assigned"), post("verk", rad["objekt_varde"])
        else:
            yield s, p("fm", "objektvarde"), L(rad["objekt_varde"])
    if rad.get("plats_id"):
        yield s, p("crm", "P7_took_place_at"), post("entitet", rad["plats_id"])
    if rad.get("tid_edtf") or rad.get("tid_fran") is not None:
        tid = del_av(s, "tid")
        yield s, p("crm", "P4_has_time-span"), tid
        yield from tidsintervall(tid, rad.get("tid_edtf"), rad.get("tid_fran"), rad.get("tid_till"))
    yield s, p("crm", "P70i_is_documented_in"), post("passage", rad["passage_id"])
    if rad.get("citat"):
        yield s, p("fm", "citat"), L(rad["citat"])
    yield from proveniens(s, rad)


_PASTAENDERELATION = {"stoder": "stoder", "motsager": "motsager", "beroende_av": "beroendeAv",
                      "samma_som": "sammaSom"}


def pastaende_relation(rad: dict) -> Iterator[Trippel]:
    egenskap = _PASTAENDERELATION.get(rad["relation"])
    if egenskap:
        yield post("pastaende", rad["fran_id"]), p("fm", egenskap), post("pastaende", rad["till_id"])


def identifiering(rad: dict) -> Iterator[Trippel]:
    s = post("identifiering", rad["id"])
    yield s, TYP, p("fm", "Identifiering")
    yield s, p("fm", "entitet"), post("entitet", rad["entitet_id"])
    yield s, p("fm", "identifieradMed"), post("entitet", rad["identifierad_med"])
    if rad.get("alternativgrupp"):
        yield s, p("fm", "alternativgrupp"), L(rad["alternativgrupp"])
    if rad.get("kommentar"):
        yield s, p("rdfs", "comment"), L(rad["kommentar"], "sv")


def _publikationslank(varde: str) -> str | None:
    """En DOI eller webbadress som URI, annars None."""
    varde = varde.strip()
    if varde.startswith(("http://", "https://")):
        return varde
    if varde.lower().startswith("doi:"):
        varde = varde[4:].strip()
    if varde.startswith("10.") and "/" in varde:
        return "https://doi.org/" + varde
    return None


def bedomning(rad: dict) -> Iterator[Trippel]:
    s = post("bedomning", rad["id"])
    yield s, TYP, p("fm", "Bedomning")
    for kolumn, typ in (("pastaende_id", "pastaende"), ("verk_id", "verk"), ("vittne_id", "vittne"),
                        ("identifiering_id", "identifiering")):
        if rad.get(kolumn):
            yield s, p("crminf", "J4_that"), post(typ, rad[kolumn])
    yield s, p("fm", "aspekt"), vok("bedomningsaspekt", rad["aspekt"])
    if rad["aspekt"] == "datering":
        tid = del_av(s, "tid")
        yield s, p("crminf", "J5_holds_to_be"), tid
        yield from tidsintervall(tid, rad["varde"], None, None)
    else:
        yield s, p("crminf", "J5_holds_to_be"), vok(rad["aspekt"], rad["varde"])
    if rad.get("sakerhet"):
        yield s, p("fm", "sakerhet"), vok("sakerhet", rad["sakerhet"])
    yield s, p("fm", "bedomare"), L(rad["bedomare"])
    if rad.get("publikation"):
        yield s, p("fm", "publikation"), L(rad["publikation"])
    if rad.get("publikation_id"):
        lank = _publikationslank(rad["publikation_id"])
        if lank:
            yield s, p("crm", "P70i_is_documented_in"), I(lank)
        else:
            yield s, p("dcterms", "identifier"), L(rad["publikation_id"])
    if rad.get("sidor"):
        yield s, p("fm", "sidor"), L(rad["sidor"])
    if rad.get("motivering"):
        yield s, p("fm", "motivering"), L(rad["motivering"], "sv")
    if rad.get("ar"):
        yield s, p("fm", "ar"), ar(rad["ar"])
    if rad.get("registrerad_av"):
        yield s, p("fm", "registreradAv"), L(rad["registrerad_av"])
    yield s, p("fm", "granskad"), sanning(rad["granskad"])


# -----------------------------------------------------------------------------
# Längder
# -----------------------------------------------------------------------------

def langd(rad: dict) -> Iterator[Trippel]:
    s = post("langd", rad["id"])
    yield s, TYP, p("fm", "Langd")
    yield s, ETIKETT, L(rad["namn"], "sv")
    if rad.get("beskrivning"):
        yield s, p("dcterms", "description"), L(rad["beskrivning"], "sv")
    if rad.get("kalla"):
        yield s, p("dcterms", "source"), L(rad["kalla"])
    if rad.get("licens"):
        yield s, p("dcterms", "rights"), L(rad["licens"], "sv")
        for uri in licens_uri(rad["licens"]):
            yield s, p("dcterms", "license"), I(uri)


def langd_titel(rad: dict) -> Iterator[Trippel]:
    """En titel i en längd, som ett påstående med längden som belägg."""
    langd_uri = post("langd", rad["langd_id"])
    s = del_av(langd_uri, f"{rad['person_id']}-{rad['nr']}")
    yield s, TYP, p("fm", "Pastaende")
    yield s, p("crm", "P140_assigned_attribute_to"), post("entitet", rad["person_id"])
    yield s, p("crm", "P177_assigned_property_of_type"), vok("predikat", "innehar_ambete")
    yield s, p("fm", "objektvarde"), L(rad["titel"], "sv")
    if rad.get("sate_id"):
        yield s, p("crm", "P7_took_place_at"), post("entitet", rad["sate_id"])
    if rad.get("fran") is not None or rad.get("till") is not None:
        fran, till = rad.get("fran"), rad.get("till")
        edtf = f"{fran or ''}/{till or ''}" if fran != till else f"{fran}"
        tid = del_av(s, "tid")
        yield s, p("crm", "P4_has_time-span"), tid
        yield from tidsintervall(tid, edtf,
                                 fran * 10000 + 101 if fran is not None else None,
                                 till * 10000 + 1231 if till is not None else None)
    if rad.get("ar_text"):
        yield s, p("rdfs", "comment"), L(rad["ar_text"], "sv")
    yield s, p("crm", "P70i_is_documented_in"), langd_uri


def auktoritetens_lankar(rad: dict) -> Iterator[Trippel]:
    if rad.get("wikidata_id"):
        yield post("entitet", rad["person_id"]), p("skos", "exactMatch"), I(WD + rad["wikidata_id"])
    if rad.get("wikipedia"):
        # Längderna anger artikelns titel på svenska Wikipedia, inte en adress
        titel = rad["wikipedia"].strip()
        adress = titel if titel.startswith("http") else (
            "https://sv.wikipedia.org/wiki/" + urllib.parse.quote(titel.replace(" ", "_"), safe="()_,'-"))
        yield post("entitet", rad["person_id"]), p("foaf", "page"), I(adress)

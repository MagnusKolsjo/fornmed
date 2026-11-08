"""
REST-API för källorna, med OpenAPI-beskrivning under /openapi.json.

Allt är GET och bara läsande. Varje resurs kan hämtas som JSON, Markdown
eller text, och listor även som CSV; formatet väljs med `format=` eller
Accept-huvudet (se svarsformat.py). Dokument hämtas hela, del för del eller
som ett avsnitt, på valt språk (se dokument.py).

API:et anropar samma funktioner som MCP-verktygen (fragor.py, sok.py,
dokument.py, listor.py), så att svaren är desamma oavsett väg in. Appen körs ensam med
uvicorn eller tillsammans med MCP-servern i tjanst.py.

    uvicorn api:app --port 8424
"""

import logging
import pathlib
import threading
import urllib.parse
from typing import Annotated

# db läser .env vid import och måste därför importeras före moduler som
# läser sin konfiguration ur miljön (embeddings via sok)
import db
import dokument
import fragor
import listor
import objektsok
import rdf_post
import rdf_uri
import sok
from dokument import DokumentFel
from fastapi import FastAPI, Path, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from svarsformat import FORMAT, SLAG, aterge, valj_format

log = logging.getLogger("api")

# Högst så här många sökningar räknar embeddings samtidigt. Varje sökning
# håller en CPU-kärna i någon tiondels sekund; utan tak kan en ensam
# skrapare ta hela maskinen.
SOKNINGAR_SAMTIDIGT = threading.BoundedSemaphore(2)

MAX_PER_SIDA = 500

BESKRIVNING = """
Källor till Sveriges och Nordens forntid och medeltid: medeltidsbrev ur SDHK,
runinskrifter, landskapslagarna, sagor, krönikor och annaler, med entiteter,
påståenden om vad källorna hävdar och forskningens bedömningar av dem.

**Format.** Alla resurser finns som JSON (standard), Markdown (`format=md`) och
text (`format=txt`). Listor finns också som CSV (`format=csv`), med
pagineringen i huvudena `X-Total` och `Link`. Formatet kan också väljas med
Accept-huvudet.

**Dokument.** `/v1/verk/{verk_id}/text` ger hela verket i ett svar.
`/v1/verk/{verk_id}/delar` listar böcker, balkar och sagor, som hämtas var för
sig. `sprak=` väljer språkversion, i prioritetsordning (`sprak=swe,dan,lat`).
`parallellt=ja` med två språk ger texterna passage för passage.

**Länkade data.** Verk, passager, utgåvor, entiteter och påståenden finns som RDF
med `format=ttl`, `jsonld`, `nt` eller `rdf`. `/id/{typ}/{id}` är de beständiga
URI:erna (https://w3id.org/fornmed/id/…) och `/def/` Fornmeds klasser och egenskaper.

**Källkritik.** Svenska översättningar gjorda av språkmodell är ogranskade och
märkta så i varje svar; de bör inte citeras som översättning. Ett påstående
beskriver vad en källa hävdar, inte vad som hände. Licensen anges per utgåva.
"""

app = FastAPI(
    title="Fornmed",
    version="1",
    description=BESKRIVNING,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url=None,
)

# Öppna data: vem som helst får läsa från en webbsida på en annan domän
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"],
                   expose_headers=["X-Total", "Link"])


class _Cache:
    """Datan ändras bara vid leveranser, så lyckade svar under /v1 får cachas en stund.

    Ren ASGI-middleware: MCP-servern delar app i tjanst.py, och dess
    strömmande svar under /mcp ska passera orörda.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/v1/"):
            await self.app(scope, receive, send)
            return

        async def skicka(meddelande) -> None:
            if meddelande["type"] == "http.response.start" and meddelande["status"] == 200:
                huvuden = list(meddelande.get("headers", []))
                if not any(k.lower() == b"cache-control" for k, _ in huvuden):
                    huvuden.append((b"cache-control", b"public, max-age=300"))
                meddelande = {**meddelande, "headers": huvuden}
            await send(meddelande)

        await self.app(scope, receive, skicka)


app.add_middleware(_Cache)


# -----------------------------------------------------------------------------
# Svar i valt format
# -----------------------------------------------------------------------------

FormatParam = Annotated[str | None, Query(
    alias="format", pattern="^(json|md|txt|csv|ttl|jsonld|nt|rdf)$",
    description="json, md, txt eller csv (csv bara för listor). Verk, passager, utgåvor, entiteter och "
                "påståenden finns också som RDF: ttl, jsonld, nt eller rdf. Gäller före Accept-huvudet.")]


def _innehall(slag: str) -> dict:
    """OpenAPI-beskrivning av de format en resurs finns i."""
    return {200: {"content": {FORMAT[k].split(";")[0]: {} for k in SLAG[slag]}}}


def _svar(request: Request, data, slag: str, rader: list[dict] | None = None,
          titel: str | None = None, total: int | None = None, sida: int = 1,
          per_sida: int | None = None, omslag: dict | None = None) -> Response:
    """Svaret i det format som begärts.

    `data` är JSON-svaret. För listor är `rader` det som blir tabell i
    Markdown och CSV; utan `rader` används `data` självt. En sidindelad
    lista får i JSON ett omslag med total och sida, och med de uppgifter i
    `omslag` som gäller hela listan.
    """
    tillatna = SLAG[slag]
    fmt = valj_format(request.query_params.get("format"), request.headers.get("accept"), tillatna)
    if fmt is None:
        return JSONResponse({"fel": "Formatet finns inte för den här resursen.",
                             "format": list(tillatna)}, status_code=406)

    huvuden = {}
    if total is not None:
        huvuden["X-Total"] = str(total)
        if per_sida and sida * per_sida < total:
            nasta = request.url.include_query_params(sida=sida + 1)
            huvuden["Link"] = f'<{nasta}>; rel="next"'

    if fmt == "json":
        if total is not None:
            data = {**(omslag or {}), "total": total, "sida": sida, "per_sida": per_sida,
                    "poster": data}
        return JSONResponse(jsonable_encoder(data), headers=huvuden)
    innehall = jsonable_encoder(rader if rader is not None else data)
    return Response(aterge(innehall, slag, fmt, titel), media_type=FORMAT[fmt], headers=huvuden)


def _rdf_format(request: Request) -> str | None:
    """
    RDF-formatet om ett sådant begärts med format= eller uttryckligen i
    Accept-huvudet, annars None. Ett Accept med */* räknas inte, så att
    klienter som inte anger något fortsätter att få JSON.
    """
    begart = request.query_params.get("format")
    if begart:
        return begart if begart in rdf_post.FORMAT else None
    accept = request.headers.get("accept") or ""
    if not any(mediatyp in accept.lower() for mediatyp in rdf_post.MEDIATYP_TILL_FORMAT):
        return None
    fmt = rdf_post.valj_format(None, accept, html=False)
    if fmt is None or rdf_post.kvalitet(accept, rdf_post.FORMAT[fmt][0]) <= rdf_post.kvalitet(accept, "application/json"):
        return None
    return fmt


def _rdf_svar(typ: str, post_id: str, fmt: str) -> Response:
    """Postens beskrivning som RDF, samma som under /id/."""
    try:
        tripler = rdf_post.tripler(typ, post_id)
    except rdf_post.PostSaknas:
        raise DokumentFel(404, "Posten finns inte.")
    mediatyp = rdf_post.FORMAT[fmt][0]
    return Response(rdf_post.serialisera(tripler, fmt), media_type=f"{mediatyp}; charset=utf-8",
                    headers={"Vary": "Accept"})


def _hittad(varde, beskrivning: str):
    if varde is None:
        raise DokumentFel(404, f"{beskrivning} finns inte.")
    return varde


def _sprakkoder(sprak: str | None) -> list[str] | None:
    return [s.strip() for s in sprak.split(",") if s.strip()] if sprak else None


@app.exception_handler(DokumentFel)
async def _dokumentfel(_request: Request, fel: DokumentFel) -> JSONResponse:
    return JSONResponse(jsonable_encoder({"fel": fel.meddelande, **fel.detaljer}),
                        status_code=fel.kod)


# -----------------------------------------------------------------------------
# Allmänt
# -----------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def rot() -> dict:
    return {"namn": "Fornmed", "dokumentation": "/docs", "openapi": "/openapi.json",
            "version": "/v1"}


@app.get("/halsa", tags=["allmänt"], summary="Kontrollera att tjänsten och databasen svarar")
def halsa() -> JSONResponse:
    try:
        conn = db._hamta_db()
        conn.close()
        return JSONResponse({"status": "ok"})
    except Exception as fel:
        log.warning("Hälsokontroll: databasen svarar inte: %s", fel)
        return JSONResponse({"status": "fel", "databas": "svarar inte"}, status_code=503)


@app.get("/v1/oversikt", tags=["allmänt"], responses=_innehall("objekt"),
         summary="Antal poster per tabell och källsamlingarna")
def oversikt(request: Request, _format: FormatParam = None) -> Response:
    return _svar(request, fragor.statistik(), "objekt", titel="Fornmed – översikt")


@app.get("/v1/kallsamlingar", tags=["källor"], responses=_innehall("lista"),
         summary="Källsamlingarna med licens och antal verk")
def kallsamlingar(request: Request, _format: FormatParam = None) -> Response:
    rader = fragor.statistik()["kallsamlingar"]
    return _svar(request, rader, "lista", titel="Källsamlingar")


# -----------------------------------------------------------------------------
# Verk och dokument
# -----------------------------------------------------------------------------

VerkId = Annotated[str, Path(description="Verkets id, t.ex. verk:lag:aldre_vastgotalagen")]
SprakParam = Annotated[str | None, Query(
    description="Språk i prioritetsordning, ISO 639-3: sprak=swe,dan,lat. "
                "Utan sprak blir det originalspråket.")]
UtgavaParam = Annotated[str | None, Query(description="En bestämd utgåva; gäller före sprak.")]
RollParam = Annotated[str | None, Query(description="huvudtext eller skolier")]


@app.get("/v1/verk", tags=["källor"], responses=_innehall("lista"), summary="Lista verk")
def lista_verk(
    request: Request,
    kallsamling: str | None = None,
    genre: Annotated[str | None, Query(description="t.ex. lag, saga, kronika, diplom")] = None,
    sprak: Annotated[str | None, Query(description="Verkets språk, t.ex. fsv eller lat")] = None,
    ar_fran: int | None = None,
    ar_till: int | None = None,
    titel: Annotated[str | None, Query(description="Del av titeln")] = None,
    plats: Annotated[str | None, Query(description="Platsens entitets-id, t.ex. plats:sdhk:lund. "
                                                         "En kommun, ett landskap eller ett land omfattar platserna där, t.ex. plats:kommun:1281")] = None,
    plats_roll: Annotated[str | None, Query(
        description="utfardandeort, fyndplats, socken, harad, kommun, omrade eller forvaring")] = None,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=MAX_PER_SIDA)] = 100,
    _format: FormatParam = None,
) -> Response:
    rader, total = dokument.lista_verk(kallsamling, genre, sprak, ar_fran, ar_till, titel,
                                       sida, per_sida, plats, plats_roll)
    return _svar(request, rader, "lista", titel="Verk", total=total, sida=sida, per_sida=per_sida)


@app.get("/v1/verk/{verk_id}", tags=["källor"], responses=_innehall("objekt"),
         summary="Ett verk med vittnen, utgåvor, passager (utan text) och bedömningar")
def hamta_verk(request: Request, verk_id: VerkId, _format: FormatParam = None) -> Response:
    if fmt := _rdf_format(request):
        return _rdf_svar("verk", verk_id, fmt)
    verk = _hittad(fragor.hamta_verk(verk_id), f"Verket '{verk_id}'")
    return _svar(request, verk, "objekt")


@app.get("/v1/verk/{verk_id}/versioner", tags=["dokument"], responses=_innehall("lista"),
         summary="Verkets språkversioner")
def verkets_versioner(request: Request, verk_id: VerkId, _format: FormatParam = None) -> Response:
    # utgava_id är None för versioner utan utgåva (SDHK:s regester); utgava
    # är versionens namn i båda fallen och det som anges i utgava=
    rader = [{k: v for k, v in version.items() if k != "utgava_id"}
             for version in dokument.versioner(verk_id)]
    return _svar(request, rader, "lista", titel=f"Versioner av {verk_id}")


def _text(request: Request, verk_id: str, del_: str | None, sprak: str | None,
          utgava: str | None, roll: str | None, fran: str | None, till: str | None,
          parallellt: bool) -> Response:
    if parallellt:
        data = dokument.hamta_parallellt(verk_id, _sprakkoder(sprak) or [], del_, fran, till)
        return _svar(request, data, "parallell")
    data = dokument.hamta_text(verk_id, _sprakkoder(sprak), utgava, roll, del_, fran, till)
    return _svar(request, data, "dokument")


@app.get("/v1/verk/{verk_id}/text", tags=["dokument"], responses=_innehall("dokument"),
         summary="Hela verket i ett svar, eller ett avsnitt med fran och till")
def verkets_text(
    request: Request,
    verk_id: VerkId,
    sprak: SprakParam = None,
    utgava: UtgavaParam = None,
    roll: RollParam = None,
    fran: Annotated[str | None, Query(description="Första passagens id")] = None,
    till: Annotated[str | None, Query(description="Sista passagens id")] = None,
    parallellt: Annotated[bool, Query(description="Texterna på språken i sprak sida vid sida")] = False,
    _format: FormatParam = None,
) -> Response:
    return _text(request, verk_id, None, sprak, utgava, roll, fran, till, parallellt)


@app.get("/v1/verk/{verk_id}/delar", tags=["dokument"], responses=_innehall("lista"),
         summary="Verkets delar: böcker, balkar, sagor, avsnitt")
def verkets_delar(request: Request, verk_id: VerkId, sprak: SprakParam = None,
                  utgava: UtgavaParam = None, roll: RollParam = None,
                  _format: FormatParam = None) -> Response:
    data = dokument.hamta_delar(verk_id, _sprakkoder(sprak), utgava, roll)
    return _svar(request, data, "lista", rader=data["delar"], titel=f"Delar av {data['verk']['titel']}")


@app.get("/v1/verk/{verk_id}/delar/{del_}/text", tags=["dokument"], responses=_innehall("dokument"),
         summary="En del av verket i ett svar")
def delens_text(
    request: Request,
    verk_id: VerkId,
    del_: Annotated[str, Path(description="Delens namn, t.ex. 'bok VII' eller 'Kirkiu bolkær'")],
    sprak: SprakParam = None,
    utgava: UtgavaParam = None,
    roll: RollParam = None,
    parallellt: bool = False,
    _format: FormatParam = None,
) -> Response:
    return _text(request, verk_id, del_, sprak, utgava, roll, None, None, parallellt)


@app.get("/v1/passager/{passage_id}", tags=["dokument"], responses=_innehall("passage"),
         summary="En passage med hela texten; sprak= ger samma passage på ett annat språk")
def hamta_passage(request: Request, passage_id: str, sprak: SprakParam = None,
                  _format: FormatParam = None) -> Response:
    if fmt := _rdf_format(request):
        return _rdf_svar("passage", passage_id, fmt)
    if koder := _sprakkoder(sprak):
        return _svar(request, dokument.hamta_passage_pa_sprak(passage_id, koder), "passage")
    return _svar(request, dokument.hamta_passage(passage_id), "passage")


@app.get("/v1/verk/{verk_id}/utgavor", tags=["källor"], responses=_innehall("lista"),
         summary="Verkets utgåvor, också tryck utan text i databasen")
def verkets_utgavor(request: Request, verk_id: VerkId, _format: FormatParam = None) -> Response:
    return _svar(request, listor.utgavor(verk_id), "lista", titel=f"Utgåvor av {verk_id}")


@app.get("/v1/utgavor/{utgava_id}", tags=["källor"], responses=_innehall("objekt"),
         summary="En utgåva med språk, typ, licens, omfång och delar")
def hamta_utgava(request: Request, utgava_id: str, _format: FormatParam = None) -> Response:
    if fmt := _rdf_format(request):
        return _rdf_svar("utgava", utgava_id, fmt)
    return _svar(request, listor.hamta_utgava(utgava_id), "objekt")


@app.get("/v1/sdhk/{nummer}", tags=["källor"], status_code=307,
         summary="Genväg till ett brev i SDHK; omdirigerar till verket")
def sdhk(request: Request, nummer: int) -> RedirectResponse:
    verk_id = listor.sdhk_verk_id(nummer)
    # Relativ adress, så att omdirigeringen behåller https och värdnamnet bakom proxyn
    adress = app.url_path_for("hamta_verk", verk_id=verk_id)
    if request.url.query:
        adress += f"?{request.url.query}"
    return RedirectResponse(adress, status_code=307)


# -----------------------------------------------------------------------------
# Sökning
# -----------------------------------------------------------------------------

@app.get("/v1/sok", tags=["sökning"], responses=_innehall("lista"),
         summary="Sök i regester och översättningar, och vid behov i originaltexterna")
def sokning(
    request: Request,
    q: Annotated[str, Query(min_length=1, description="Frågan")],
    metod: Annotated[str, Query(pattern="^(hybrid|fts|vektor)$")] = "hybrid",
    antal: Annotated[int, Query(ge=1, le=50)] = 10,
    ar_fran: int | None = None,
    ar_till: int | None = None,
    genre: str | None = None,
    texttyper: Annotated[str, Query(pattern="^(moderna|alla)$")] = "moderna",
    expandera: bool = True,
    max_tecken_per_traff: Annotated[int, Query(
        ge=50, le=20000, description="Längre träfftexter kapas; läs hela passagen med /v1/passager")] = 500,
    _format: FormatParam = None,
) -> Response:
    with SOKNINGAR_SAMTIDIGT:
        try:
            svar = sok.sok(q, metod, antal, sok.Filter(ar_fran, ar_till, genre), texttyper, expandera)
        except ValueError as fel:
            raise DokumentFel(400, str(fel)) from fel
    for traff in svar["traffar"]:
        traff["trunkerad"] = len(traff["text"]) > max_tecken_per_traff
        traff["text"] = traff["text"][:max_tecken_per_traff]
    data = {"fraga": q, "metod": metod, "texttyper": texttyper, "antal": len(svar["traffar"]),
            "expansion": svar["expansion"], "traffar": svar["traffar"]}
    return _svar(request, data, "lista", rader=svar["traffar"], titel=f"Sökning: {q}")


def _bbox(varde: str | None) -> tuple[float, float, float, float] | None:
    if not varde:
        return None
    try:
        vast, syd, ost, nord = (float(v) for v in varde.split(","))
    except ValueError as fel:
        raise DokumentFel(400, "bbox anges som västra längd,södra bredd,östra längd,norra bredd") from fel
    return vast, syd, ost, nord


@app.get("/v1/sok/objekt/{objekt_id}", tags=["sökning"], responses=_innehall("objekt"),
         summary="Ett verks eller en entitets sökpost: typ, tider och platser")
def sokpost(request: Request, objekt_id: str, _format: FormatParam = None) -> Response:
    post = _hittad(objektsok.hamta_poster([objekt_id]).get(objekt_id), f"Sökposten '{objekt_id}'")
    return _svar(request, post, "objekt")


@app.get("/v1/sok/objekt", tags=["sökning"], responses=_innehall("lista"),
         summary="Sök dokument och entiteter med tid, plats och fasetter")
def sok_objekt(
    request: Request,
    q: Annotated[str | None, Query(description="Frågan. Utan fråga listas urvalet i tidsordning")] = None,
    objekttyp: Annotated[str | None, Query(pattern="^(verk|entitet)$")] = None,
    undertyp: Annotated[str | None, Query(description="Verkets genre (diplom, saga, lag …) eller "
                                                      "entitetens typ (person, plats …)")] = None,
    kallsamling: Annotated[str | None, Query(description="t.ex. sdhk, df, rundata")] = None,
    ar_fran: int | None = None,
    ar_till: int | None = None,
    tidsaxel: Annotated[str, Query(
        pattern="^(primar|handelse|tillkomst|forlaga)$",
        description="Vilken tid årsfiltret gäller: primar (händelsen om den är känd, annars tillkomsten), "
                    "handelse, tillkomst eller forlaga (äldsta daterade vittne)")] = "primar",
    plats: Annotated[str | None, Query(description="Platsens entitets-id. Ett land, landskap, län, en kommun "
                                                   "eller socken omfattar platserna där, t.ex. plats:gotland")] = None,
    platsroll: Annotated[str | None, Query(
        pattern="^(primar|handelse|tillkomst|forvaring|lage)$",
        description="Vilken roll platsen ska ha; utan roll räknas alla")] = None,
    bbox: Annotated[str | None, Query(description="Primära platser inom västra längd,södra bredd,"
                                                  "östra längd,norra bredd (WGS84)")] = None,
    texttyper: Annotated[str, Query(pattern="^(moderna|alla)$")] = "moderna",
    expandera: bool = True,
    fasetter: bool = True,
    karta: Annotated[bool, Query(description="Urvalets primära platser med läge och antal, för en karta")] = False,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=100)] = 20,
    max_tecken_per_traff: Annotated[int, Query(ge=50, le=20000)] = 500,
    _format: FormatParam = None,
) -> Response:
    filter_ = sok.Filter(ar_fran, ar_till, tidsaxel=tidsaxel, kallsamling=kallsamling, plats=plats,
                         platsroll=platsroll, objekttyp=objekttyp, undertyp=undertyp, bbox=_bbox(bbox))
    with SOKNINGAR_SAMTIDIGT:
        try:
            svar = objektsok.sok_objekt(q, filter_, per_sida, sida, texttyper, expandera, fasetter, karta)
        except ValueError as fel:
            raise DokumentFel(400, str(fel)) from fel
    for traff in svar["traffar"]:
        utdrag = traff.get("utdrag")
        if utdrag:
            utdrag["trunkerad"] = len(utdrag["text"]) > max_tecken_per_traff
            utdrag["text"] = utdrag["text"][:max_tecken_per_traff]
    rader = [{"id": t["id"], "objekttyp": t["objekttyp"], "undertyp": t["undertyp"], "rubrik": t["rubrik"],
              "tid_fran": (t["tid"]["visas"] or {}).get("fran"), "tid_till": (t["tid"]["visas"] or {}).get("till"),
              "tid_kalla": (t["tid"]["visas"] or {}).get("kalla"),
              "platser": "; ".join(p["namn"] for p in t["platser"] if p["primar"]),
              "sammanfattning": t["sammanfattning"]} for t in svar["traffar"]]
    return _svar(request, svar["traffar"], "lista", rader=rader, titel=f"Sökning: {q or 'urval'}",
                 total=svar["total"], sida=sida, per_sida=per_sida,
                 omslag={"fraga": q, "expansion": svar["expansion"], "stavning": svar["stavning"], "kapad": svar["kapad"],
                         "fasetter": svar["fasetter"], "karta": svar["karta"]})


# -----------------------------------------------------------------------------
# Entiteter och påståenden
# -----------------------------------------------------------------------------

@app.get("/v1/entiteter", tags=["entiteter"], responses=_innehall("lista"),
         summary="Sök personer, platser, folk, ämbeten och begrepp på namn")
def sok_entiteter(
    request: Request,
    namn: Annotated[str, Query(min_length=1)],
    typ: Annotated[str | None, Query(description="person, grupp, plats, institution, indelning, ambete, begrepp")] = None,
    antal: Annotated[int, Query(ge=1, le=100)] = 20,
    _format: FormatParam = None,
) -> Response:
    return _svar(request, fragor.sok_entitet(namn, typ, antal), "lista", titel=f"Entiteter: {namn}")


@app.get("/v1/entiteter/{entitet_id}", tags=["entiteter"], responses=_innehall("objekt"),
         summary="En entitet med identifieringar och påståenden")
def hamta_entitet(
    request: Request,
    entitet_id: str,
    predikat: str | None = None,
    antal: Annotated[int, Query(ge=1, le=200)] = 50,
    fran: Annotated[int, Query(ge=0)] = 0,
    _format: FormatParam = None,
) -> Response:
    if fmt := _rdf_format(request):
        return _rdf_svar("entitet", entitet_id, fmt)
    entitet = _hittad(fragor.hamta_entitet(entitet_id, predikat, antal, fran),
                      f"Entiteten '{entitet_id}'")
    return _svar(request, entitet, "objekt")


@app.get("/v1/entiteter/{entitet_id}/namnformer", tags=["entiteter"], responses=_innehall("lista"),
         summary="Entitetens namnformer i källorna")
def entitetens_namnformer(
    request: Request,
    entitet_id: str,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=MAX_PER_SIDA)] = 100,
    _format: FormatParam = None,
) -> Response:
    rader, total = listor.namnformer(entitet_id, sida, per_sida)
    return _svar(request, rader, "lista", titel=f"Namnformer för {entitet_id}", total=total,
                 sida=sida, per_sida=per_sida)


@app.get("/v1/entiteter/{entitet_id}/identifieringar", tags=["entiteter"], responses=_innehall("lista"),
         summary="Identifieringar åt båda håll, en rad per bedömning")
def entitetens_identifieringar(request: Request, entitet_id: str,
                               _format: FormatParam = None) -> Response:
    return _svar(request, listor.identifieringar(entitet_id), "lista",
                 titel=f"Identifieringar för {entitet_id}")


@app.get("/v1/pastaenden", tags=["påståenden"], responses=_innehall("lista"),
         summary="Påståenden med filter på entitet, predikat, verk, källsamling och tid")
def lista_pastaenden(
    request: Request,
    entitet: Annotated[str | None, Query(description="Som subjekt, objekt eller plats")] = None,
    predikat: Annotated[str | None, Query(description="t.ex. innehar_ambete, utfardar; se /v1/vokabularer/predikat")] = None,
    verk: str | None = None,
    kallsamling: str | None = None,
    extraktion: Annotated[str | None, Query(pattern="^(manuell|regel|modell)$")] = None,
    granskad: bool | None = None,
    ar_fran: int | None = None,
    ar_till: int | None = None,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=MAX_PER_SIDA)] = 100,
    _format: FormatParam = None,
) -> Response:
    rader, total = listor.lista_pastaenden(entitet, predikat, verk, kallsamling, extraktion,
                                           granskad, ar_fran, ar_till, sida, per_sida)
    return _svar(request, rader, "lista", titel="Påståenden", total=total, sida=sida,
                 per_sida=per_sida)


@app.get("/v1/bedomningar", tags=["påståenden"], responses=_innehall("lista"),
         summary="Forskningens bedömningar av påståenden, verk, vittnen och identifieringar")
def lista_bedomningar(
    request: Request,
    pastaende: str | None = None,
    verk: str | None = None,
    aspekt: Annotated[str | None, Query(description="t.ex. historicitet, akthet, datering, identifiering")] = None,
    bedomare: Annotated[str | None, Query(description="Del av bedömarens namn")] = None,
    granskad: bool | None = None,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=MAX_PER_SIDA)] = 100,
    _format: FormatParam = None,
) -> Response:
    rader, total = listor.lista_bedomningar(pastaende, verk, aspekt, bedomare, granskad, sida, per_sida)
    return _svar(request, rader, "lista", titel="Bedömningar", total=total, sida=sida,
                 per_sida=per_sida)


@app.get("/v1/pastaenden/{pastaende_id}", tags=["påståenden"], responses=_innehall("objekt"),
         summary="Ett påstående med källa, relationer och bedömningar")
def hamta_pastaende(request: Request, pastaende_id: str, _format: FormatParam = None) -> Response:
    if fmt := _rdf_format(request):
        return _rdf_svar("pastaende", pastaende_id, fmt)
    pastaende = _hittad(fragor.hamta_pastaende(pastaende_id), f"Påståendet '{pastaende_id}'")
    return _svar(request, pastaende, "objekt", titel=pastaende_id)


@app.get("/v1/omstridda", tags=["påståenden"], responses=_innehall("objekt"),
         summary="Där bedömningarna går isär, och konkurrerande identifieringar")
def omstridda(
    request: Request,
    maltyp: Annotated[str | None, Query(pattern="^(pastaende|verk|vittne|identifiering)$")] = None,
    _format: FormatParam = None,
) -> Response:
    return _svar(request, fragor.omstridda(maltyp), "objekt", titel="Omstridda")


# -----------------------------------------------------------------------------
# Vokabulär, begrepp och ordböcker
# -----------------------------------------------------------------------------

@app.get("/v1/vokabularer", tags=["vokabulär"], responses=_innehall("lista"),
         summary="Alla kontrollerade värden")
def vokabularer(request: Request, _format: FormatParam = None) -> Response:
    return _svar(request, fragor.lista_vokabular(), "lista", titel="Vokabulär")


@app.get("/v1/vokabularer/{schema}", tags=["vokabulär"], responses=_innehall("lista"),
         summary="Värdena för en klassificeringsaxel, t.ex. genre eller historicitet")
def vokabular(request: Request, schema: str, _format: FormatParam = None) -> Response:
    rader = fragor.lista_vokabular(schema)
    if not rader:
        raise DokumentFel(404, f"Vokabuläret '{schema}' finns inte.")
    return _svar(request, rader, "lista", titel=f"Vokabulär: {schema}")


@app.get("/v1/begrepp/{term}", tags=["vokabulär"], responses=_innehall("objekt"),
         summary="Ett medeltida begrepp med termer, relationer och ordboksartiklar")
def begrepp(request: Request, term: str,
            max_tecken_per_artikel: Annotated[int, Query(ge=100, le=20000)] = 1500,
            _format: FormatParam = None) -> Response:
    traffar = fragor.hamta_begrepp(term, max_tecken_per_artikel)
    if not traffar:
        raise DokumentFel(404, f"Begreppet '{term}' finns inte i registret.")
    return _svar(request, {"term": term, "begrepp": traffar}, "objekt", titel=f"Begrepp: {term}")


@app.get("/v1/ordbok", tags=["vokabulär"], responses=_innehall("objekt"),
         summary="Slå upp ett fornsvenskt ord i Schlyter och Söderwall")
def ordbok(
    request: Request,
    ord: Annotated[str, Query(min_length=1)],
    ordbok: Annotated[str | None, Query(pattern="^(schlyter|soderwall|soderwall_supp)$")] = None,
    antal: Annotated[int, Query(ge=1, le=50)] = 10,
    _format: FormatParam = None,
) -> Response:
    artiklar = fragor.sok_ordbok(ord, ordbok, antal, 1500)
    return _svar(request, {"ord": ord, "artiklar": artiklar}, "objekt", titel=f"Ordbok: {ord}")


# -----------------------------------------------------------------------------
# Auktoriteter
# -----------------------------------------------------------------------------

@app.get("/v1/auktoriteter", tags=["auktoriteter"], responses=_innehall("lista"),
         summary="Längderna över regenter, biskopar och påvar")
def auktoriteter(request: Request, _format: FormatParam = None) -> Response:
    return _svar(request, listor.auktoritetslangder(), "lista", titel="Auktoriteter")


@app.get("/v1/auktoriteter/{langd}", tags=["auktoriteter"], responses=_innehall("lista"),
         summary="En längd i tillträdesordning, en rad per titel och säte")
def auktoritetslangd(
    request: Request,
    langd: Annotated[str, Path(description="regenter, biskopar eller pavar")],
    titel: Annotated[str | None, Query(description="t.ex. kung, biskop, arkebiskop, pave")] = None,
    sate: Annotated[str | None, Query(description="Rike eller stift, t.ex. Sverige eller Uppsala")] = None,
    ar: Annotated[int | None, Query(description="De som bar titeln det året")] = None,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=MAX_PER_SIDA)] = MAX_PER_SIDA,
    _format: FormatParam = None,
) -> Response:
    uppgifter, rader, total = listor.auktoritet(langd, titel, sate, ar, sida, per_sida)
    return _svar(request, rader, "lista", titel=uppgifter["namn"], total=total, sida=sida,
                 per_sida=per_sida, omslag={"langd": uppgifter})


@app.get("/v1/auktoriteter/{langd}/{person_id}", tags=["auktoriteter"], responses=_innehall("objekt"),
         summary="En person i längden med alla titlar")
def auktoritet(request: Request, langd: str, person_id: str, _format: FormatParam = None) -> Response:
    return _svar(request, listor.hamta_auktoritet(langd, person_id), "objekt")


# -----------------------------------------------------------------------------
# Leveranser
# -----------------------------------------------------------------------------

@app.get("/v1/leveranser", tags=["allmänt"], responses=_innehall("lista"),
         summary="Uppdateringar av databasen, senaste först")
def lista_leveranser(
    request: Request,
    sida: Annotated[int, Query(ge=1)] = 1,
    per_sida: Annotated[int, Query(ge=1, le=MAX_PER_SIDA)] = 50,
    _format: FormatParam = None,
) -> Response:
    rader, total = listor.leveranser(sida, per_sida)
    return _svar(request, rader, "lista", titel="Leveranser", total=total, sida=sida,
                 per_sida=per_sida)


@app.get("/v1/leveranser/{leverans_id}", tags=["allmänt"], responses=_innehall("objekt"),
         summary="En leverans med antal per tabell och källsamling")
def hamta_leverans(request: Request, leverans_id: str, _format: FormatParam = None) -> Response:
    return _svar(request, listor.hamta_leverans(leverans_id), "objekt", titel=f"Leverans {leverans_id}")


# -----------------------------------------------------------------------------
# Länkade data: uppslag av URI:er
# -----------------------------------------------------------------------------
# https://w3id.org/fornmed/id/… vidarebefordras till https://<domän>/id/…,
# som nginx skickar hit. En webbläsare skickas vidare till postens webbsida;
# ett program får RDF. Webbsidornas adresser följer samma regler som
# webbplatsen (webb/sidor/texter.py och webb/sidor/lankar.py): verk under
# /kallor/verk/, entiteter under /register/.

ONTOLOGI = pathlib.Path(__file__).parent / "lankade_data" / "fornmed.ttl"
ONTOLOGINS_DOKUMENTATION = "https://github.com/MagnusKolsjo/fornmed/blob/main/lankade_data/README.md"


def _verkets_sida(verk_id: str) -> str:
    return f"/kallor/verk/{verk_id.removeprefix('verk:').replace(':', '-')}/"


def _entitetens_sida(entitet_id: str) -> str:
    return f"/register/{urllib.parse.quote(entitet_id.replace(':', '--'))}/"


def _webbsida(typ: str, post_id: str) -> str | None:
    """Webbsidan som visar posten, eller None om ingen sida finns."""
    conn = db._hamta_db()
    try:
        fraga = lambda sql: rdf_post._rader(conn, sql, post_id)  # noqa: E731
        if typ == "verk":
            return _verkets_sida(post_id) if fraga("SELECT 1 FROM {pf}verk WHERE id = ?") else None
        if typ == "entitet":
            return _entitetens_sida(post_id) if fraga("SELECT 1 FROM {pf}entitet WHERE id = ?") else None
        if typ == "kallsamling":
            return "/kallor/" if fraga("SELECT 1 FROM {pf}kallsamling WHERE id = ?") else None
        verk_sql = {
            "vittne": "SELECT verk_id FROM {pf}vittne WHERE id = ?",
            "utgava": "SELECT verk_id FROM {pf}utgava WHERE id = ?",
            "passage": "SELECT verk_id FROM {pf}passage WHERE id = ?",
            "pastaende": "SELECT ps.verk_id FROM {pf}pastaende p JOIN {pf}passage ps ON ps.id = p.passage_id "
                         "WHERE p.id = ?",
            "bedomning": "SELECT coalesce(b.verk_id, v.verk_id, ps.verk_id) AS verk_id FROM {pf}bedomning b "
                         "LEFT JOIN {pf}vittne v ON v.id = b.vittne_id "
                         "LEFT JOIN {pf}pastaende p ON p.id = b.pastaende_id "
                         "LEFT JOIN {pf}passage ps ON ps.id = p.passage_id WHERE b.id = ?",
        }
        entitet_sql = {
            "identifiering": "SELECT entitet_id FROM {pf}identifiering WHERE id = ?",
            "term": "SELECT entitet_id FROM {pf}term WHERE id = ?",
        }
        if typ in verk_sql:
            rader = fraga(verk_sql[typ])
            if rader and rader[0]["verk_id"]:
                return _verkets_sida(rader[0]["verk_id"])
        if typ in entitet_sql or typ == "bedomning":
            sql = entitet_sql.get(typ, "SELECT i.entitet_id FROM {pf}bedomning b "
                                       "JOIN {pf}identifiering i ON i.id = b.identifiering_id WHERE b.id = ?")
            rader = fraga(sql)
            if rader:
                return _entitetens_sida(rader[0]["entitet_id"])
        return None
    finally:
        conn.close()


def _alternativ(sokvag: str) -> str:
    """Link-huvud med postens adress i varje RDF-format."""
    return ", ".join(f'<{sokvag}?format={kod}>; rel="alternate"; type="{mediatyp}"'
                     for kod, (mediatyp, _, _) in rdf_post.FORMAT.items())


ID_TYPER = "|".join(rdf_uri.TYPER + ("vokabular",))


@app.api_route("/id/{typ}/{post_id:path}", methods=["GET", "HEAD"], tags=["länkade data"],
         responses={200: {"content": {t: {} for t in rdf_post.MEDIATYP_TILL_FORMAT}}, 303: {}},
         summary="En post som länkade data: webbsidan för en webbläsare, RDF för ett program")
def id_uppslag(
    request: Request,
    typ: Annotated[str, Path(pattern=f"^({ID_TYPER})$",
                             description="verk, passage, entitet, pastaende, bedomning …")],
    post_id: Annotated[str, Path(description="Postens id, t.ex. sdhk:34486 eller plats:socken:449")],
    format_: Annotated[str | None, Query(alias="format", pattern="^(html|ttl|jsonld|nt|rdf)$",
                                         description="html, ttl, jsonld, nt eller rdf. Gäller före Accept-huvudet.")] = None,
) -> Response:
    fmt = rdf_post.valj_format(format_, request.headers.get("accept"))
    if fmt is None:
        return JSONResponse({"fel": "Formatet finns inte.", "format": ["html", *rdf_post.FORMAT]},
                            status_code=406)
    sokvag = f"/id/{typ}/{rdf_uri.koda(post_id)}"
    if fmt == "html":
        sida = _webbsida(typ, post_id)
        if sida:
            return RedirectResponse(sida, status_code=303, headers={"Vary": "Accept"})
        # Poster utan egen webbsida (vokabulär, längder, ordboksartiklar) visas som Turtle
        fmt = "ttl"
    svar = _rdf_svar(typ, post_id, fmt)
    svar.headers["Link"] = _alternativ(sokvag)
    svar.headers["Cache-Control"] = "public, max-age=300"
    return svar


@app.api_route("/def/", methods=["GET", "HEAD"], tags=["länkade data"], summary="Fornmeds klasser och egenskaper")
@app.api_route("/def/{namn}", methods=["GET", "HEAD"], tags=["länkade data"], include_in_schema=False)
def ontologi(request: Request, namn: str | None = None,
             format_: Annotated[str | None, Query(alias="format", pattern="^(html|ttl|jsonld|nt|rdf)$")] = None,
             ) -> Response:
    # Klasserna och egenskaperna har URI:er som /def/Pastaende men beskrivs alla i samma dokument
    fmt = rdf_post.valj_format(format_, request.headers.get("accept"))
    if fmt == "html":
        return RedirectResponse(ONTOLOGINS_DOKUMENTATION, status_code=303, headers={"Vary": "Accept"})
    if fmt is None:
        return JSONResponse({"fel": "Formatet finns inte.", "format": ["html", *rdf_post.FORMAT]},
                            status_code=406)
    if fmt == "ttl":
        innehall = ONTOLOGI.read_bytes()
    else:
        g = rdf_post.Graph().parse(ONTOLOGI, format="turtle")
        innehall = g.serialize(format=rdf_post.FORMAT[fmt][1], encoding="utf-8")
    return Response(innehall, media_type=f"{rdf_post.FORMAT[fmt][0]}; charset=utf-8",
                    headers={"Vary": "Accept", "Cache-Control": "public, max-age=3600",
                             "Link": _alternativ("/def/")})

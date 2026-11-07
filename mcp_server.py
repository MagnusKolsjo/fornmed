"""
MCP-server för källor till Sveriges och Nordens forntid och medeltid.

Verktygen läser ur den lokala databasen: källor i fyra nivåer (verk,
vittne, utgåva, passage), entiteter, påståenden om vad källorna hävdar och
forskningens bedömningar av dem. Alla verktyg har prefixet fornmed_.
"""

import logging
import sys

# db läser .env vid import och måste därför importeras före moduler som
# läser sin konfiguration ur miljön (embeddings)
import db
import embeddings
import fragor
import sok
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from mcp_transport import starta

# stdout är MCP-kanalen i stdio-läget; loggning måste gå till stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# Alla verktyg läser bara ur serverns egen databas
LASNING_DB = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

mcp = MCPServer(
    "fornmed",
    instructions=(
        "Källor till Sveriges och Nordens forntid och medeltid: medeltidsbrev ur "
        "Riksarkivets SDHK (44 000 brev fram till 1540), Diplomatarium Fennicum (6 900 brev), Diplomatarium Norvegicum (19 000 brev), Diplomatarium Islandicum (8 700 brev), runinskrifter (Rundata, "
        "6 800 inskrifter), landskapslagarna, Grágás, Eddorna, Heimskringla, "
        "islänningasagorna med Landnámabók och Íslendingabók, Hervarar saga, Fagrskinna, "
        "Morkinskinna, Ágrip, Knýtlinga saga, Saxo, Sven Aggesen, Erikskrönikan, "
        "Karlskrönikan, Konungastyrelsen, Adam av Bremen, frankiska annaler och tyska "
        "krönikor ur MGH (bl.a. Annales Bertiniani, Thietmar, Widukind, Helmold, Henrik "
        "av Lettland), Ottars och Wulfstans berättelser, Olaus Magnus Historia de gentibus "
        "septentrionalibus, romerska och arabiska källor om Norden och andra berättande källor. "
        "Verktygen har prefixet fornmed_. "
        "MASKINÖVERSÄTTNING: svenska översättningar i utgåvor märkta 'språkmodell' "
        "(passage-id som slutar på ':sv', utgåvor '…:sv_modell') är ogranskade. Citera "
        "originalet, inte översättningen. Det gäller bl.a. alla "
        "landskapslagar, alla latinska krönikor ur MGH (Gregorius av Tours, Adam av "
        "Bremen med skolier, Jordanes, Vita Anskarii, de frankiska annalerna, Thietmar, "
        "Widukind, Helmold, Henrik av Lettland, Paulus Diaconus m.fl.), Theodoricus, "
        "Historia Norwegie, Olaus Magnus, Erikskrönikan, Karlskrönikan, "
        "Konungastyrelsen och de sagor och "
        "kungakrönikor som saknar äldre översättning (Fagrskinna, Morkinskinna, "
        "Landnámabók m.fl.). Markeringen [osäker tolkning] i sådan text betyder att "
        "översättningen är osäker på det stället. "
        "RUNINSKRIFTER: uppgifter ur Rundata ska anges med källa (Rundata.info, som "
        "bygger på Samnordisk runtextdatabas). "
        "KEDJOR: fornmed_sok → fornmed_hamta_passage eller fornmed_hamta_verk. "
        "För personer, folk, platser och ämbeten: fornmed_sok_entitet → "
        "fornmed_hamta_entitet → fornmed_hamta_pastaende. fornmed_omstridda "
        "listar var forskningen är oenig. "
        "KÄLLKRITIK: ett påstående beskriver vad en källa HÄVDAR, inte vad som "
        "hände. Redovisa alltid källans genre och tidsavståndet (tidsavstand_ar "
        "är det minsta möjliga avståndet mellan händelse och källa). Relationen "
        "'beroende_av' betyder att en källa återger en annan och inte ger "
        "oberoende stöd. När bedömningar går isär ska alla ståndpunkter redovisas "
        "med bedömare, inte vägas samman till en. Bedömningar med granskad=false "
        "är inte kontrollerade mot publikationen och ska presenteras som "
        "ogranskade. Verkbedömningar som 'akthet: misstankt' gäller brevet som "
        "helhet och ska nämnas när brevet används som belägg. "
        "SÖKNING: sökningen gäller som standard regester och översättningar "
        "(svenska, men också t.ex. Winkel Horns danska Saxo och engelska "
        "översättningar). Hybridsökning (standard) fångar både ordträffar och "
        "omskrivningar; den semantiska delen använder en svensk modell för "
        "svenska texter och en flerspråkig för danska och engelska översättningar "
        "och de latinska krönikorna (Adam av Bremen, Gregorius, Jordanes, de "
        "frankiska annalerna, Thietmar, Helmold m.fl.). Sagorna har äldre svenska, "
        "danska eller engelska översättningar där sådana är fria; Grágás och Sven "
        "Aggesen finns bara i dansk översättning. "
        "Frågans fackord (ledung, frälse, lagman, härad …) och namn (Uppsala, "
        "Starkad, Ansgar …) expanderas automatiskt med registrets termer och "
        "namnformer: fornsvenska, fornvästnordiska, latin och danska (fältet "
        "expansion visar vilka begrepp och namn som användes). texttyper='alla' söker även i originaltexterna på latin, "
        "fornsvenska och fornvästnordiska; utom de latinska krönikorna söks "
        "originaltexterna bara med fulltext, så sök gärna med källspråkets egna ord. Latinska termer söks på stammen och kan ge brus (decim* "
        "träffar även ordningstal). Originaltext läses med fornmed_hamta_passage. "
        "DIPLOMATARIER: Diplomatarium Fennicum (df:N), Norvegicum (dn:band:nr) och Islandicum (di:band:nr) har regester på "
        "svenska, danska/norska respektive isländska. Islandicums brevtext är OCR med läsfel, och gränsen mellan breven "
        "är osäker där verkets uppgifter anger grans_osaker. Ett brev som också finns i SDHK visas en gång i sökningen, med de andra "
        "utgåvorna i fältet samma_brev. Norvegicums och Islandicums brevspråk är maskinellt bestämt (fältet sprakbedomning i "
        "verkets uppgifter anger metoden). texttyper='alla' söker även i utgivarnas noter (passagetyp "
        "'anmarkning') och i bandens registerposter (passagetyp 'register'); en registerpost gäller brevens "
        "sida, inte nödvändigtvis det enskilda brevet. "
        "SKOLIER: Adam av Bremens skolier (passagetyp 'skolion') söks med "
        "texttyper='alla'. De är marginaltillägg i handskrifterna, delvis av Adam "
        "själv och delvis av senare avskrivare, och ska redovisas som skolier, "
        "inte som huvudtext. Adressen anger vilket kapitel skoliet hör till och "
        "om texten är ofullständig i OCR. "
        "BEGREPP OCH ORDBÖCKER: fornmed_begrepp förklarar ett medeltida begrepp "
        "med termer, relationer och Schlyters/Söderwalls artiklar. "
        "fornmed_ordbok slår upp ett fornsvenskt ord i Schlyter (lagspråket) och "
        "Söderwall med supplement. Registrets definitioner är ett ogranskat "
        "utkast; ordböckernas egna definitioner är den citerbara källan och "
        "ska anges med ordbok och uppslagsord. "
        "CITAT: citera aldrig ordagrant ur en text där trunkerad=true utan att "
        "läsa vidare med fran_tecken. Regester är moderna sammanfattningar och "
        "får inte presenteras som citat ur källan."
    ),
)


def _hittad(varde, beskrivning: str):
    if varde is None:
        raise ToolError(f"{beskrivning} finns inte i databasen.")
    return varde


@mcp.tool(title="Sök i källorna", annotations=LASNING_DB)
def fornmed_sok(
    fraga: str,
    metod: str = "hybrid",
    antal: int = 10,
    ar_fran: int | None = None,
    ar_till: int | None = None,
    genre: str | None = None,
    texttyper: str = "moderna",
    expandera: bool = True,
    max_tecken_per_traff: int = 500,
) -> dict:
    """Sök i regester och översättningar, och vid behov i originaltexterna.

    metod: 'hybrid' (fulltext + semantisk, standard), 'fts' (bara ordträffar)
    eller 'vektor' (bara semantisk likhet). ar_fran/ar_till avgränsar på
    källans datering (överlappande intervall; odaterade källor faller bort).
    genre avgränsar på källgenre, t.ex. 'diplom', 'saga', 'kronika' — se
    fornmed_vokabular('genre'). texttyper: 'moderna' (regester och
    översättningar) eller 'alla' (även originaltexter på latin och
    fornsvenska m.fl.; utom de latinska krönikorna söks de bara med fulltext).
    expandera: utöka frågans fackord med begreppsregistrets termer.

    Varje träff har passage_id och verk_id för vidare läsning, källans genre
    och datering, passagetyp och språk, länk till verket (url), länk till
    underlaget för just passagen (underlag_url), licens samt
    verkbedomningar, t.ex. misstänkt förfalskning. I hybridläget anger
    fts_plats och vektor_plats träffens placering i respektive delsökning
    (vektor_plats i den modell som embeddat passagen).
    expansion listar de begrepp frågan utökades med.
    """
    if not fraga.strip():
        raise ToolError("fraga saknas.")
    antal = max(1, min(antal, 50))
    try:
        svar = sok.sok(fraga, metod, antal, sok.Filter(ar_fran, ar_till, genre), texttyper, expandera)
    except ValueError as fel:
        raise ToolError(str(fel)) from fel
    for t in svar["traffar"]:
        t["trunkerad"] = len(t["text"]) > max_tecken_per_traff
        t["text"] = t["text"][:max_tecken_per_traff]
    return {"fraga": fraga, "metod": metod, "texttyper": texttyper, "antal": len(svar["traffar"]),
            "expansion": svar["expansion"], "traffar": svar["traffar"]}


@mcp.tool(title="Förklara ett medeltida begrepp", annotations=LASNING_DB)
def fornmed_begrepp(term: str, max_tecken_per_artikel: int = 1500) -> list[dict]:
    """Slå upp ett begrepp i begreppsregistret (ledung, frälse, härad, lagman …).

    term kan vara modern eller fornsvensk, i valfri böjning (lagmannen,
    hæraþ, leþunger), eller ett begrepps-id ('begrepp:ledung'). Svaret har
    registrets definition (ett ogranskat utkast), termer per språk (swe
    modern svenska, fsv fornsvenska, non fornvästnordiska, lat latin),
    relationer till bredare, smalare och relaterade begrepp, samt
    Schlyters och Söderwalls artiklar om ordet med alla betydelser.
    Tom lista om begreppet inte finns i registret — pröva då fornmed_ordbok.
    """
    return fragor.hamta_begrepp(term, max_tecken_per_artikel)


@mcp.tool(title="Slå upp i Schlyter och Söderwall", annotations=LASNING_DB)
def fornmed_ordbok(
    ord: str,
    ordbok: str | None = None,
    antal: int = 10,
    max_tecken_per_betydelse: int = 1500,
) -> list[dict]:
    """Slå upp ett fornsvenskt ord i Schlyters och Söderwalls ordböcker.

    Stavningen normaliseras (þ, dh, gh, æ, w, dubbelteckning), så härad,
    häradh och hæraþ ger samma träff; utan exakt träff prövas ordet som
    början av uppslagsordet. ordbok avgränsar till 'schlyter' (lagspråket,
    1877), 'soderwall' (huvudverket, 1884–1918) eller 'soderwall_supp'
    (supplementet, 1925–1973). När Söderwall bara hänvisar till lagarna
    (hanvisar_till_lagarna=true) tas Schlyters artikel om samma ord med.
    Definitionerna innehåller ordböckernas förkortningar för källor
    (VG = Västgötalagen, U = Upplandslagen, SM = Södermannalagen …).
    Ordböckerna är digitaliserade av Språkbanken (CC BY 4.0). Söderwalls
    huvudverk saknar uppslagsord på ä och supplementet saknar v.
    """
    if not ord.strip():
        raise ToolError("ord saknas.")
    return fragor.sok_ordbok(ord, ordbok, max(1, min(antal, 50)), max_tecken_per_betydelse)


@mcp.tool(title="Läs ett verk", annotations=LASNING_DB)
def fornmed_hamta_verk(verk_id: str) -> dict:
    """Hämta ett verk (brev, saga, krönika …) med vittnen, utgåvor och bedömningar.

    Svaret listar verkets passager med id och längd men utan text; läs
    texten med fornmed_hamta_passage. Vittnen är bevarade original,
    avskrifter och registraturer; deras datering är skild från verkets.
    Bedömningar gäller verket som helhet (äkthet, datering). Utgåvorna har
    var sin licens; passagerna har underlag_url för manuell kontroll. För
    runinskrifter listar bilder länkar till fotografier och dokumentation
    hos museer och Riksantikvarieämbetet (förvaltarnas egna villkor gäller).
    platser listar verkets geografiska platser som entiteter, med roll
    (utfardandeort, fyndplats, socken, harad, kommun, omrade) och källans
    ordalydelse. osaker betyder att källan anger orten med frågetecken eller
    som ett alternativ, harledd att orten står inom parentes i källan.
    Kopplingen går på namnet: en plats med ett vanligt namn kan avse flera orter.
    """
    return _hittad(fragor.hamta_verk(verk_id), f"Verket '{verk_id}'")


@mcp.tool(title="Läs en passage", annotations=LASNING_DB)
def fornmed_hamta_passage(passage_id: str, max_tecken: int = 8000, fran_tecken: int = 0) -> dict:
    """Hämta en passages text (regest, originaltext eller översättning).

    Långa texter kapas vid max_tecken; ett kapat svar har trunkerad=true och
    fortsatt_fran_tecken, som skickas som fran_tecken för att läsa vidare.
    Svaret anger utgåvan, licensen (utgåvans eller källsamlingens), och
    underlag_url: länk till sidbilden eller sidan i den digitala utgåvan där
    texten kan kontrolleras manuellt (t.ex. dMGH-sidbild, Wikisource med
    inskannade sidor, Rundatas inskriftssida); verk_url gäller hela verket.
    Svaret listar också de påståenden som registrerats ur passagen.
    """
    return _hittad(fragor.hamta_passage(passage_id, max_tecken, fran_tecken),
                   f"Passagen '{passage_id}'")


@mcp.tool(title="Sök personer, platser och begrepp", annotations=LASNING_DB)
def fornmed_sok_entitet(namn: str, typ: str | None = None, antal: int = 20) -> list[dict]:
    """Sök entiteter på namn eller namnform (delsträng, skiftlägesokänsligt).

    typ avgränsar till t.ex. 'person', 'grupp', 'plats', 'institution',
    'indelning', 'ambete', 'handelse' eller 'begrepp'. Varje källas namnform
    kan vara en egen entitet (Hygelac, Chlochilaicus); att de avser samma
    person är en identifiering som visas av fornmed_hamta_entitet.
    """
    return fragor.sok_entitet(namn, typ, max(1, min(antal, 100)))


@mcp.tool(title="Läs en entitet", annotations=LASNING_DB)
def fornmed_hamta_entitet(entitet_id: str, predikat: str | None = None, antal: int = 50,
                          fran: int = 0) -> dict:
    """Hämta en entitet med identifieringar och de påståenden den förekommer i.

    En plats har plats_uppgift med nutida namn, kommun, land och koordinater. Med
    metod 'sprakmodell' och granskad=false är kopplingen inte kontrollerad av människa.

    Identifieringar visas åt båda håll med forskningens bedömningar.
    Identifieringar med samma alternativgrupp utesluter varandra (t.ex.
    gēatas = götar, jutar eller geter). Påståendena listas med källans genre,
    tidsavstånd och om bedömningarna av historiciteten går isär.

    sammanfattning ger antal och årsspann per predikat. Påståendena kommer
    sidvis: högst antal (max 200) från position fran, och fortsatt_fran anger
    nästa sida. predikat avgränsar, t.ex. 'innehar_ambete' eller 'utfardar'.
    Påståenden med extraktion 'regel' ur SDHK:s utfärdarfält bygger på
    Riksarkivets registeruppgift, inte på ett citat ur brevet.

    titulatur på ett titelpåstående säger att brevets datering inte faller
    inom personens innehav av titeln: fore_titeln och efter_titeln (personen
    levde, t.ex. en avsatt kung som fortsatte att kallas kung), efter_dodsfall
    (omnämnd efter sin död) och fore_fodelse (dateringen eller identifieringen
    är fel). Utfärdare vars identitet är oklar har en egen entitet med de
    möjliga personerna som identifieringar (bedömning 'mojlig'); redovisa
    dem som möjliga, inte som fastställda.
    """
    return _hittad(fragor.hamta_entitet(entitet_id, predikat, max(1, min(antal, 200)), max(0, fran)),
                   f"Entiteten '{entitet_id}'")


@mcp.tool(title="Läs ett påstående", annotations=LASNING_DB)
def fornmed_hamta_pastaende(pastaende_id: str) -> dict:
    """Hämta ett påstående med källa, relationer och bedömningar.

    Ett påstående är vad en passage hävdar. Relationer visar vilka andra
    påståenden det stöder, motsäger eller är beroende av. Bedömningarna är
    forskares omdömen om historiciteten och korroborationen, var och en
    med bedömare, publikation och granskningsstatus.
    """
    return _hittad(fragor.hamta_pastaende(pastaende_id), f"Påståendet '{pastaende_id}'")


@mcp.tool(title="Visa var forskningen är oenig", annotations=LASNING_DB)
def fornmed_omstridda(maltyp: str | None = None) -> dict:
    """Lista mål där bedömningarna går isär, och konkurrerande identifieringar.

    maltyp avgränsar till 'pastaende', 'verk', 'vittne' eller 'identifiering'.
    Ett mål är omstritt inom en aspekt (historicitet, datering, äkthet,
    identifiering) när minst två bedömningar ger olika värden.
    """
    return fragor.omstridda(maltyp)


@mcp.tool(title="Visa klassificeringsvärden", annotations=LASNING_DB)
def fornmed_vokabular(schema: str | None = None) -> list[dict]:
    """Lista de kontrollerade värdena för klassificeringsaxlarna.

    schema avgränsar till en axel, t.ex. 'genre', 'historicitet', 'akthet',
    'korroboration', 'identifiering', 'predikat' eller 'entitetstyp'.
    Utan schema listas alla.
    """
    return fragor.lista_vokabular(schema)


@mcp.tool(title="Översikt över databasen", annotations=LASNING_DB)
def fornmed_oversikt() -> dict:
    """Antal verk, passager, entiteter, påståenden och bedömningar, samt källsamlingar med licens."""
    return fragor.statistik()


if __name__ == "__main__":
    starta(
        mcp,
        standardport=8010,
        initiera=db.initiera_schema,
        # I http-läget laddas modellerna före första anropet; i stdio-läget
        # laddas de lat så att klienten inte väntar vid start
        forvarm_http=lambda: [embeddings._hamta_modell(m) for m in embeddings.MODELLER.values()],
    )

"""
Skapar webbplatsens sidor med deras första texter.

    python manage.py skapa_sidor
    python manage.py skapa_sidor --skriv-over mcp
    python manage.py skapa_sidor --skriv-over

Sidor som redan finns lämnas orörda, så att det som redigerats i Wagtail
behålls. Med --skriv-over ersätts texterna i de angivna sidorna (deras
slug, eller start för startsidan) med dem som står här; utan namn ersätts
alla sidors texter.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site

from sidor.models import KallforteckningSida, StartSida, TextSida, UppdateringarSida

START_INGRESS = (
    "Fornmed samlar källor till Sveriges och Nordens forntid och medeltid och gör dem sökbara "
    "och citerbara. Varje uppgift går att följa tillbaka till en passage i källan, och där "
    "forskningen är oenig visas alla ståndpunkter med vem som framfört dem."
)

START_TEXT = """
<h2>Vad som finns</h2>
<ul>
<li>Medeltidsbrev ur Riksarkivets SDHK, 44 000 brev fram till 1540, med regester och originaltexter</li>
<li>Runinskrifter ur Rundata, 6 800 inskrifter med translitterering, normalisering och översättning</li>
<li>Landskapslagarna, stadslagen och landslagarna, Grágás och Hednalagen</li>
<li>Eddorna, Heimskringla, islänningasagorna, fornaldarsagorna och kungasagorna</li>
<li>Saxo, Adam av Bremen, Erikskrönikan, Karlskrönikan, Olaus Magnus och frankiska och tyska krönikor och annaler</li>
<li>Romerska och arabiska källor om Norden</li>
<li>Schlyters och Söderwalls ordböcker och ett register över medeltida begrepp</li>
<li>Längder över regenter, biskopar och påvar</li>
</ul>
<p>Alla källor står i <a href="/kallor/">källförteckningen</a>, med licens och språkversioner.</p>
<h2>Påståenden och bedömningar</h2>
<p>Ur källorna har vi tagit ut påståenden: vad en källa hävdar om en person, en plats, ett ämbete eller en lagregel. Påståendena är knutna till sin passage, och forskningens bedömningar av dem registreras med bedömare och publikation. Läs mer om <a href="/pastaenden/">påståendesamlingarna</a> och om <a href="/metod/">metoden</a>.</p>
<h2>Använd Fornmed</h2>
<p>Fornmed är en MCP-server som en AI-assistent som Claude kan söka och läsa i. Lägg till den med adressen <code>https://mcp.fornmed.se</code>; ingen inloggning behövs. <a href="/mcp/">Så ansluter du.</a></p>
<p>Allt finns också i ett öppet <a href="/api/">API</a>. Hela dokument, delar och enskilda passager kan hämtas på valt språk som JSON, Markdown eller text, och listor som CSV.</p>
"""

KALLOR_INGRESS = (
    "Alla källor i Fornmed i bokstavsordning, med de språkversioner som finns och licensen för var och en."
)

KALLOR_TEXT = """
<p>Varje språkversion är en utgåva av verket. En version kan vara</p>
<ul>
<li><b>original</b>: källans text i utgåva eller transkription,</li>
<li><b>översättning</b>: en tryckt översättning av en namngiven översättare,</li>
<li><b>maskinöversättning</b>: en svensk översättning gjord av en språkmodell. Den är ogranskad och får inte citeras som översättning; hänvisa till originalet eller en tryckt översättning,</li>
<li><b>maskintranskription</b>: originaltext som en språkmodell läst av från sidbilder. Den är ogranskad och bör kontrolleras mot sidbilden.</li>
</ul>
<p>Titeln leder till texten i originalet och språket till den versionen. Där kan texten också visas sida vid sida med en översättning och hämtas som Markdown, text eller JSON. Medeltidsbreven och runinskrifterna är tusentals verk och redovisas som en post var.</p>
"""

PASTAENDEN_INGRESS = (
    "Ett påstående beskriver vad en källa hävdar, inte vad som hände. Fornmed har i dag tre "
    "samlingar av påståenden: en regelbaserad ur SDHK och två piloter där en språkmodell har "
    "tagit ut påståendena ur originaltexten och en oberoende andra extraktion har kontrollerat dem."
)

PASTAENDEN_TEXT = """
<h2>Vad ett påstående är</h2>
<p>Ett påstående har ett subjekt, ett predikat och ett objekt eller värde: <i>Peter i Skeda</i> <i>innehar ämbete</i> <i>häradshövding i Hanekinds härad</i>. Det kan ha en tid och en plats, och det är alltid knutet till den passage som hävdar det, i de flesta fall med ett ordagrant citat ur originaltexten. Varje påstående anger hur det har tagits fram (med regler, av en språkmodell eller för hand) och om det har granskats.</p>
<p>Påståendet säger alltså vad källan hävdar. Om det stämmer är en annan fråga, och den besvaras med bedömningar: en forskares eller en publikations omdöme om påståendets historicitet, om källans äkthet eller om att två namn avser samma person. När bedömningarna går isär redovisas alla, med bedömare och publikation.</p>
<p>Personer, platser, ämbeten och begrepp är entiteter som delas mellan källorna. Kungarna i Västgötalagens konungalängd är samma entiteter som utfärdarna i medeltidsbreven, och samma person behåller sitt id mellan versionerna av databasen.</p>

<h2>Medeltidsbreven i SDHK</h2>
<p><b>87 090 påståenden ur 38 113 brev, regelbaserade och ogranskade.</b></p>
<p>Riksarkivets kartotek anger för de flesta brev vem som utfärdade dem, till exempel ”Biskop Knut i Linköping”. Fältet tolkas med regler till tre slags påståenden: att personen utfärdar brevet (47 979), har en titel eller ett ämbete (20 922) och har ett stånd som riddare eller väpnare (6 282). Påståendena dateras med brevets datum.</p>
<p>Vem ett namn avser avgörs i flera steg. Regenter, påvar och biskopar slås upp i auktoritetslängderna, som anger åren för varje titel. Brevets datering avgör sedan om personen bar titeln då, ännu inte bar den, hade förlorat den eller redan var död. ”Kung Albrekt” år 1395 blir Albrekt av Mecklenburg med anmärkningen att han inte längre var kung. När flera kandidater passar lika bra kopplas brevet inte till någon av dem; kandidaterna registreras i stället som möjliga identifieringar. Stadsråd, kloster och domkapitel blir en institution per ort, och övriga personer slås samman försiktigt när namn, ort eller ämbete och tid stämmer.</p>
<p>Ur regesternas första mening tas dessutom gärningarna: vem som säljer, skänker, pantsätter, testamenterar, upplåter, förlänar, byter, stadfäster, dömer eller utnämner, till vem, vilken egendom det gäller och priset. Det ger omkring 11 900 påståenden. Mottagarna identifieras på samma sätt som utfärdarna, så den som köper jord i ett brev och säljer i ett annat är samma person.</p>
<p>Utfärdarfältet är Riksarkivets registeruppgift och inte ett citat ur brevet, och regesten är en modern sammanfattning. Påståendena har därför inget citat. Kända svagheter är att samma person kan bli flera entiteter när fältet saknar ort eller ämbete, och att altaren och kapell utan ortnamn inte alltid känns igen som mottagare.</p>

<h2>Pilot 1: Västgötalagens längder</h2>
<p><b>222 påståenden ur konunga-, lagmans- och biskopslängden, extraherade av språkmodell och kontrollerade med en oberoende extraktion.</b></p>
<p>Längderna i Äldre Västgötalagens handskrift räknar upp kungar, lagmän och biskopar med korta omdömen. Ur dem har vi tagit ut ämbeten, ordningen mellan innehavarna, föräldrar och syskon, födelseort, död, dråp och gravplats (166 påståenden), och gärningar som kyrkbyggen, broar, gåvor, lagstiftning och erövringar (56 påståenden). Varje påstående har ett ordagrant citat ur den fornsvenska texten, och citaten är kontrollerade mot passagerna.</p>
<p>Piloten prövade granskningsmodellen: en annan språkmodell gjorde en egen extraktion utan att se den första, och en människa avgjorde bara skillnaderna. Versionerna var överens om 157 av 162 påståenden. Personerna är länkade till samma entiteter som i SDHK och biskopslängden. Där längden och den gängse identifieringen inte stämmer överens, som för Emund Kolbränna och Anund Jakob, får längdens person en egen entitet och identifieringen en bedömning.</p>

<h2>Pilot 2: Normer i lagarna</h2>
<p><b>2 235 påståenden ur 23 lagtexter, extraherade av språkmodell och kontrollerade i sin helhet med en oberoende extraktion.</b></p>
<p>Piloten är den första fasen i ett tema om statsbildning genom lagarna. Den omfattar landskapslagarna med fragment och tillägg, Hednalagen, Vidhemsprästens anteckningar, Bjärköarätten, Magnus Erikssons land- och stadslag, Kristoffers landslag och Grágás, och fem ämnen: dråp, edsöre, jäv och oväld, lagstiftning och konungaval.</p>
<p>Normerna har ett begrepp som subjekt och lagen som källa: <i>dråp</i> har <i>påföljd</i> <i>mansbot, nio marker</i>. Predikaten anger påföljd, vem böterna tillfaller, var målet handläggs, vad som krävs, vad som diskvalificerar en domare, nämndeman eller ett vittne, vem som utser och hur lagen definierar ett begrepp. 173 begrepp, från tvebot och mordgäld till sägnarting och kungsnämnd, finns i begreppsregistret med Schlyters och Söderwalls artiklar. Påståenden om vem som stiftade eller stadfäste en lag pekar på personerna, som kung Birger, Magnus Eriksson och lagmännen.</p>
<p>Kontrollen gjordes i två steg. Ett stratifierat stickprov om 53 flockar visade att versionerna täckte samma regler i omkring 85 procent av fallen. Det var för lite, så hela materialet extraherades en andra gång. De 2 034 skillnaderna prövades mot texten, vilket gav 189 tillagda, 58 rättade och 67 borttagna påståenden. Principfrågorna, som hur rån och domarens ansvar ska behandlas, avgjordes av projektägaren. Påståendena är ordnade efter landsdel, så att skillnaderna mellan Götaland, Svealand, Gotland, Skåne, städerna, riket och Island går att jämföra.</p>

<h2>Dessutom</h2>
<p>Ett litet handregistrerat testfall om Hygelac, Beowulf och ynglingakretsen visar hur oberoende och beroende källor och omstridda identifieringar registreras. Där finns till exempel frågan om vilka gēatas var, med var sin forskares ståndpunkt.</p>

<h2>Fortsatt arbete</h2>
<p>Påståendesamlingarna ska fyllas på med samma granskningsmodell som i piloterna: en språkmodell extraherar, en annan gör en oberoende extraktion och en människa avgör skillnaderna. En fullständig granskning av varje påstående mot utgåvan skulle ta veckor per källa; modellen koncentrerar arbetet till det som är osäkert. Planerat är:</p>
<ul>
<li><b>Fler faser i lagtemat.</b> Fler brottsrubriceringar och påföljder och de förvaltnings- och statsrättsliga begreppen, för att kunna svara på hur lag och förvaltning växte fram, vilka som var inblandade, varför, och hur landsdelarna skilde sig åt.</li>
<li><b>Gärningar ur längderna</b> med oberoende extraktion, som i den första piloten.</li>
<li><b>Teman valda efter kunskapsluckor.</b> Ämnena väljs efter de luckor som forskningsöversikter pekar ut. Två förslag är statsbildning och kungamakt jämförd mellan Svealand, Götaland, Gotland, Skåne och de små landen i Småland, och kommersialisering och städer med belägg ur breven, som köping, stad och myntväsen.</li>
<li><b>Beowulf-kretsen.</b> Gutertolkningen av gēatas som ett fjärde alternativ, med Wulfstans beskrivning av Gotland, Gutasagan och Jordanes som underlag.</li>
<li><b>Fler källor och bättre identifiering.</b> Fler källor att knyta påståenden till, och en fortsatt sammanslagning av personer som förekommer i flera källor, med stabila id:n så att länkar inte bryts.</li>
<li><b>Granskade bedömningar.</b> Forskningens ståndpunkter kontrollerade mot publikationerna, så att bedömningarna kan markeras som granskade.</li>
</ul>
<p>Nya samlingar meddelas under <a href="/uppdateringar/">uppdateringar</a>.</p>
"""

MCP_INGRESS = (
    "Fornmed är en MCP-server. En AI-assistent som Claude kan söka i källorna, läsa passager och "
    "följa påståenden och bedömningar genom den, med källhänvisning till varje uppgift."
)

MCP_TEXT = """
<p>Adressen är <code>https://mcp.fornmed.se</code>. Servern kräver ingen inloggning.</p>
<h2>Ansluta från Claude</h2>
<p>claude.ai och Claude Desktop delar samma anslutningsmekanism (”Anpassade anslutningar”, på engelska custom connectors, via remote MCP). Under Customize (Anpassa) → Connectors (Anslutningar), välj ”Lägg till anpassad anslutning”, ange serveradressen (<code>https://mcp.fornmed.se</code>) och lämna autentiseringsvalet på ”Ingen”. <a href="https://support.claude.com/en/articles/11503834-build-custom-connectors-via-remote-mcp-servers">support.claude.com — Build custom connectors via remote MCP servers</a>, läst 2026-09-07.</p>
<p>Claude Code ansluts från kommandoraden:</p>
<p><code>claude mcp add --transport http fornmed https://mcp.fornmed.se</code></p>
<p><a href="https://code.claude.com/docs/en/mcp">code.claude.com — Connect Claude Code to tools via MCP</a>, läst 2026-09-07.</p>
<h2>Ansluta från ChatGPT</h2>
<p>I ChatGPT desktop app (macOS): öppna Inställningar → Pluginer, välj fliken MCP:er, klicka Lägg till → Lägg till MCP-server. I formuläret ”Sammanlänka med en anpassad MCP”: ange valfritt namn, välj typen Strömningsbar HTTP (inte STDIO), och ange serveradressen (<code>https://mcp.fornmed.se</code>) som URL. Fälten för bärartoken och huvuden lämnas tomma, eftersom servern inte kräver någon autentisering. Klicka Spara. Inget utvecklarläge behövs för det här flödet, till skillnad från webbversionen. Flödet är verifierat direkt i ChatGPT desktop app, macOS, 2026-09-08.</p>
<h2>Ansluta från Gemini</h2>
<p>Gemini CLI läser MCP-servrar ur sin egen inställningsfil, antingen i hemkatalogen eller i det aktuella projektet:</p>
<p><code>{"mcpServers": {"fornmed": {"httpUrl": "https://mcp.fornmed.se"}}}</code></p>
<p><a href="https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html">google-gemini.github.io — MCP servers with the Gemini CLI</a>, läst 2026-09-07. Gemini-appen (konsumentversionen, till skillnad från CLI:t och företagsutgåvorna) har inte något dokumenterat stöd för anpassade fjärr-MCP-servrar vid samma läsdatum. Det är alltså inte verifierat att den fungerar, snarare tvärtom.</p>
<h2>Verktygen</h2>
<ul>
<li><code>fornmed_sok</code>: sökning i regester och översättningar, och vid behov i originaltexterna, med både ordträffar och betydelselikhet</li>
<li><code>fornmed_hamta_passage</code> och <code>fornmed_hamta_verk</code>: läs en passage eller ett verk med utgåvor, vittnen och bedömningar</li>
<li><code>fornmed_sok_entitet</code>, <code>fornmed_hamta_entitet</code> och <code>fornmed_hamta_pastaende</code>: personer, platser, folk och ämbeten med påståenden och identifieringar</li>
<li><code>fornmed_omstridda</code>: var forskningen är oenig</li>
<li><code>fornmed_begrepp</code> och <code>fornmed_ordbok</code>: medeltida begrepp och Schlyters och Söderwalls ordböcker</li>
<li><code>fornmed_vokabular</code> och <code>fornmed_oversikt</code>: klassificeringarna och databasens omfång</li>
</ul>
<h2>Att tänka på</h2>
<p>Servern ger assistenten samma regler som står under <a href="/metod/">metod och källkritik</a>: att ett påstående är vad källan hävdar, att maskinöversättningar inte får citeras som översättning och att oeniga bedömningar ska redovisas var för sig. Be gärna assistenten ange passagens adress och utgåva när den citerar.</p>
"""

API_INGRESS = (
    "Allt i Fornmed finns i ett öppet REST-API. Det kräver ingen nyckel och beskrivs med OpenAPI."
)

API_TEXT = """
<p>Adressen är <code>https://api.fornmed.se</code>. Dokumentationen med alla resurser och parametrar finns på <a href="https://api.fornmed.se/docs">api.fornmed.se/docs</a>, och beskrivningen på <code>/openapi.json</code>.</p>
<h2>Format</h2>
<p>Alla resurser finns som JSON, Markdown och text, och listor också som CSV. Formatet väljs med <code>format=json</code>, <code>md</code>, <code>txt</code> eller <code>csv</code>, eller med Accept-huvudet. Markdown och text inleds med en källhänvisning: verk, utgåva, språk och licens.</p>
<h2>Dokument</h2>
<p>Ett verk hämtas helt i ett svar:</p>
<p><code>https://api.fornmed.se/v1/verk/verk:lag:aldre_vastgotalagen/text?format=md</code></p>
<p>Stora verk kan också hämtas del för del, till exempel en balk eller en bok: <code>/v1/verk/{id}/delar</code> listar delarna. <code>sprak=</code> väljer språkversion i prioritetsordning (<code>sprak=swe,dan,lat</code>), och <code>sprak=fsv,swe&amp;parallellt=true</code> ger original och översättning passage för passage.</p>
<h2>Listor och sökning</h2>
<ul>
<li><code>/v1/sok?q=…</code>: sökning, som MCP-verktyget</li>
<li><code>/v1/verk</code>, <code>/v1/pastaenden</code>, <code>/v1/bedomningar</code>: listor med filter</li>
<li><code>/v1/auktoriteter/biskopar?sate=Uppsala&amp;format=csv</code>: ärkebiskoparna i Uppsala</li>
<li><code>/v1/verk?plats=plats:kommun:1281</code>: källor från platser i Lunds kommun</li>
<li><code>/v1/leveranser</code>: databasens uppdateringar</li>
</ul>
<p>Listor delas upp i sidor med <code>sida</code> och <code>per_sida</code>. Hela databasen går inte att hämta i ett anrop; hämta de dokument och listor du behöver.</p>
<h2>Villkor</h2>
<p>API:et är öppet med en gräns på tio anrop i sekunden per adress. Licensen för texterna anges i varje svar och i <a href="/kallor/">källförteckningen</a>. Maskinöversättningar är märkta som ogranskade.</p>
"""

METOD_INGRESS = (
    "Fornmed är byggt för att skilja det en källa hävdar från det forskningen bedömer, och för att "
    "visa varifrån varje uppgift kommer."
)

METOD_TEXT = """
<h2>Källor i fyra nivåer</h2>
<p>Varje källa beskrivs som ett <b>verk</b> (texten som helhet, till exempel Västgötalagen), dess <b>vittnen</b> (bevarade handskrifter, avskrifter och registraturer, med egen datering), dess <b>utgåvor</b> (tryckta eller digitala, med licens) och dess <b>passager</b>, de citerbara textenheterna. Händelsens, textens och handskriftens tid hålls därmed isär.</p>
<h2>Påståenden och tidsavstånd</h2>
<p>Ett påstående beskriver vad en källa hävdar. Det redovisas alltid med källans genre och det minsta möjliga tidsavståndet mellan händelsen och källan. En krönika skriven tvåhundra år efter händelserna är ett annat belägg än ett brev från samma år.</p>
<p>När en källa återger en annan registreras det som ett beroende. Den senare källan ger då inte oberoende stöd, hur många gånger uppgiften än upprepas.</p>
<h2>Bedömningar och oenighet</h2>
<p>Forskningens omdömen registreras som bedömningar, flera per påstående, verk eller identifiering, med bedömare, publikation och granskningsstatus. De vägs aldrig samman till en. Där bedömningarna går isär visas alla ståndpunkter.</p>
<p>Bedömningar som inte har kontrollerats mot publikationen är märkta som ogranskade och ska presenteras så. En bedömning av ett brev som misstänkt förfalskning gäller hela brevet och bör nämnas när brevet används som belägg.</p>
<h2>Översättningar</h2>
<p>Där det finns fria äldre översättningar används de. Övriga texter har svenska översättningar gjorda av en språkmodell. De gör texterna sökbara på svenska, men de är ogranskade och får inte citeras som översättning. Markeringen [osäker tolkning] anger att översättningen är osäker på det stället.</p>
<h2>Begrepp och ordböcker</h2>
<p>Begreppsregistret förklarar medeltida begrepp som ledung, frälse och härad, med termer på fornsvenska, fornvästnordiska och latin. Registrets definitioner är ett ogranskat utkast. Den citerbara källan är ordböckernas egna artiklar: Schlyters ordbok till lagarna och Söderwalls ordbok över medeltidsspråket.</p>
<h2>Geografiska platser</h2>
<p>Platserna i breven och runinskrifterna är kopplade till entiteter, och källans namnform behålls alltid. Stommen är Riksantikvarieämbetets socknar, kommuner, län, landskap och länder, med koordinater från Wikidata. Det gör att källor kan sökas på en nutida kommun eller socken.</p>
<p>Vilken nutida plats en brevort avser har oftast bedömts av oberoende språkmodeller, och uppgiften används bara när minst två är överens. Kopplingarna är inte kontrollerade av människa och är märkta som ogranskade. Ett läge som bara är känt på socken- eller ortsnivå är märkt som närmevärde. Omkring 15 procent av breven med ort saknar ännu nutida plats, och det arbetet fortsätter.</p>
<h2>Auktoritetslängderna</h2>
<p>Längderna över regenter, biskopar och påvar används för att identifiera personer i breven. De är sammanställda ur allmänna uppslagsverk och svenska Wikipedia och inte kontrollerade mot primärlitteraturen. Listornas år är ofta ungefärliga, och det ursprungliga uttrycket finns bevarat.</p>
"""

UPPDATERINGAR_INGRESS = (
    "Nya källor, fler påståenden och andra ändringar i databasen, senaste först. Varje leverans av "
    "databasen redovisas med vad som tillkommit."
)

LICENSER_INGRESS = "Källorna i Fornmed har olika licenser. Licensen för varje text anges med texten."

LICENSER_TEXT = """
<p>Licensen står i varje svar från API:et och MCP-servern och i <a href="/kallor/">källförteckningen</a>. De viktigaste:</p>
<ul>
<li><b>SDHK:</b> Riksarkivet, CC BY 4.0.</li>
<li><b>Runinskrifterna:</b> Rundata.info, Stockholms universitet, som bygger på Samnordisk runtextdatabas, Uppsala universitet. ODbL 1.0, innehållet DbCL 1.0, med Uppsala runforums tilläggsvillkor. Uppgifter ur Rundata ska anges med källa.</li>
<li><b>Lagarna och de fornsvenska krönikorna:</b> Fornsvenska textbanken, Lunds universitet, via Språkbanken Text, Göteborgs universitet, CC BY 4.0.</li>
<li><b>Schlyters och Söderwalls ordböcker:</b> Språkbanken Text, Göteborgs universitet, CC BY 4.0.</li>
<li><b>MGH:</b> Monumenta Germaniae Historica och Bayerische Staatsbibliothek, openMGH, CC BY 4.0.</li>
<li><b>Sagorna, Eddorna och Heimskringla:</b> heimskringla.no och sagadb.org. Utgåvorna är fria; normaliseringen i Guðni Jónssons utgåvor har upphovsrätt och används icke-kommersiellt.</li>
<li><b>Transkriptioner från Wikisource:</b> CC BY-SA 4.0. Biskopslängden bygger på svenska Wikipedia och har samma licens.</li>
<li><b>Geografisk stomme:</b> Riksantikvarieämbetet, K-samsöks geografiska auktoriteter, och Wikidata, båda CC0.</li>
<li><b>Arabiska källor:</b> OpenITI, CC BY-NC-SA 4.0.</li>
<li><b>Romerska källor:</b> Perseus Digital Library, CC BY-SA 4.0, och The Latin Library.</li>
<li><b>Äldre utgåvor ur Internet Archive och Project Runeberg:</b> fria från upphovsrätt.</li>
</ul>
<p>Fornmed är ett icke-kommersiellt projekt. Typsnitten Source Sans 3 och EB Garamond är fria under SIL Open Font License 1.1. Besöksstatistiken förs med Umami utan kakor, och IP-adresserna i serverns loggar anonymiseras.</p>
"""

# Sidor som visar databasens omfång under texten
VISA_OMFANG = {"metod"}

# (klass, slug, titel, ingress, brödtext, i menyn)
SIDOR = [
    (KallforteckningSida, "kallor", "Källor", KALLOR_INGRESS, KALLOR_TEXT, True),
    (TextSida, "pastaenden", "Påståendesamlingarna", PASTAENDEN_INGRESS, PASTAENDEN_TEXT, True),
    (TextSida, "metod", "Metod och källkritik", METOD_INGRESS, METOD_TEXT, True),
    (TextSida, "mcp", "Använd med AI", MCP_INGRESS, MCP_TEXT, True),
    (TextSida, "api", "API", API_INGRESS, API_TEXT, True),
    (UppdateringarSida, "uppdateringar", "Uppdateringar", UPPDATERINGAR_INGRESS, "", True),
    (TextSida, "licenser", "Licenser", LICENSER_INGRESS, LICENSER_TEXT, False),
]


class Command(BaseCommand):
    help = __doc__.split("\n\n")[0]

    def add_arguments(self, tolk):
        tolk.add_argument("--skriv-over", nargs="*", metavar="SLUG",
                          help="ersätt texterna i de angivna sidorna, eller i alla, med dem i kommandot")

    @transaction.atomic
    def handle(self, *args, skriv_over: list[str] | None = None, **kwargs):
        def ska_skrivas_over(slug: str) -> bool:
            return skriv_over is not None and (not skriv_over or slug in skriv_over)

        rot = Page.get_first_root_node()
        start = StartSida.objects.first()
        if start is None:
            start = StartSida(title="Fornmed", slug="fornmed", ingress=START_INGRESS, brodtext=START_TEXT,
                              seo_title="Fornmed – källor till Sveriges och Nordens forntid och medeltid",
                              search_description=START_INGRESS)
            rot.add_child(instance=start)
            self.stdout.write("Skapade startsidan.")
        elif ska_skrivas_over("start"):
            start.ingress, start.brodtext = START_INGRESS, START_TEXT
            start.save_revision().publish()

        # Webbplatsen pekas om till startsidan innan Wagtails exempelsida från
        # första migreringen tas bort; annars tar borttagningen platsen med sig
        site = Site.objects.filter(is_default_site=True).first() or Site(is_default_site=True)
        site.root_page = start
        site.hostname = "fornmed.se"
        site.port = 443
        site.site_name = "Fornmed"
        site.save()
        for gammal in Page.objects.child_of(rot).exclude(id=start.id):
            if gammal.specific_class is Page:
                gammal.delete()

        for klass, slug, titel, ingress, text, i_menyn in SIDOR:
            sida = start.get_children().filter(slug=slug).specific().first()
            if sida is None:
                sida = klass(title=titel, slug=slug, ingress=ingress, brodtext=text,
                             show_in_menus=i_menyn, search_description=ingress,
                             visa_omfang=slug in VISA_OMFANG)
                start.add_child(instance=sida)
                self.stdout.write(f"Skapade {titel}.")
            elif ska_skrivas_over(slug):
                sida.title, sida.ingress, sida.brodtext = titel, ingress, text
                sida.visa_omfang = slug in VISA_OMFANG
                sida.show_in_menus = i_menyn
                sida.save_revision().publish()
                self.stdout.write(f"Skrev över {titel}.")

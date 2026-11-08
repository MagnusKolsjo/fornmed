# Fornmed – driftplan för VPS

<domän> är domänen i `deploy/server.env` (mall: `server.example.env`).

Vad som körs på servern, var det ligger och hur data kommer dit. Upplägget
följer Valvaka.online där inget särskilt skäl talar emot: nginx med certbot,
gunicorn och systemd, Umami och GoAccess för statistik, `/srv/<projekt>` för
kod och `www-data` som tjänsteanvändare.

## Grundprinciper

- **Servern är en mottagare.** Import, embeddings och schemaändringar görs
  lokalt. Servern får färdiga databaskopior och kod från git, och inget på
  servern behöver säkerhetskopieras utom det som anges under *Data som bara
  finns på servern*.
- **Allt är läsande och öppet.** MCP och API kräver ingen nyckel. Skyddet är
  en skrivskyddad databasroll och hastighetsbegränsning i nginx.
- **En process för MCP och API.** Embeddingmodellerna laddas en gång och delas.
  Webbplatsen är en egen process, så att den lever vidare om
  söktjänsten startas om.
- **Stabila id:n.** Verk, passager, entiteter och påståenden behåller sina id:n
  mellan databaskopior, så att länkar i API:et och på webben inte bryts.

## Domäner

| Adress | Innehåll | Bakom |
|---|---|---|
| `https://<domän>` | Webbplatsen | nginx → gunicorn (Django/Wagtail) |
| `https://<domän>/id/`, `https://<domän>/def/` | Länkade data: uppslag av URI:er och Fornmeds vokabulär | nginx → fornmed-tjänsten |
| `https://www.<domän>` | 301 till `https://<domän>` | nginx |
| `https://api.<domän>` | REST-API, OpenAPI under `/openapi.json`, dokumentation under `/docs` | nginx → fornmed-tjänsten |
| `https://mcp.<domän>` | MCP över streamable http, utan sökväg | nginx → fornmed-tjänsten |
| `https://stat.<domän>` | Umami, besöksstatistik för webbplatsen | nginx → Umami |
| `https://<domän>/statistik/` | GoAccess-rapport för alla fyra namnen, lösenordsskyddad | nginx (statisk fil) |

A- och AAAA-poster finns för de fyra första namnen. `stat.<domän>` saknar DNS-poster och
behöver samma poster innan certbot körs.

Certifikat: `certbot --nginx` med ett certifikat för samma namn som ovan, förnyas av
`certbot.timer`.

## Tjänster

| systemd-enhet | Vad | Lyssnar på | Kör som |
|---|---|---|---|
| `fornmed-tjanst.service` | FastAPI (API) och MCP-servern i samma uvicorn-process | `127.0.0.1:8424` | `www-data` |
| `postgresql@16-main.service` | Postgres 16 med pgvector | `localhost:5432` | `postgres` |
| `fornmed-goaccess.timer` | Bygger statistikrapporterna var femte minut | – | `root` |
| `fornmed-halsokontroll.timer` | Hälsokontrollen var femte minut (`deploy/halsokontroll.sh`), med larm via Healthchecks.io | – | `root` |
| `umami-<domän>rvice` | Umami 3.3.1 (Node 22, pnpm 12.3.4), byggd av `deploy/installera_umami.sh` | `127.0.0.1:3000` | `www-data` |
| `fornmed-webb.service` | Webbplatsen: Django 5.2 och Wagtail 7.4 i gunicorn, byggd av `deploy/installera_webb.sh` | `unix:/run/fornmed-webb/fornmed-webb.sock` | `www-data` |
| `fornmed-sakerhetskopia.timer` | `pg_dump` av `fornmed_webb` och `umami` varje natt, sparade i 14 dagar | – | `root` |

`fornmed-tjanst` monterar MCP-appen under `/mcp` i FastAPI-appen. nginx skriver om
`https://mcp.<domän>/` till `/mcp`, som för Valvaka, och skickar `api.<domän>`
till resten av appen. Tjänsten läser modellerna utan nätåtkomst och kan bara skriva
i modellkatalogen. Umami har lägre CPU-vikt (`CPUWeight=50`) än söktjänsten och
högst 1 GB minne.

`deploy/startsida/` innehåller sidan som nginx visar när webbplatsen eller söktjänsten
startar om, och indexsidan för statistiken.

## Kataloger

| Sökväg | Innehåll |
|---|---|
| `/srv/fornmed/fornmed/` | Koden, skickad med `deploy/skicka_kod.sh`; ägs av den som skickar |
| `/srv/fornmed/fornmed/.env` | Konfiguration för söktjänsten, skapad av installationsskriptet |
| `/srv/fornmed/venv/` | Python-miljön, utanför kodkatalogen så att `rsync --delete` inte rör den |
| `/srv/fornmed/modeller/` | Embeddingmodellerna (`HF_HOME`), nedladdade vid installationen |
| `/srv/fornmed/inkommande/` | De två senaste databaskopiorna |
| `/var/www/fornmed/` | Startsidan, sidan som visas vid omstart och den grafiska profilen |
| `/var/www/goaccess-fornmed/` | GoAccess-rapporterna |
| `/etc/nginx/sites-available/<domän>` | nginx-konfigurationen, med certbots 443-block |
| `/etc/postgresql/16/main/conf.d/fornmed.conf` | Postgres minnesinställningar |
| `/srv/fornmed/umami/` | Umami med `.env` och `webbplats-id` (webbplatsens id, som startsidans spårning använder) |
| `/etc/nginx/fornmed-admin.conf` | Adresserna som når Umamis inloggning (`--admin-ip`) |
| `/var/lib/fornmed/` | Hälsokontrollens senaste utskrift och räknare för röda körningar |
| `/srv/fornmed/fornmed/webb/` | Webbplatsens kod, med `.env` skapad av `installera_webb.sh` |
| `/srv/fornmed/webb-venv/` | Webbplatsens Python-miljö |
| `/srv/fornmed/webb-static/`, `/srv/fornmed/webb-media/` | Statiska filer och uppladdade bilder |
| `/srv/fornmed/sakerhetskopior/` | Nattliga kopior av webbplatsens och Umamis databaser |

## Databaser

| Databas | Innehåll | Ursprung |
|---|---|---|
| `fornmed` | Källorna, påståendena, vokabulärerna, embeddings och leveranserna | Kopia av den lokala `fornmed`, ersätts vid varje leverans |
| `fornmed_foregaende` | Den förra kopian | Kvar till nästa leverans, för att kunna återställa |
| `fornmed_webb` | Wagtail-sidor och uppdateringsinlägg | Skapas på servern av `installera_webb.sh` |
| `umami` | Besöksstatistik | Skapas på servern av `installera_umami.sh` |

Kopiorna läses in av `postgres`, utan ägare och behörigheter från utvecklingsdatorn.
Söktjänsten ansluter som `fornmed_las`, som bara har `SELECT` på schemat `fornmed`;
inläsningsskriptet ger rättigheterna på nytt efter varje kopia.

Postgres 16 och pgvector hämtas från PostgreSQL:s apt-arkiv (PGDG), eftersom
Ubuntu 26.04 levererar en nyare huvudversion. Huvudversionen måste vara densamma som
i den lokala Postgres.app, och kopian måste göras med Postgres.app:s `pg_dump` i
version 16: en kopia från en nyare `pg_dump` kan inte läsas av en äldre
`pg_restore`. pgvector får vara en nyare underversion på servern (i dag 0.8.7 mot
0.8.2 lokalt); dumpen låser inte versionen och indexen är kompatibla.

## Installation

1. På utvecklingsdatorn, från produktionsmappen:
   `deploy/skicka_kod.sh --bara-kod`
2. På servern:
   `sudo bash /srv/fornmed/fornmed/deploy/installera_server.sh --epost <ADRESS> --admin-ip <ADRESS>`.
   Skriptet installerar paketen, Postgres med pgvector, Python-miljön med PyTorch
   för CPU, modellerna, systemd-enheterna, startsidan, nginx och certifikaten. Det
   kan köras om; `.env`, modellerna, certifikaten och databasen behålls.
3. Lösenord för statistiken:
   `sudo htpasswd -c /etc/nginx/fornmed-statistik.htpasswd <ANVÄNDARE>`, och ett nytt
   lösenord för Umamis konto `admin` på `https://stat.<domän>`.
   Healthchecks: skapa en kontroll och lägg ping-adressen som
   `FORNMED_HEALTHCHECKS_URL=` i `/srv/fornmed/fornmed/.env`.
4. Den första databaskopian, på utvecklingsdatorn:
   `deploy/skicka_databas.sh "Första leveransen"`.

Därefter skickas ny kod med `deploy/skicka_kod.sh` och nya kopior med
`deploy/skicka_databas.sh`. En misslyckad kopia lämnar den gamla orörd, och
`sudo bash deploy/las_in_databas.sh --aterstall` tar tillbaka den förra.

## Leverans av data

`deploy/skicka_databas.sh "<anmärkning>"` gör allt i ett steg:

1. `leverans.py` skriver en rad i `fornmed.leverans` med antal per tabell och
   källsamling och skillnaden mot förra leveransen, och gör sedan kopian med
   `pg_dump -Fc` i version 16. Raden följer alltså med kopian, och historiken
   finns kvar när servern byter databas.
2. Kopian skickas med `rsync` till `/srv/fornmed/inkommande/`.
3. På servern läser `deploy/las_in_databas.sh` in den i `fornmed_ny` medan
   tjänsten svarar från `fornmed`, kör `ANALYZE` och kontrollerar att verk,
   passager, vektorer och fulltextindex finns.
4. Om kontrollen går igenom byter databaserna namn (`fornmed` →
   `fornmed_foregaende`, `fornmed_ny` → `fornmed`) i en transaktion, så att
   `fornmed` hela tiden finns. Den gamla databasen stängs för nya anslutningar
   under de millisekunder bytet tar, och `db.py` låter en anslutning som kommer
   just då vänta och försöka igen. Söktjänsten startas inte om: modellerna ligger
   kvar i minnet och MCP-sessionerna överlever, och webbplatsens anslutningar
   kontrolleras före varje begäran. Svarar tjänsten inte med den nya kopian byts
   namnen tillbaka. I ett prov med två byten under kontinuerlig belastning
   misslyckades inga av 444 API-anrop, 278 MCP-anrop och 120 sidvisningar.

`FORNMED_PYTHON` och `FORNMED_PG_DUMP` anger Python-miljön och `pg_dump` i
version 16, i miljön eller i den lokala `.env`.

Webbplatsens uppdateringslista och `/v1/leveranser` bygger på `fornmed.leverans`.

Kod levereras med `git pull` i `/srv/fornmed/fornmed/` och omstart av tjänsten.

## Data som bara finns på servern

- `fornmed_webb`: Wagtail-sidor och manuellt skrivna uppdateringar. Ett nattligt
  `pg_dump` hämtas till den lokala datorn.
- `umami`: besöksstatistik. Ingår i samma nattliga dump.
- `.env`-filerna. En kopia förvaras lokalt i lösenordshanteraren.

Allt annat kan byggas upp igen från git och den lokala databasen.

## Webbplatsen

Django och Wagtail i `webb/`, med samma uppbyggnad som Valvaka och den grafiska
profilen i `grafisk_profil/` (självhostade typsnitt och logotyp, inga
tredjepartsanrop utom Umami på egen subdomän). Texterna redigeras i Wagtail på
`https://<domän>/admin/`, som bara nås från adresserna i
`/etc/nginx/fornmed-admin.conf`. `manage.py skapa_sidor` skapar sidorna med sina
första texter; befintliga sidor lämnas orörda.

Sidor:

- **Start:** vad Fornmed är, databasens omfång och de senaste uppdateringarna.
- **Källor:** alla källor i bokstavsordning med källsamling, licens och
  språkversioner, och om versionerna är maskinöversatta. Hämtas ur Fornmeds
  databas och cachas per leverans. Medeltidsbreven och runinskrifterna är en post var.
- **Påståendesamlingarna:** SDHK, de två piloterna (Västgötalagens längder och
  normerna i lagarna) och det fortsatta arbetet.
- **Metod och källkritik**, **Använd med AI** (MCP), **API** och **Licenser**.
- **Uppdateringar:** leveranserna ur `fornmed.leverans` och skrivna inlägg.

Webbplatsen läser Fornmeds databas med söktjänstens skrivskyddade roll och har
en egen databas, `fornmed_webb`, för sidorna. Går Fornmeds databas inte att nå
visas sidorna ändå, utan källförteckning.

## Statistik

- **Umami** på `stat.<domän>` för webbplatsen. Kakfri och självhostad.
  Spårningsskriptet och insamlingen (`/script.js`, `/api/send`) är öppna; resten,
  med inloggningen, nås bara från adresserna i `/etc/nginx/fornmed-admin.conf`.
  Umami skapar kontot `admin` med lösenordet `umami`, som byts vid första
  inloggningen. Webbplatsen registreras direkt i databasen av installationen.
  Umami räknar bara besök på webbplatsen: anrop till API:et och MCP-servern kör
  inget skript och syns bara i GoAccess.
- **GoAccess** för alla fyra namnen, ur nginx-loggar med anonymiserade IP-adresser,
  samma `log_format anonymiserad` som för Valvaka. Varje namn får en egen
  loggfil, så att API- och MCP-användning syns för sig.
- **Användning per resurs:** API-loggen räcker för att se vilka endpoints som används.
  MCP-anrop loggas av tjänsten med verktygsnamn men utan frågetext.

## Övervakning

`deploy/halsokontroll.sh` körs var femte minut och kontrollerar söktjänsten
lokalt, `https://<domän>`, `https://api.<domän>` med att databasen har
innehåll, en MCP-handskakning mot `https://mcp.<domän>`, Umami, ledig disk
(minst 3 GB) och certifikatets giltighet (minst 14 dagar). Svarar söktjänsten
inte lokalt startas den om först.

Larmen går via Healthchecks.io, som för Valvaka. Ping-adressen står i
`FORNMED_HEALTHCHECKS_URL` i serverns `.env`. Vid grönt pingas kontrollen;
uteblir pingen larmar Healthchecks när fristen löpt ut. Är kontrollen röd två
körningar i följd skickas utskriften till `/fail`, så att larmet säger vad som
fallerade. Kontrollen hos Healthchecks sätts till period 5 minuter och frist 15
minuter. Under en databasinläsning görs ingenting.

## Hastighetsbegränsning

| Zon | Gäller | Gräns |
|---|---|---|
| `webb_per_ip` | `<domän>` | 20 begäranden/s, kö 100 |
| `api_per_ip` | `api.<domän>` | 10 begäranden/s, kö 30 |
| `mcp_lasning` | `mcp.<domän>` | 10 begäranden/s, kö 20 |

Söktjänsten har dessutom en övre gräns för samtidiga embeddingberäkningar (två
sökningar åt gången), så att en skrapare inte kan ta all CPU. Lyckade API-svar får
`Cache-Control: public, max-age=300`, eftersom datan bara ändras vid leveranser.

## API

FastAPI, versionerat under `/v1`, OpenAPI 3.1. Koden finns i `api.py`,
`dokument.py` (hela dokument, delar och språkversioner), `listor.py` (listor med
filter) och `svarsformat.py`. `tjanst.py` kör API:et och MCP-servern i samma
process. Allt är `GET`. Listor pagineras med `sida` och `per_sida` (högst 500) och
har `total` i JSON och `X-Total` i huvudet. Varje svar med källtext innehåller
licens, utgåva och versionens typ, och maskinöversättningar har `ogranskad` och en
anmärkning, så att regeln om ogranskade översättningar följer med datan.

API:et och MCP-verktygen anropar samma funktioner i `fragor.py`, `sok.py`,
`dokument.py` och `listor.py`. Logiken finns bara på ett ställe.

| Resurs | Endpoints | Motsvarande MCP-verktyg |
|---|---|---|
| Översikt | `/v1/oversikt` | `fornmed_oversikt` |
| Källsamlingar | `/v1/kallsamlingar` | – |
| Verk | `/v1/verk` (filter: källsamling, genre, språk, datering, titel), `/v1/verk/{verk_id}` | `fornmed_hamta_verk` |
| Hela dokument | `/v1/verk/{verk_id}/text` (hela versionen i ett svar, eller `fran`/`till`) | – |
| Delar och volymer | `/v1/verk/{verk_id}/delar`, `/v1/verk/{verk_id}/delar/{del}/text` | – |
| Språkversioner | `/v1/verk/{verk_id}/versioner`. Textendpointerna tar `sprak=`, `utgava=`, `roll=` och `parallellt=` | – |
| Utgåvor | `/v1/verk/{verk_id}/utgavor`, `/v1/utgavor/{utgava_id}` | – |
| Passager | `/v1/passager/{passage_id}`, med `sprak=` för samma passage på ett annat språk | `fornmed_hamta_passage` |
| SDHK | `/v1/sdhk/{nummer}` (307 till brevets verk) | – |
| Sökning | `/v1/sok` (`q`, `metod`, `antal`, `ar_fran`, `ar_till`, `genre`, `texttyper`, `expandera`) | `fornmed_sok` |
| Entiteter | `/v1/entiteter` (`namn`, `typ`), `/v1/entiteter/{id}`, `/v1/entiteter/{id}/namnformer`, `/v1/entiteter/{id}/identifieringar` | `fornmed_sok_entitet`, `fornmed_hamta_entitet` |
| Auktoriteter | `/v1/auktoriteter`, `/v1/auktoriteter/{langd}` (filter: titel, säte eller rike, år), `/v1/auktoriteter/{langd}/{person_id}` | – |
| Påståenden | `/v1/pastaenden` (filter: entitet, predikat, verk, källsamling, extraktion, granskad, år), `/v1/pastaenden/{id}` med bedömningar och relationer | `fornmed_hamta_pastaende` |
| Bedömningar | `/v1/bedomningar` (filter: påstående, verk, aspekt, bedömare, `granskad`) | – |
| Omstridda | `/v1/omstridda` | `fornmed_omstridda` |
| Vokabulärer | `/v1/vokabularer`, `/v1/vokabularer/{schema}` | `fornmed_vokabular` |
| Begrepp | `/v1/begrepp/{term}` | `fornmed_begrepp` |
| Ordböcker | `/v1/ordbok` (`ord`, `ordbok`) | `fornmed_ordbok` |
| Leveranser | `/v1/leveranser`, `/v1/leveranser/{id}` (det som webbens uppdateringslista bygger på) | – |
| Hälsa | `/halsa` (utanför `/v1`, bara en anslutning till databasen) | – |

### Auktoriteter

Auktoriteterna är längderna över ämbetsinnehavare: regenter, biskopar och påvar
(`data/auktoriteter/*.json`). `auktoriteter.py` läser in dem i tabellerna
`auktoritetslangd`, `auktoritet` (person, levnadsår, Wikidata-id) och
`auktoritet_titel` (titel, säte eller rike, från, till och längdens ursprungliga
årsuttryck), så att de följer med databaskopian. `person_id` är personens
entitets-id; samma person har samma id i alla längder. Kör skriptet igen när
filerna ändrats.

Varje längd har sin egen licens och beskrivning, och de följer med i svaret.
Biskopslängden bygger på svenska Wikipedia och har därför CC BY-SA 4.0. Den
licensen kräver att bearbetningar delas under samma villkor. Regent- och
påvelängderna är projektets egna sammanställningar och har ingen egen licens
angiven.

### Format

Alla resurser kan hämtas i flera format. Formatet väljs med `format=` i adressen
eller med `Accept`-huvudet. Parametern vinner om båda anges.

| Format | `format=` | Media-typ | Gäller |
|---|---|---|---|
| JSON | `json` (standard) | `application/json` | Alla resurser |
| Markdown | `md` | `text/markdown; charset=utf-8` | Alla resurser |
| Text | `txt` | `text/plain; charset=utf-8` | Dokument, passager, begrepp och ordboksartiklar |
| CSV | `csv` | `text/csv; charset=utf-8` | Alla listor, till exempel verk, påståenden, bedömningar, auktoritetslängder och vokabulärer |

- **JSON** är den fullständiga formen. Övriga format är vyer av samma svar.
- **Markdown** inleds med en källhänvisning: verk, utgåva, passageadress, licens och
  eventuell markering om ogranskad maskinöversättning. Därefter kommer texten. För en
  lista blir det en tabell.
- **Text** är texten utan formatering, med samma källhänvisning som inledande rader.
  Formatet passar för vidare bearbetning i andra verktyg.
- **CSV** har en rad per post och platta kolumner. Nästlade fält, till exempel
  bedömningarna i ett påstående, blir en egen lista med egen endpoint i stället för
  att packas in i en cell. CSV-filen har kolumnrubriker, UTF-8 och komma som
  avgränsare. Den skickas med pagineringen i huvudena `X-Total` och `Link`, så att
  tabellen innehåller bara data.
- Ett format som inte är meningsfullt för resursen, till exempel CSV för en enskild
  passage, ger `406 Not Acceptable` med en lista över de format som finns.

OpenAPI-beskrivningen listar alla media-typer per endpoint, så att klienter som
genererats ur den kan välja format.

### Hela dokument, delar och enskilda passager

Ett dokument hämtas som en helhet, inte sida för sida. `/v1/verk/{verk_id}/text`
ger hela utgåvan i ett svar, med passagerna i ordning. Äldre Västgötalagen är
ett anrop i varje format. Ett Markdown- eller textsvar är löpande text med
passageadresserna som rubriker, så att varje stycke fortfarande går att citera.

Verk som består av flera delar kan också hämtas del för del. Det gäller
volymer, böcker, balkar och liknande. `/v1/verk/{verk_id}/delar` listar delarna
med typ, namn och antal passager, och `/v1/verk/{verk_id}/delar/{del}/text` ger
en del i ett svar. Delen står i `passage.del` och `passage.del_typ` (bok, del,
balk, saga, avsnitt, volym). `struktur.py` fyller i dem ur passageadressen; i dag
har 33 verk delar. Delarna listas i den ordning deras första passage har.

### Språkversioner

Många verk finns på flera språk, till exempel Äldre Västgötalagen på fornsvenska
och i svensk maskinöversättning, Saxo på latin och i Winkel Horns danska
översättning, och Adam av Bremen på latin och svenska. Varje språkversion är en
utgåva.

- `/v1/verk/{verk_id}/versioner` listar utgåvorna. För varje utgåva anges språk
  (ISO 639-3: `lat`, `fsv`, `non`, `swe`, `dan` med flera), typ (`original`,
  `oversattning`, `maskinoversattning` eller `maskintranskription`), översättare och år för äldre
  översättningar, licens, roll (`huvudtext`, `skolier` med flera) och antal passager.
- Textendpointerna (`/text`, `/delar/{del}/text`, `/passager/{id}`) tar `sprak=`.
  Utan `sprak=` blir svaret originalspråket.
- Finns flera utgåvor på samma språk väljs den som har rollen `huvudtext`.
  `utgava=` väljer en bestämd utgåva och gäller före `sprak=`. Adam av Bremens
  skolier hämtas alltså med `utgava=`, eller med `roll=skolier`.
- `sprak=` kan ta flera språk i prioritetsordning, till exempel `sprak=swe,dan,lat`.
  Svaret blir då det första språk som finns för verket. Det gör det enkelt att be om
  svenska när det finns och annars originalet.
- En begärd språkversion som saknas ger `404` med en lista över de språk som finns.
- En passage kan hämtas parallellt på flera språk med `sprak=fsv,swe&parallellt=ja`.
  Svaret innehåller då samma passageadress i varje språk, vilket gör texterna lätta
  att jämföra rad för rad.
- Maskinöversatta versioner märks i varje svar, i Markdown- och textformaten
  med en rad överst om att översättningen är ogranskad och inte får citeras som
  översättning.

Fälten `sprak`, `typ`, `roll`, `oversattare` och `ar` på `utgava` fylls i av
`struktur.py`. Runinskrifternas utgåvor har flera språk i samma utgåva
(translitterering, normalisering och översättning) och inget eget språk. Där
filtreras passagerna på passagens eget språk.

Den som bara vill ha ett visst ställe hämtar passagen med `/v1/passager/{id}`
eller ett avsnitt med `fran=` och `till=` (passage-id:n) på textendpointen.

Storlek: den största utgåvan i databasen, Olaus Magnus, är 2,1 miljoner tecken.
Med komprimering (`gzip` i nginx för JSON, Markdown, text och CSV) blir det några
hundra kB över nätet, vilket ett enda svar klarar utan problem. En utgåva över
10 miljoner tecken skulle inte skickas hel. Den ger då `413` med länkar till sina
delar. Ingen utgåva är i dag i närheten av den gränsen.

### Ingen nedladdning av hela datamängden

API:et erbjuder inte hela databasen i ett anrop. Den som vill ha mycket hämtar de
dokument som behövs, ett i taget. Listor (verk, påståenden, bedömningar med flera)
pagineras och har en övre gräns för `per_sida`. Gränsen gäller listor, inte
texterna i ett dokument.

### MCP i öppet läge

`mcp_transport.py` får ett uttryckligt öppet läsläge, som för Valvaka:
`MCP_OPPEN_LASNING=på` startar http-läget utan `MCP_API_KEY`. Utan någon av dem
avbryts uppstarten som i dag, så att en öppen endpoint aldrig uppstår av misstag.

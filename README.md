# Forntida och medeltida Sverige

Databas och MCP-server för källor till Sveriges och Nordens forntid och
medeltid, byggd så att varje uppgift kan spåras till en passage i en källa
och så att forskningens bedömningar av uppgiften — belagd, legendarisk,
omstridd — kan lagras sida vid sida.

## MCP-verktyg

Servern (`mcp_server.py`) läser bara ur den lokala databasen. Verktygen har
prefixet `fornmed_`.

| Verktyg | Gör |
|---|---|
| `fornmed_sok` | Hybrid-, fulltext- eller semantisk sökning i regester och originaltexter, med termexpansion och filter på datering och genre |
| `fornmed_begrepp` | Ett medeltida begrepp med definition, termer per språk, relationer och ordboksartiklar |
| `fornmed_ordbok` | Uppslag i Schlyter och Söderwall med normaliserad stavning |
| `fornmed_hamta_verk` | Ett verk med vittnen, utgåvor, passager och bedömningar |
| `fornmed_hamta_passage` | En passages text (regest, originaltext, översättning), med fortsatt läsning för långa texter |
| `fornmed_sok_entitet` | Personer, folk, platser, ämbeten m.m. på namn eller namnform |
| `fornmed_hamta_entitet` | En entitet med identifieringar, bedömningar och påståenden (sammanfattning per predikat, påståendena sidvis) |
| `fornmed_hamta_pastaende` | Ett påstående med källa, tidsavstånd, relationer och bedömningar |
| `fornmed_omstridda` | Var bedömningarna går isär och konkurrerande identifieringar |
| `fornmed_vokabular` | Klassificeringsvärden för genre, historicitet, äkthet m.m. |
| `fornmed_oversikt` | Antal poster och källsamlingar med licens |

Serverns instruktioner till klienten säger hur svaren ska läsas
källkritiskt: ett påstående är vad en källa hävdar, beroende källor ger inte
oberoende stöd, oeniga bedömningar redovisas var för sig och ogranskade
bedömningar presenteras som ogranskade.

Lägg till servern i MCP-klientens konfiguration enligt
`claude_desktop_config.example.json`. Servern läser `.env` i projektmappen.
Transporten väljs med `MCP_TRANSPORT`: `stdio` för en lokal klient, `http`
för delad drift. http-läget kräver antingen `MCP_API_KEY` eller öppet läsläge
(`MCP_OPPEN_LASNING=på`); utan något av dem startar servern inte. Bakom en
reverse proxy anges de publika värdnamnen i `MCP_TILLATNA_VARDAR`.

## API

`api.py` är ett REST-API med samma innehåll som MCP-verktygen och några
resurser till: hela dokument, delar och språkversioner. Beskrivningen finns
under `/openapi.json` och dokumentationen under `/docs`.

```bash
.venv/bin/python tjanst.py          # API på /, MCP på /mcp, port 8424
.venv/bin/uvicorn api:app --port 8424   # bara API:et
```

`tjanst.py` kör API:et och MCP-servern i samma process, så att
embeddingmodellerna laddas en gång. MCP-delen följer samma åtkomstregler som
ovan; API:et är alltid öppet.

| Resurs | Innehåll |
|---|---|
| `/v1/oversikt`, `/v1/kallsamlingar` | Antal poster och källsamlingar med licens |
| `/v1/verk` | Verk med filter på källsamling, genre, språk, datering, titel och plats |
| `/v1/verk/{id}` | Ett verk med vittnen, utgåvor, passager (utan text) och bedömningar |
| `/v1/verk/{id}/versioner` | Språkversionerna |
| `/v1/verk/{id}/text` | Hela verket i ett svar, eller ett avsnitt med `fran` och `till` |
| `/v1/verk/{id}/delar`, `/v1/verk/{id}/delar/{del}/text` | Delarna och en del i ett svar |
| `/v1/verk/{id}/utgavor`, `/v1/utgavor/{id}` | Utgåvorna, också tryck utan text i databasen |
| `/v1/passager/{id}` | En passage med hela texten |
| `/v1/sdhk/{nummer}` | Genväg till ett brev (omdirigerar till verket) |
| `/v1/sok` | Sökning, som `fornmed_sok` |
| `/v1/entiteter`, `/v1/entiteter/{id}` | Sökning på namn och en entitet med påståenden |
| `/v1/entiteter/{id}/namnformer`, `/v1/entiteter/{id}/identifieringar` | Namnformerna i källorna och identifieringarna med bedömningar |
| `/v1/pastaenden`, `/v1/pastaenden/{id}` | Påståenden med filter på entitet, predikat, verk, källsamling, extraktion, granskning och år, och ett påstående |
| `/v1/bedomningar`, `/v1/omstridda` | Bedömningar med filter, och var de går isär |
| `/v1/auktoriteter`, `/v1/auktoriteter/{langd}`, `/v1/auktoriteter/{langd}/{person}` | Regent-, biskops- och påvelängderna, med filter på titel, säte och år |
| `/v1/leveranser`, `/v1/leveranser/{id}` | Databasens uppdateringar med vad som ändrats |
| `/v1/vokabularer`, `/v1/begrepp/{term}`, `/v1/ordbok` | Vokabulär, begreppsregister och ordböcker |
| `/halsa` | Kontroll av att tjänsten och databasen svarar |

**Format.** Alla resurser finns som JSON (standard), Markdown och text, och
listor även som CSV. Formatet väljs med `format=json|md|txt|csv` eller med
Accept-huvudet. Ett format som inte finns för resursen, som CSV för ett
dokument, ger 406 med de format som finns. Listor pagineras med `sida` och
`per_sida`; i CSV står totalen i `X-Total` och nästa sida i `Link`.

**Språk.** `sprak=` väljer språkversion med ISO 639-3-koder i
prioritetsordning: `sprak=swe,dan,lat` ger svenska om den finns, annars
danska, annars latin. Utan `sprak` blir det originalspråket. `utgava=` väljer
en bestämd utgåva och `roll=skolier` Adam av Bremens skolier.
`sprak=fsv,swe&parallellt=true` ger texterna passage för passage.

**Källhänvisning.** Markdown och text inleds med verk, utgåva, språk, typ och
licens. Maskinöversättningar och maskintranskriptioner har dessutom en rad om
att texten är ogranskad, också när en enskild passage hämtas.

En utgåva över tio miljoner tecken skickas inte hel utan ger 413 med verkets
delar. Den största i dag är Olaus Magnus med 2,1 miljoner.

### Drift på server

`deploy/` innehåller installationen på en Ubuntu-server: Postgres 16 med
pgvector, söktjänsten (API och MCP) som systemd-tjänst, webbplatsen, Umami,
nginx med certifikat för domänen och dess underdomäner www, api, mcp och
stat, statistik med GoAccess och en hälsokontroll med larm via
Healthchecks.io. Stegen står i `deploy/DRIFTPLAN.md`.

```bash
cp deploy/server.example.env deploy/server.env          # ange domänen
deploy/skicka_kod.sh --bara-kod                       # koden till servern
ssh fornmed sudo bash /srv/fornmed/fornmed/deploy/installera_server.sh --epost <ADRESS> --admin-ip <ADRESS>
deploy/skicka_databas.sh "Första leveransen"          # databasen till servern
```

### Webbplatsen

`webb/` är webbplatsen fornmed.se, byggd med Django och Wagtail. Källförteckningen
och uppdateringarna läses ur Fornmeds databas; sidornas texter ligger i
webbplatsens egen databas och redigeras i Wagtail.

```bash
cd webb
cat > .env <<'ENV'
WEBB_DEBUG=på
WEBB_DATABASE_URL=postgresql://<ANVÄNDARE>@localhost:5432/fornmed_webb
FORNMED_DATABASE_URL=postgresql://<ANVÄNDARE>@localhost:5432/fornmed
ENV
python manage.py migrate
python manage.py skapa_sidor
python manage.py runserver 127.0.0.1:8425
```

### Auktoriteter och leveranser

```bash
.venv/bin/python auktoriteter.py
.venv/bin/python leverans.py --anmarkning "Erikskrönikan tillagd" --fil fornmed.pgdump
```

`auktoriteter.py` läser in längderna i `data/auktoriteter` i tabellerna
`auktoritetslangd`, `auktoritet` och `auktoritet_titel`, så att de följer med
databaskopian. Personerna har samma id som sina entiteter. Biskopslängden har
svenska Wikipedias licens (CC BY-SA 4.0), som anges i svaren.

`leverans.py` körs när databasen ska till servern. Det räknar rader per tabell
och verk per källsamling, skriver en rad i `leverans` med skillnaden mot förra
leveransen och gör sedan kopian med `pg_dump`, så att raden följer med.
Webbplatsens lista över uppdateringar bygger på den. `--bara-registrera`
skriver raden utan att göra någon kopia.

## Datamodell

Källor beskrivs i fyra nivåer så att händelsens, textens och handskriftens
datering hålls isär:

| Tabell | Innehåll | Exempel |
|---|---|---|
| `verk` | Texten som intellektuell enhet | SDHK 1000, Beowulf, Västgötalagen |
| `vittne` | Fysisk eller registrerad överlevnad | Original, medeltida avskrift, registratur |
| `utgava` | Tryckt eller digital utgåva | DS 611 |
| `passage` | Citerbar textenhet | Regest, originaltext, översättning |

Ovanpå källorna:

| Tabell | Innehåll |
|---|---|
| `entitet`, `entitet_namnform` | Personer, platser, institutioner, indelningar, ämbeten, händelser, begrepp |
| `pastaende` | Vad en passage *hävdar*: subjekt – predikat – objekt, tid och plats, med proveniens (manuell, regel, språkmodell) och granskningsstatus |
| `pastaende_relation` | Påståenden som stöder, motsäger eller är beroende av varandra |
| `identifiering` | Att två entiteter är samma (Beowulfs Hygelac = Gregorius Chlochilaicus); alternativ som utesluter varandra delar `alternativgrupp` |
| `bedomning` | En forskares eller publikations omdöme om ett påstående, verk, vittne eller en identifiering — flera per mål, med granskningsstatus |
| `vokabular` | Kontrollerade värden för genre, historicitet, äkthet, korroboration, predikat m.m. (definieras i `vokabular.py`) |

Vyer:

- `pastaende_oversikt` — varje påstående med källans genre, minsta möjliga
  tidsavstånd mellan påstådd händelse och källans tillkomst, antal
  bedömningar och om bedömningarna av historiciteten går isär.
- `omstridda` — påståenden, verk, vittnen och identifieringar där minst två
  bedömningar ger olika värden inom samma aspekt.
- `konkurrerande_identifieringar` — entiteter där flera uteslutande
  identifieringar har bedömts som säkra eller sannolika av olika forskare.

### Språkversioner och delar

Varje språkversion av ett verk är en egen utgåva. `utgava` anger språk
(ISO 639-3), typ (`original`, `oversattning`, `maskinoversattning`,
`maskintranskription`), roll (`huvudtext`, `skolier`) samt översättare och
år för tryckta översättningar. Runinskrifternas utgåvor har flera språk i
samma utgåva och får inget eget språk; där gäller passagens.

Passager i verk med indelning får `del` och `del_typ`: bok, balk, del av en
annalserie, saga eller namngivet avsnitt. Det gäller i dag 33 verk, bland
dem landskapslagarna, Saxo, Olaus Magnus, Adam av Bremen och
kungasagesamlingarna. Böcker skrivs med romerska siffror, så att Olaus
Magnus "Liber Septimus" och "Liber XIIII" blir `bok VII` och `bok XIV`.
Verk med bara en del får ingen.

Fälten härleds ur passagernas språk och adresser och utgåvans referens.
Kör efter varje import:

```bash
.venv/bin/python struktur.py
```

Körningen skriver bara ändrade värden och kan köras hur många gånger som
helst.

Datering lagras som EDTF (`1276-05-23`, `1396`, `1373~`, `1375/1378?`) plus
ett heltalsintervall `ÅÅÅÅMMDD` för sökning. Datumen återges som i källan
(julianska) och konverteras inte.

## Installation

PostgreSQL-servern behöver tillägget pgvector.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.env .env   # välj PostgreSQL eller SQLite i DATABASE_URL
```

## Import av SDHK

```bash
.venv/bin/python importera_sdhk.py
```

Skriptet hämtar Riksarkivets SDHK-fil (CC BY 4.0) till `data/raw/sdhk/`,
skapar schemat och importerar. Importen är idempotent och kan köras om mot en
ny ögonblicksbild. Råposterna sparas oförändrade i `sdhk_brev`; ur dem byggs:

- ett `verk` per brev (genre `diplom`) med datering, språk och utfärdandeort,
- `vittne` för original, avskrifter, registraturer, fotokopior och faksimil,
- `utgava` för tryckreferenser,
- `passage` för regesten (modern svenska) och, där den finns, editionstexten,
- en `bedomning` av äktheten för brev där SDHK:s anmärkningar nämner
  förfalskning (värdet sätts till `misstankt`).

Fulltextsökning: PostgreSQL indexerar regester både med och utan svensk
stemming, och originaltext utan; SQLite använder FTS5 (`passage_fts`).
Begreppsregistrets termer söks utan stemming när stemmingen skulle slå
ihop dem med vardagsord (fastar → fast).

## Semantisk sökning

```bash
.venv/bin/python berakna_embeddings.py
.venv/bin/python sok.py "kungen befriar ett kloster från skatt"
```

`berakna_embeddings.py` delar passagerna i chunkar (`chunk`) och beräknar
vektorer (`embedding`) med två modeller:

| Modell | Variabel | Passager |
|---|---|---|
| KBLab/sentence-bert-swedish-cased | `EMBEDDING_MODELL` | regester och översättningar på modern svenska |
| intfloat/multilingual-e5-base | `EMBEDDING_MODELL_FLERSPRAK` | översättningar till andra moderna språk (Winkel Horns danska Saxo, engelska översättningar av de romerska källorna och runinskrifterna) samt latinet i Adam av Bremen med skolier, Gregorius, Jordanes, Liber historiae Francorum, Vita Anskarii, Germania, Plinius och Mela |

Varje passage embeddas med en modell. Vektorer från olika modeller går inte
att jämföra, så varje modell har ett eget partiellt HNSW-index
(`db.skapa_vektorindex`), och sökningen embeddar frågan med båda modellerna,
söker i var sitt index och väger samman listorna på placering. Den
flerspråkiga modellen gör att en svensk fråga träffar Saxos danska text och
de latinska krönikorna ("danerna under kung Chlochilaicus anfaller Gallien"
ger Gregorius 3.3).

Övriga originaltexter embeddas inte: SDHK-originalen, runtranslitterationer
och normaliseringar, Saxos latin, grekiska, arabiska och fornspråken. När de
låg i samma index som krönikorna hamnade det formelartade brevlatinet och
translitterationerna nära nästan varje fråga och trängde undan riktiga
träffar. Av samma skäl embeddas inte Rundatas engelska översättningar av
fragment (färre än 40 bokstäver) eller futharkrader. Verken hittas i stället
via sin regest eller översättning, och originalen med fulltext och
begreppsregistrets termexpansion. Körningen är inkrementell och kan köras om
efter varje import (`--modell flersprak` kör bara den ena modellen); vid
byte av modell räknas den modellens vektorer om.

Regester med färre än fem ord och SDHK:s platshållare ("Utgått. = SDHK nr …",
"Dubbelregistrering") embeddas inte. Deras vektorer ligger nära nästan alla
frågor och tränger undan riktiga träffar; de är fortfarande sökbara med
fulltext.

Vektorerna lagras med pgvector (HNSW-index) i PostgreSQL och med sqlite-vec
i SQLite.

`sok.py` har tre sökmetoder:

| Metod | Hittar |
|---|---|
| `fts` | Regester som innehåller frågans ord |
| `vektor` | Regester som handlar om samma sak, även med andra ord |
| `hybrid` | Båda, sammanvägda med reciprocal rank fusion (standard) |

Hybridsökningen väger samman placeringarna i stället för poängen, eftersom
fulltextrankning och cosinuslikhet ligger på olika skalor. Utskriften visar
varje träffs placering i fulltexten och i vektorsökningen.

Fulltexten rankas efter hur sällsynta de träffade orden är. Varje frågeord
som inte expanderats är en grupp, och varje begrepp eller namn ur registret
med alla sina termer en; en passage får summan av gruppernas IDF, räknad som
i bm25. Utan det (Postgres `ts_rank_cd` väger alla termer lika) gick en
passage som nämner kung och ö före en som nämner Starkad. SQLite-backenden
använder bm25 och gör samma sak.

`utvardera_sok.py` mäter sökningen mot 30 frågor med kända svar, både i
originaltexterna och bland breven. Kör det före och efter en ändring i
sökningen eller registret.

När originaltexterna söks (`--texttyper alla`) räknas en passages bästa
placering fullt och placeringarna i övriga listor med halv vikt
(`RRF_OVRIGA_VIKT`). Med vanlig RRF, där placeringarna summeras, vinner en
passage som syns måttligt högt i två listor över en som står överst i en
enda. Det missgynnar texter som bara kan träffas på ett sätt: ett latinskt
kapitel matchar inte en svensk fråga i fulltexten och har ingen svensk
vektor. I en provuppsättning med 22 frågor med kända svar gav halv vikt en
relevant träff bland de tio första för 16 frågor mot 13 (före IDF-rankningen). Bland regester och
moderna översättningar ger den inte fler relevanta träffar men släpper in
mer brus, så där summeras placeringarna som vanligt. Ett eget index för
latinet prövades också men gav sämre resultat än ett gemensamt för den
flerspråkiga modellen.

Vektorsökningen är stark på omskrivningar ("en änka skänker jord för sin
mans själ" hittar "hustru … ger sin gård … för sin själ") men svag på
enstaka historiska fackord som *ledung* eller *frälse*, som modellen inte
känner. För sådana frågor är det fulltextträffarna som bär.

## Litterära källor och lagar

Varje källa har en tolk i `tolkar/` som läser källans format och lämnar ett
källpaket (`kallpaket.py`): verk, utgåvor med licens och passager med
citerbara adresser i källans egen indelning. Laddningen är idempotent.

En tolk äger sina utgåvor. Vid ny inläsning tas passager som utgåvan inte
längre innehåller bort, till exempel när en rättad tolk delar upp ett kapitel
annorlunda. En inaktuell passage som påståenden bygger på tas inte bort utan
loggas som varning, eftersom påståendena annars skulle försvinna med den;
sådana passager får flyttas eller tas bort för hand.

```bash
.venv/bin/python -m tolkar.beowulf
.venv/bin/python -m tolkar.openmgh
.venv/bin/python -m tolkar.adam_skolier
.venv/bin/python -m tolkar.adam_skolier_lappenberg
.venv/bin/python -m tolkar.heimskringla_no
.venv/bin/python -m tolkar.ynglingatal
.venv/bin/python -m tolkar.wikisource
.venv/bin/python -m tolkar.romerska
.venv/bin/python -m tolkar.eddan
.venv/bin/python -m tolkar.snorres_edda
.venv/bin/python -m tolkar.saxo
.venv/bin/python -m tolkar.arabiska
.venv/bin/python -m tolkar.liber_monstrorum
.venv/bin/python -m tolkar.fornsvenska_lagar
.venv/bin/python -m tolkar.fornsvenska_kronikor
.venv/bin/python -m tolkar.sagor_heimskringla
.venv/bin/python -m tolkar.storm_mhn
.venv/bin/python -m tolkar.ottar_wulfstan
.venv/bin/python -m tolkar.olaus_magnus
.venv/bin/python berakna_embeddings.py
```

| Tolk | Innehåll | Källa och licens | Passager |
|---|---|---|---|
| `beowulf` | Beowulf (fornengelska) med Wickbergs svenska översättning; Finnsburgfragmentet | Harrison & Sharp 1894 (Project Gutenberg, PD); Wickberg 1914 (sv.wikisource, PD, transkription CC BY-SA 4.0) | per fitt, adress med Harrison & Sharps radnumrering |
| `openmgh` | Adam av Bremen, Vita Anskarii, Jordanes Getica, Gregorius av Tours, Liber historiae Francorum; frankiska annaler (Annales regni Francorum, Bertiniani, Fuldenses, Xantenses, Vedastini); Einhards Vita Karoli, Thegan och Astronomus om Ludvig den fromme; Widukind, Thietmar av Merseburg, Helmold av Bosau, Henrik av Lettland, Paulus Diaconus (latin) | openMGH, CC BY 4.0; svenska: språkmodellsöversättning | per kapitel med MGH-sidor; annalerna per år; Getica och Helmold per MGH-sida |
| `adam_skolier` | Skolierna till Adam av Bremen (alla 158), som egna passager av typen `skolion` under Adams verk | Schmeidler 1917, OCR ur Internet Archive (PD); skolier som är ofullständiga eller saknas i OCR:en transkriberade från sidbild (`data/transkriptioner/`); svenska: språkmodellsöversättning | per skolion, med kapitlet det hör till och MGH-sida |
| `adam_skolier_lappenberg` | Lappenbergs text till de skolier som är ofullständiga i OCR:en av Schmeidler, som parallella passager | Lappenberg & Waitz 1876, OCR ur Internet Archive (PD); svenska: språkmodellsöversättning | per skolion i Lappenbergs numrering |
| `heimskringla_no` | Heimskringla: 16 sagor på fornvästnordiska och i svensk översättning | Linder & Haggson 1869–72 och Emil Olson 1919–26 (heimskringla.no, PD) | per kapitel i respektive utgåvas numrering |
| `ynglingatal` | Ynglingatal: de 27 citaten ur dikten i Ynglinga saga, på fornvästnordiska och i svensk översättning | Ur Linder & Haggsons och Olsons text på heimskringla.no (PD) | per citat, med kapitlet i båda utgåvorna |
| `wikisource` | Gutasagan; Gutalagen i Säves utgåva (som ny utgåva av textbankens Gutalag); Västgötalagens lagmans-, konungs- och biskopslängd; Hednalagen med Olavus Petris kommentar; svenska språkmodellsöversättningar av Gutasagan och Gutalagen | Säve 1859; Collin & Schlyter 1827; von Friesen 1902 (PD), transkriptioner på svenska Wikisource (CC BY-SA 4.0) | Gutasagan per kapitel; längderna en passage per lagman, kung och biskop |
| `romerska` | Tacitus Germania (hela); Plinius Naturalis historia, kapitlen om Norden; Pomponius Mela 3.25–33, 44–46; Prokopios Krigen 6.14–15 | Perseus Digital Library (CC BY-SA 4.0), The Latin Library; engelska Church & Brodribb 1876, Bostock & Riley 1855; svenska: språkmodellsöversättning | per kapitel; Plinius med paragrafnummer |
| `eddan` | Den poetiska Eddan, 39 kväden och prosastycken | Finnur Jónsson 1932 (fornisländska), Erik Brate 1913 (svenska), heimskringla.no (PD) | per kväde, stroferna numrerade |
| `snorres_edda` | Snorres Edda: Prologus, Gylfaginning, Skáldskaparmál, Skáldatal | Guðni Jónsson (fornisländska; upphovsrätt för normaliseringen), Cnattingius 1819 (svenska, PD), heimskringla.no | per kapitel i respektive utgåva |
| `saxo` | Saxo Grammaticus, Gesta Danorum, alla 16 böcker | Latinsk text på latinska Wikisource (efter Det Kongelige Biblioteks e-text); Winkel Horns danska översättning 1898 (heimskringla.no, PD) | latin per bok och kapitel med paragrafnummer; danska per Winkel Horns avsnitt |
| `arabiska` | Ibn Fadlans Risala (hela); avsnitt om rus, slaver och Norden ur Ibn Khurradadhbih, Ibn Rusta, al-Masʿudi, Ibn Hawqal, al-Idrisi och al-Qazwini (med al-Turtushi om Hedeby) | OpenITI (CC BY-NC-SA 4.0); svenska: språkmodellsöversättning | per avsnitt |
| `liber_monstrorum` | Liber monstrorum, tre böcker | Haupt 1863, OCR ur Internet Archive (PD); svenska: språkmodellsöversättning | per bok och kapitel i Haupts numrering |
| `fornsvenska_lagar` | Landskapslagarna, Magnus Erikssons lands- och stadslag, Kristoffers landslag m.fl. (32 texter) | Fornsvenska textbankens material, Språkbanken, CC BY 4.0; svenska: språkmodellsöversättning | per flock med hänvisning i formen "UL Äb 10"; fragment och inledningar per stycke |
| `fornsvenska_kronikor` | Erikskrönikan, Karlskrönikan, Konungastyrelsen, Prosaiska krönikan (början) | Fornsvenska textbankens material, Språkbanken, CC BY 4.0 | per sida i utgåvan |
| `storm_mhn` | Theodoricus monachus, Historia de antiquitate regum Norwagiensium; Historia Norwegie (latin) | Storm, Monumenta historica Norvegiæ 1880, OCR ur Internet Archive (två skanningar som rättar varandra; PD); svenska: språkmodellsöversättning | Theodoricus per kapitel, Historia Norwegie per rubrik, med Storms sidor |
| `ottar_wulfstan` | Ottars och Wulfstans berättelser och beskrivningen av Europas norra folk ur den fornengelska Orosius | Sweet 1885, OCR ur Internet Archive, rensad av språkmodell (ogranskad, `data/transkriptioner/`); svenska: språkmodellsöversättning | per stycke med Sweets sida och rader |
| `olaus_magnus` | Olaus Magnus, Historia de gentibus septentrionalibus (1555), alla 22 böcker | Project Runeberg efter Nasjonalbibliotekets skanning och OCR (PD); svenska: språkmodellsöversättning | per bok och kapitel med tryckets sidor |
| `sagor_heimskringla` | Islänningasagor och þættir (Íslendinga sögur), Íslendingabók, Landnámabók, Hervarar saga, Ágrip, Fagrskinna, Morkinskinna, Knýtlinga saga; Sven Aggesen och Grágás i dansk översättning | Guðni Jónsson m.fl. (heimskringla.no); sagor som saknas där ur Icelandic Saga Database (sagadb.org, modern isländsk stavning); äldre svenska, danska och engelska översättningar tryckta före 1931 (PD) | per kapitel; Fagrskinna, Morkinskinna, Landnámabók och Grágás per delsida och kapitel |

Begränsningar:

- Harrison & Sharps radnumrering avviker upp till två rader från
  standardnumreringen (Klaeber) mot slutet av Beowulf. Wickberg utelämnar
  skadade rader, och vid fittgränserna kan en rad hamna förskjuten.
- openMGH-texterna är OCR utan märkt kapitelindelning; kapitlen tas fram ur
  radinledande nummer. Där OCR:en tappat flera nummer i följd blir ett
  kapitel för stort; för Gregorius fylls luckorna med hjälp av The Latin Library.
- Adams skolier står inte i openMGH-texten och hämtas ur OCR:en av
  Schmeidlers tryck. Kapitlet ett skolion hör till bestäms genom att ankarets
  rad i marginalen söks upp i huvudtexten. Skolion 88, 144 och 149 saknar
  läsbar rubrik i OCR:en. Skolier som är ofullständiga eller saknas i OCR:en
  har transkriberats av en språkmodell från utgåvans sidbilder; de ligger i en
  egen utgåvepost och adressen anger "transkriberat från sidbild, ogranskat".
  En transkription används bara om dess början stämmer med OCR:en, eller om
  OCR:en bevisligen läst fel stycke. Skolion 102 och 152 är fragment redan i
  handskriften (A 2 resp. A). Lappenbergs OCR är av låg kvalitet och duger
  som jämförelse, inte som citat.
- Annalerna delas per år efter årtalen i utgåvan ("861.", "Anno Domini 865.",
  "DCCXV."). Åren tas som den längsta följden av stigande årtal, så att tal i
  noterna inte bryter indelningen; år som OCR:en förvanskat hamnar i
  föregående års passage. Det sena supplementet till Annales Xantenses
  (640–789) tas inte med. Helmolds OCR-text saknar kapitelrubriker och delas
  per MGH-sida. Holtzmanns Thietmarutgåva trycker Dresdenhandskriften och
  Corveybearbetningen på motstående sidor, och OCR:en följer sidorna; där båda
  versionerna finns innehåller en passage därför samma stycke två gånger, i
  de två versionerna. De skiljs inte ut. Annales regni Francorum trycks på
  samma sätt med Annales Laurissenses och den bearbetade versionen
  (Einhardsannalerna) parallellt, och passagerna blandar de två.
- Islänningasagorna står i Guðni Jónssons normaliserade utgåva, som inte är
  fri i strikt mening (Guðni Jónsson dog 1974); heimskringla.no publicerar den
  som public domain. Sagor som saknas på heimskringla.no tas ur sagadb.org i
  modern isländsk stavning. En översättning tas med bara om titelsidan anger
  ett tryckår före 1931 och inget copyrighttecken; svenska går före danska
  och engelska. Femton þættir finns i ingen av källorna.
- Theodoricus och Historia Norwegie är OCR av Storms tryck; ord byts mot den
  andra skanningens form bara när den förekommer på annat ställe i texten.
  Ordfel finns kvar, särskilt i Historia Norwegie, och Storms tecken för
  lakuner har fallit bort. Historia Norwegies sista avsnitt (De ortu regum,
  s. 97–124) saknar rubriker och är en enda lång passage.
- Olaus Magnus står i Runebergs OCR-text, delvis korrekturläst; tryckets
  marginalanteckningar ligger inne i raderna. Kapitelgränserna är
  ofullkomliga: en tvåradig kapitelrubrik kan delas mellan två passager,
  några kapitel vars "CAP."-rad OCR:en tappat eller förvanskat ligger i
  föregående kapitels passage (t.ex. bok IX kap. 46), och passagen för bok
  XI kap. 42 har fått id-numret 52 efter OCR:ens "LII". Gränserna ändras inte,
  eftersom översättningarna följer dem. Den svenska översättningen
  1909–25 (Michaelisgillet) tas inte med: översättaren anges inte och
  texten finns bara som sidbilder.
- Hakluyts engelska översättning av Ottar och Wulfstan (1889) saknas i
  Internet Archives skanning och tas inte med.
- Grágás och Sven Aggesen finns på heimskringla.no bara i dansk översättning
  (Finsen 1870, Olrik 1900–01). Finsens fornisländska utgåva (1852) finns som
  OCR på Internet Archive men med förvanskade þ och ð.
- Linder & Haggson och Olson delar sagorna i kapitel på olika sätt (Aðils
  död är kap. 33 hos Linder & Haggson och kap. 29 hos Olson); original och
  översättning paras därför inte ihop kapitel för kapitel.
- Västgötalagens längder står också i Fornsvenska textbankens "Vidhemsprästens
  anteckningar", men där som en enda lång passage. Tolken `wikisource` delar
  dem per lagman, kung och biskop efter Collin & Schlyters utgåva och numrerar
  efter handskriftens egna ordningstal; konungalängden hoppar över den
  fjortonde kungen. Hednalagen finns bara i eftermedeltida avskrifter.
- De romerska källorna saknar fria svenska översättningar. De svenska
  texterna är gjorda av en språkmodell från latinet och grekiskan
  (`data/oversattningar/romerska_sv.json`), ligger i en egen utgåva och är
  märkta som ogranskade maskinöversättningar; citera originalet eller en
  tryckt översättning. Mayhoffs Plinius har den textkritiska apparaten
  inbäddad i Perseus fil; den tas bort, och enstaka rester kan finnas kvar.
- Saxo saknar fri svensk översättning; Winkel Horns danska översättning
  söks med fulltext och embeddas med den flerspråkiga modellen.
- De arabiska texterna och Liber monstrorum har svenska översättningar gjorda
  av en språkmodell (`data/oversattningar/`), märkta som ogranskade. OpenITI:s
  licens är CC BY-NC-SA, vilket bara tillåter icke-kommersiellt bruk.
- Gregorius av Tours: kapitel som OCR:en tappat numret på letas upp med
  hjälp av The Latin Librarys kapitelindelning (kapitlets första ord söks i
  texten); 434 av 442 kapitel hittas.
- Finnur Jónssons danska kommentarer till Eddakvädena tas bort; en kort dansk
  inledningsmening kan undantagsvis stå kvar.
- Ynglingatal finns bara som Snorres citat. Tolken tar citat som inleds med
  Þjóðólfr som skald och parar originalets och översättningens citat i
  ordning; ett citat kan omfatta flera strofer, och numreringen följer
  citaten, inte någon utgåva av skaldediktningen.
- Lagkorpusen märker inte balk och flock. Indelningen tolkas ur rubriker och
  nummer i handskriften (se `tolkar/fornsvenska_lagar.py`). Antalet flockar
  per balk stämmer med handskrifternas egna angivelser ("tæliæs i hanum
  flokkær XXI") för bl.a. Södermannalagen, Östgötalagen och Hälsingelagen,
  och stickprov mot Schlyters utgåva (Äldre Västgötalagen, Hälsingelagen)
  ger samma flockar. Upplandslagen B saknar nummer och delas efter
  Upplandslagen A genom ordlikhet. Östgötalagens fragment, Gutalagens
  additament och stadsfästelsen saknar flockindelning.
- Hänvisningen inleds med lagens gängse förkortning (UL, SdmL, ÄVgL, MEL …).
  Balkförkortningarna (Kkb, Kgb, Äb …) är enhetliga inom databasen men
  följer ingen enskild tryckt förteckning; för Magnus Erikssons och
  Kristoffers lagar används textbankens egen form (KgB, ÄB, TgB …). Den
  fullständiga balkrubriken står kvar i adressen.
- Originaltexter söks med `texttyper="alla"`. Utom de latinska krönikorna
  är de inte embeddade (se Semantisk sökning), så där bär fulltexten och
  begreppsregistrets termexpansion.

## Maskinöversättningar

Texter som saknar fri svensk översättning har fått en översättning gjord av
en språkmodell (Claude) direkt från originalspråket: alla landskaps- och
stadslagar i Fornsvenska textbanken (också Kristoffers landslags flockar ur
Magnus Erikssons landslag, Upplandslagen B och textbankens Gutalag),
Västgötalagens längder, Hednalagen, Vǫluspá hin skamma, Finnsburgfragmentet,
alla openMGH-texter (Gregorius av Tours, Adam av Bremen, Jordanes, Vita
Anskarii, Liber historiae Francorum, de frankiska annalerna, Einhard, Thegan,
Astronomus, Widukind, Thietmar, Helmold, Henrik av Lettland och Paulus
Diaconus) och alla 168 skolier till Adam, Theodoricus monachus, Historia
Norwegie, Olaus Magnus Historia de gentibus septentrionalibus, de
romerska och arabiska källorna, Gutasagan, Säves Gutalag och Liber
monstrorum, de fornsvenska krönikorna (Erikskrönikan, Karlskrönikan,
Konungastyrelsen, Prosaiska krönikan) samt de islänningasagor, þættir och
kungakrönikor som saknar fri äldre översättning (bland andra Fagrskinna,
Morkinskinna, Landnámabók, Vatnsdæla, Ljósvetninga och Svarfdæla saga; 63
verk). Rimkrönikorna är översatta rad för rad, skaldestroferna strof för
strof med kenningarna ordagrant. Där utgåvan blandar två versioner
(Thietmar, Annales regni Francorum) är allt översatt i den ordning det står,
också ord som bryts vid versionsskiftet; Olaus Magnus marginalanteckningar
står som [I marginalen: …]. Utgivarnas fotnoter och textkritiska apparat är
inte översatta. Ottars och Wulfstans berättelser är översatta
från fornengelskan.

Översättningarna ligger som JSON i `data/oversattningar/` (nyckel:
originalpassagens id) och laddas av respektive tolk med
`Kallpaket.lagg_till_maskinoversattningar`. Varje översättning blir en
passage `<id>:sv` i en egen utgåva `<utgåva>:sv_modell`, märkt som ogranskad,
och får samma underlagslänk som originalet. De får aldrig citeras som
översättning; citera originalet.

Instruktionerna till modellen står i `data/oversattningar/RIKTLINJER.md`:
trogen och fullständig översättning, centrala fackord med originalordet
inom parentes, osäkra ställen markerade `[osäker tolkning]` eller `[oklart]`,
inga egna tillägg, och en regel för egennamn (städer, länder och större
floder i nutida eller vedertagen svensk form; byar, gods, borgar, områden och
folk i textens form, aldrig som moderna identifieringar). De äldre
översättningarna (romerska, arabiska, Gutasagan, Säves Gutalag, Liber
monstrorum) gjordes innan riktlinjerna skrevs och saknar markeringar för
osäkra ställen.

Sagorna ur sagadb.org står i modern isländsk stavning, och deras
översättningar har ofta namnen i textens form (Guðmundur), medan
heimskringla.no-texternas har den normaliserade fornvästnordiska (Guðmundr).
Fagrskinnas sidor på heimskringla.no upprepar texten med utgivarens fotnoter;
tolken tar bara med den första versionen.

Varje fil har kontrollerats mot originalen: rätt id-mängd, ingen tom
översättning, rimlig längdkvot, och att varje översättning liknar sitt eget
original mer än filens övriga (teckenbaserad jämförelse; svagare för latin
än för fornsvenska). Egennamnen i Gregorius och Adam har samordnats så att
samma latinska namn återges likadant i hela verket.

Med översättningarna hittar standardsökningen lagarna: i `utvardera_sok.py`
gav de åtta lagfrågorna ingen lagpassage bland de tio första före
översättningarna och en relevant träff för alla åtta efter (MRR 0,875).

## Runinskrifter

```bash
.venv/bin/python -m tolkar.runor
.venv/bin/python berakna_embeddings.py
```

Tolken läser Rundata.info, Stockholms universitets uppdaterade version av
Samnordisk runtextdatabas, som en SQLite-fil (hämtas automatiskt). Varje
inskrift blir ett verk med fyndort, socken, härad, datering, ristare, stil,
material och koordinater (i verkets `extra`), och upp till fem passager:
translitterering, normalisering till fornvästnordiska och till runsvenska,
svensk och engelsk översättning. 6 815 inskrifter; drygt hälften har svensk
översättning, och bara den embeddas.

Licensen är Open Database License 1.0 (innehållet Database Contents License
1.0) med Uppsala runforums tilläggsvillkor:

- databasen ska anges med namn och länk varje gång uppgifter ur den visas;
  hänvisningen står i varje inskrifts utgåva,
- en ändrad version får inte kallas Samnordisk runtextdatabas,
- Uppsala runforum ska meddelas när databasen används i en annan tillämpning.

## Ordböcker och begreppsregister

```bash
.venv/bin/python importera_ordbocker.py
.venv/bin/python begreppsregister.py
.venv/bin/python begreppsregister.py --kandidater 50
```

`importera_ordbocker.py` läser in tre ordböcker ur Språkbankens LMF-filer
(CC BY 4.0), en rad per betydelse i `ordboksartikel`:

| Ordbok | Betydelser | Anmärkning |
|---|---|---|
| Schlyter, *Ordbok till Samlingen af Sweriges gamla lagar* (1877) | 13 047 | Lagspråkets ord |
| Söderwall, *Ordbok öfver svenska medeltids-språket* (1884–1918) | 34 407 | Saknar uppslagsord på ä |
| Söderwall, *Supplement* (1925–1973) | 21 802 | Saknar uppslagsord på v |

Söderwall definierar inte lagspråkets ord utan skriver "L." och hänvisar
till Schlyter; uppslaget tar då med Schlyters artikel. Luckorna i
Söderwallfilerna är iakttagna i Språkbankens digitalisering och inte
jämförda med de tryckta utgåvorna.

`begreppsregister.py` bygger ett register över medeltida samhälls-, rätts-
och förvaltningsbegrepp (ledung, frälse, härad, hundare, lagman, fogde,
tionde …) som entiteter av typen `begrepp`, med:

- `term` — termformer per språk: modern svenska, fornsvenska (uppslagsord
  och stavningsvarianter ur ordböckerna), fornvästnordiska och latin,
- `begreppsrelation` — bredare och relaterade begrepp (SKOS),
- kopplingar till ordböckernas artiklar.

Definitionerna och de manuellt angivna termerna är ett utkast och
registreras som ogranskade. `--kandidater` listar ord som är vanliga i
SDHK:s regester och är uppslagsord hos Schlyter men saknas i registret.

Registret har också platser, folk och personer med deras namnformer i
källorna (Uppsala – Ubsola – Uppsalir, Starkad – Starcatherus – Stærkodder).
Bara stavningsvarianter av samma namn tas med; identifieringar som
forskningen diskuterar (Hygelac = Chlochilaicus) hör till
identifieringstabellen med bedömningar och expanderas inte.

Sökningen använder registret automatiskt: ett frågeord i valfri böjning
(lagmannen, häradet) som är en term för ett begrepp eller ett namn
expanderas med alla dess termer, och vektorsökningen får begreppets
definition som stöd. Med `--texttyper alla` söks även originaltexterna på latin och
fornsvenska. Medeltida stavning matchas genom en lös normalisering
(`normalisering.py`): þ, dh, gh, æ, w och dubbelteckning, så att härad,
häradh och hæraþ ger samma träff. Latinska termer söks på stammen, vilket
ger brus där stammen också är ett annat ord (decim* träffar även
ordningstalet decimus).

## Påståenden ur SDHK:s utfärdarfält

```bash
.venv/bin/python pastaenden_sdhk.py                 # läs in
.venv/bin/python pastaenden_sdhk.py --torr --rapport rapport/   # bara stickprov och otolkade fält
```

SDHK anger för de flesta brev vem som utfärdade dem, t.ex. "Biskop Knut i
Linköping" eller "Peter i Skeda, häradshövding i Hanekinds härad". Skriptet
tolkar fältet med regler och skapar tre slags påståenden, daterade med brevets
datum och knutna till brevets regest:

- `utfardar` — utfärdaren utfärdar brevet (`objekt_varde` är verkets id),
- `innehar_ambete` — titel eller ämbete, med ämbetets säte när det anges,
- `har_stand` — riddare eller väpnare.

Varje titel och ämbete är en entitet (`begrepp:kung`, `begrepp:abbot` …), så
att påståenden ur olika källor om samma ämbete går att länka. Ämbeten som
begreppsregistret saknar skapas utan termer.

Vem ett namn avser avgörs i fyra nivåer:

1. Regenter, regentinnor, hertigar, riksföreståndare och påvar slås upp i
   `data/auktoriteter/regenter.json` och `pavar.json`, som anger åren för
   varje titel och personens levnadsår. Kandidaterna är de som någon gång bar
   titeln och har förnamnet; ordningstal och furstendöme i fältet måste stämma
   ("Påven Gregorius IX", "Hertig Albrecht av Bayern"), och tillnamn avgör
   mellan kandidater ("Kung Magnus Eriksson"). Brevets datering ger sedan
   varje kandidat en grund, från den starkaste till den svagaste:

   | grund | betydelse |
   |---|---|
   | `under_titeln` | bar titeln vid dateringen |
   | `fore_titeln` | levde men hade ännu inte titeln, t.ex. Kristian II som utvald tronföljare 1488 |
   | `efter_titeln` | levde men hade förlorat eller lämnat titeln, t.ex. Albrekt av Mecklenburg som kung 1395 |
   | `efter_dodsfall` | omnämnd med titeln efter sin död |
   | `fore_fodelse` | dateringen eller identifieringen är fel |

   Har bara en kandidat den starkaste grunden kopplas utfärdaren direkt till
   personen. Är grunden en annan än `under_titeln` får titelpåståendet en
   bedömning med aspekten `titulatur` och grunden som värde, så att brevet
   räknas till personen men titeln märks som icke samtida. Utan någon levande
   kandidat räcker inte titel och förnamn: då krävs ordningstal eller tillnamn.
   När identiteten är oklar — flera kandidater med samma grund ("Kung Knut"
   1184: Knut Eriksson eller Knut VI) eller en ensam kandidat som inte levde —
   får utfärdaren en egen entitet för just det brevet, med kandidaterna som
   identifieringar i samma alternativgrupp, grunden som kommentar och
   bedömningen `mojlig`. Utfärdare som inte finns i listorna, mest utländska
   furstar, får också en egen entitet per brev.
2. Biskopar och ärkebiskopar i Uppsala, Linköping, Skara, Strängnäs,
   Västerås, Växjö, Åbo och Lund slås upp i `data/auktoriteter/biskopar.json`
   på samma sätt, med sätet i rikets ställe och samma grunder och etiketter.
   Breven skriver oftast svenska namnformer och listan blandar svenska och
   latinska, så namn som Nils och Nicolaus, Kort och Conradus, Lydeke och
   Ludechinus räknas som samma. Biskopar på andra säten klustras som andra
   personer.
3. Stadsråd, kloster, domkapitel och riksråd blir en institution per ort.
4. Övriga personer slås ihop när förnamnet är detsamma efter normalisering,
   efternamnen inte strider mot varandra, förekomsterna delar bosättningsort
   eller ämbete och ligger inom 40 år från varandra. Vilar likheten bara på ett
   ämbete med säte (biskop i Linköping) krävs högst 15 års uppehåll och högst
   50 års spann, och samma ämbete med olika säte hålls isär. Förekomster utan
   ort eller ämbete blir egna personer.

Sammanslagningen är medvetet försiktig, men två kända svagheter finns kvar.
Samma person kan bli flera entiteter när fälten saknar ort eller ämbete. Och
två ämbetsinnehavare med samma förnamn och säte kan slås ihop om de följer
tätt på varandra och fälten saknar patronymikon. Genitivformer som "hertig
Albrekts av Mecklenburg tjänare" tolkas som hertigen själv och blir egna,
okopplade entiteter med en felaktig titel. Auktoritetslistornas år är
sammanställda ur allmänna uppslagsverk och inte kontrollerade mot
primärlitteraturen. Utfärdarfältet är Riksarkivets registeruppgift och inte
ett citat ur brevet, så citatfältet är tomt. Alla påståenden har
`extraktion = 'regel'` och är ogranskade.

### Gärningar ur regesterna

De flesta regester inleds med utfärdaren följd av ett gärningsverb:
"Matts Garper … säljer till Bo Jonsson, drots i Sverige, 1 attung jord … i
Fettjestad i (Östra) Stenby socken … för 90 mark". `regest_garningar.py`
läser regestens första mening och tar ut verbet, mottagaren, egendomen,
priset och den första orten. Bara huvudsatsens verb räknas, så att "stadfäster
den gåva som X gjort" inte blir en gåva. Verben blir predikat: `saljer`,
`skanker` (skänker, och ger när egendom ges), `overlater`, `byter`,
`pantsatter`, `testamenterar`, `upplater`, `forlaner`, `stadfaster`, `domer`
och `utnamner`.

Varje utfärdare får ett påstående mot varje mottagare: säljaren är subjekt,
köparen objekt, egendom och pris värde och orten plats. Mottagarfrasen tolkas
med samma tolk som utfärdarfältet och identifieras på samma sätt (regenter,
påvar, biskopar, institutioner, sammanslagning) och ingår i samma
id-register. Den som köper jord i ett brev och säljer i ett annat blir därför
samma person; Karl Knutsson är köpare i 89 brev utöver de 322 han utfärdade.
Mottagarens titlar och ämbeten blir påståenden som utfärdarens. En
mottagare utan titel, ämbete, efternamn eller känt förnamn avvisas, eftersom
uppräknade gårdsnamn annars blir personer.

Kända svagheter: mottagare som är altaren, kapell eller kyrkor utan ortnamn
("S:ta Katarinas altare i Åbo domkyrka") känns ofta inte igen som
institutioner, och påståendet får då bara värde och inget objekt. Ett
påstående där verbet står efter en inledande bisats ("till kyrkan i
Linköping … skänker han") fångas inte. Domar och stadfästelser saknar objekt,
eftersom regestens form inte anger parten entydigt; vad som döms eller
stadfästs står i värdet.

### Stabila id:n

En person ska ha samma id oavsett hur många gånger skriptet körs, så att
andra källor kan länka till den. Regenter, påvar och biskopar har fasta id:n i
auktoritetslistorna, med Wikidata-id där sådant finns. För övriga personer
minns `data/sdhk_idregister.tsv` vilket id varje förekomst (brev och
utfärdarform) fick senast. När klustringen ändras får varje grupp det tidigare
id som flest av dess förekomster hade; större grupper väljer först. Ett id som
ingen grupp får tillbaka ersätts av det id dit flest av förekomsterna gick, och
finns kvar som en entitet med identifieringen `ersatt_av`, så att länkar från
andra källor går att följa. Ett id delas aldrig ut på nytt till en annan
person. Registret ligger i `data/` och delas mellan miljöerna, så att dev och
prod har samma id:n. Skriptet tar bort och skapar om sina påståenden vid
varje körning, men raderar aldrig en entitet som en annan källa refererar till.

### Biskopslistan

```bash
.venv/bin/python bygg_biskopslista.py
```

`data/auktoriteter/biskopar.json` byggs ur svenska Wikipedias stiftslistor
(CC BY-SA 4.0) och Wikidata (CC0): namn och ämbetsår ur listorna, Wikidata-id
ur biskoparnas artiklar och levnadsår ur Wikidata. Listornas ungefärliga år
("omkring 1150 till cirka 1190", "1050-talet") vidgas med fem år, och det
ursprungliga uttrycket står i `ar_text`. Ett id som en gång delats ut behålls
när listan byggs om, med Wikidata-id, artikel eller namn och första säte som
nyckel. En regent som också var biskop (Bengt Birgersson) har samma id i båda
listorna. Listorna bygger på äldre biskopslängder och skiljer sig ibland från
varandra och från nyare forskning.

## Påståenden ur granskningsbara filer

```bash
.venv/bin/python pastaenden_fil.py data/pastaenden/vastgotalagens_langder.json
.venv/bin/python pastaenden_fil.py --kontrollera data/pastaenden/*.json   # bara kontroll
```

Påståenden som en språkmodell eller en människa tagit ut ur en källa ligger
som JSON-filer i `data/pastaenden/`. Filen är det som granskas: varje
påstående har passage, subjekt, predikat, objekt, plats och ett ordagrant
citat ur passagens originaltext, aldrig ur en maskinöversättning. Laddaren
kontrollerar att varje citat finns i passagen, att predikaten finns i
vokabulären och att varje entitet finns i databasen eller definieras i filen,
och skriver ingenting om något fel hittas. Påståendenas id bildas av passage,
predikat, subjekt och objekt och är desamma vid varje inläsning. Entiteter som
filen definierar skrivs bara om de saknas; befintliga skrivs aldrig över.
Påståendena läses in med `extraktion = 'modell'` och är ogranskade.

Personer, platser och ämbeten länkas till samma entiteter som andra källor
använder: kungarna i Västgötalagens konungalängd från Sverker den gamle till
Johan Sverkersson är samma entiteter som regenterna i SDHK, och biskoparna i
biskopslängden är samma som i biskopslistan. Där längden och den gängse
identifieringen inte sammanfaller (Emund Kolbränna och Anund Jakob, Astmund
och Osmund) får längdens person en egen entitet och identifieringen en
bedömning.

`vastgotalagens_langder.json` innehåller 166 påståenden ur konunga-, lagmans-
och biskopslängden: ämbeten, ordningen mellan innehavarna (`eftertrader`, som
följer längdens numrering och inte säger att ämbetet övergick direkt),
föräldrar och syskon, födelseort, död, dråp och gravplats. Gärningar som
kyrkbyggen och donationer står i en egen fil, `vastgotalagens_langder_garningar.json` (56 påståenden: dop, grundanden, byggen av kyrkor, broar och vägar, vigningar, gåvor, lagstiftning, gränsdragning, pålagor, erövringar, flykt och härkomst; kyrkor är institutioner, kyrkogårdar, broar och vägar platser). Längderna daterar sällan
händelserna, så påståendena saknar tid och tidsavstånd.

### Kontroll med en oberoende extraktion

En fullständig granskning mot utgåvan tar lång tid. Det som framför allt
behöver kontrolleras är att påståendena säger det citaten säger, och det
görs med en andra, oberoende extraktion. `oberoende_extraktion/` innehåller
det som en annan språkmodell (ChatGPT, Codex) behöver:

- `PROMPT.md`, som anger uppgiften, utdatans form och reglerna,
- `indata_….json`, som innehåller originaltexterna (utan maskinöversättning),
  kandidatentiteter med fasta id:n och de tillåtna predikaten,
- `kontrollera.py`, som kontrollerar citat, predikat och entiteter utan
  databas, så att modellen kan rätta sin fil själv.

Kör den andra modellen utanför projektmappen, så att den inte kan läsa den
första extraktionen. `jamfor.py` parar sedan ihop entiteterna och
påståendena i de två filerna och listar vad som bara finns i den ena,
gemensamma påståenden med olika plats och fria värden som skiljer sig. En
människa avgör bara skillnaderna. För längderna var versionerna överens om
157 av 162 påståenden; avgörandena står i `oberoende_extraktion/jamforelse.md`.

Lagarna är för omfattande för en enda körning och kontrolleras med ett
stratifierat stickprov:

```bash
.venv/bin/python oberoende_extraktion/bygg_stickprov_lagar.py
python oberoende_extraktion/jamfor_stickprov_lagar.py \
    oberoende_extraktion/jamforelse_lagar/A_stickprov.json \
    oberoende_extraktion/lagar/utdata_lagar_stickprov.json \
    oberoende_extraktion/jamforelse_lagar/jamforelse.md
```

`bygg_stickprov_lagar.py` väljer flockar ur varje lag efter en kvot, så att
ämnena täcks. Flockar som normaliseringen markerat som osäkra tas alltid med,
liksom några grannflockar utan påståenden, så att även missade påståenden
syns. Mappen `lagar/` lämnas till den andra modellen. `jamforelse_lagar/`
innehåller våra påståenden för samma flockar och ska inte lämnas ut.

I stickprovet (53 flockar, 218 påståenden) täckte de två versionerna samma regler
i omkring 85 procent av fallen, sedan modelleringsskillnader räknats bort. Den
andra versionen hittade 21 påståenden som saknades; de är tillagda med en
anmärkning om det. Bedömningen står i `oberoende_extraktion/jamforelse_lagar/beslut.md`.

Avvikelserna i stickprovet var så stora att hela materialet kontrolleras på
samma sätt. `bygg_hela_lagar.py` delar flockarna med påståenden och deras
grannflockar, utom stickprovets, i nio delar om högst 120 000 tecken. Varje del
i `lagar_hela/del_NN/` lämnas till den andra modellen för sig, och
`jamfor_stickprov_lagar.py` jämför den med `jamforelse_lagar_hela/A_del_NN.json`
när delens indatafil anges som fjärde argument. Instruktionen bygger på
`PROMPT_mall_lagar.md`, som utöver stickprovets regler anger konventionerna för
ogilt dråp, edsöre och förverkat gods och tar med konungavalet.

En kodagent som Codex kan göra alla delarna i en körning: öppna `lagar_hela/`
(gärna en kopia utanför projektmappen) som projekt och be den följa `AGENTS.md`.
Den tar delarna i ordning, kontrollerar varje utdatafil, för `STATUS.md` och hoppar
över delar som redan är klara om körningen avbryts.

Sju delagenter prövade sedan de 2 034 skillnaderna mot texten, med instruktionen i
`jamforelse_lagar_hela/BEDOMNING.md`. Följden blev 189 tillagda, 58 rättade och 67
borttagna påståenden. Principfrågorna (rån och domarens ansvar, edsöre enligt
balkens sammanhang, supplerad text) avgjordes av användaren. Allt står i
`jamforelse_lagar_hela/beslut.md` och `genomforda_andringar.md`. `begrepp:arv`
betyder egendom; arvingarna som mottagare av bot är `begrepp:arvinge`.

## Normer i lagarna: dråp, edsöre och jäv

```bash
.venv/bin/python pastaenden_fil.py data/pastaenden/lagar/*.json   # en fil i taget
.venv/bin/python jamfor_lagar.py rapporter/jamforelse_lagar.md
```

`data/pastaenden/lagar/` innehåller påståenden ur alla 23 lagtexter i
databasen – landskapslagarna med fragment och tillägg, Hednalagen,
Vidhemsprästens anteckningar, Bjärköarätten, Magnus Erikssons land- och
stadslag, Kristoffers landslag och Grágás – om tre ämnen: dråp (påföljd,
bötesdelning, forum, bevis och lagens definitioner), edsöret och reglerna om
jäv och oväld för domare, nämnd, edgärd och vittnen. Påståenden om vem som
stiftat eller stadfäst lagen pekar på personerna (kung Birger, Magnus
Eriksson, Birger jarl, lagmännen Birger Persson och Lars Ulfsson, Viger spa
med flera).

Normpåståenden har ett begrepp som subjekt och passagen anger lagen:
`begrepp:drap` `paforljd` `begrepp:mansbot|nio marker`. Predikaten är
`paforljd`, `tillfaller`, `handlaggs_vid`, `kraver`, `diskvalificerar` (jäv:
grunden som subjekt, rollen som objekt), `utses_av`, `definieras_som` och
`stiftar_lag`. Begreppen – brott, delaktighet (rådsbane, hållbane), bötesformer
(tvebot, mordgäld, förverkat gods), processbegrepp (sägnarting, kungsnämnd,
räfst) och jävsgrunder (frändskap, svågerskap, muta, fiendskap) – finns i
begreppsregistret med termer och ordboksartiklar.

Påståendena är extraherade av språkmodell ur den fornsvenska texten, en lag
per delagent, och citaten är kontrollerade mot passagerna. Grágás finns bara i
dansk översättning och citeras efter den. Upplandslagens två handskrifter är
extraherade oberoende av varandra. Allt är ogranskat. `jamfor_lagar.py`
ställer upp påståendena per ämne och lag, ordnade efter landsdel, så att
skillnaderna mellan Götaland, Svealand, Gotland, Skåne, städerna, riket och
Island syns.

## Handregistrerade påståenden: Hygelac och ynglingakretsen

```bash
.venv/bin/python pastaenden_hygelac.py
```

En handregistrerad samling påståenden, identifieringar och bedömningar om
Beowulf, Gregorius av Tours, Liber historiae Francorum, Liber monstrorum,
Ynglingatal och Ynglinga saga. Påståendena bygger på passager som tolkarna
läst in, och varje citat kontrolleras mot sin passage vid laddningen; därför
ska tolkarna för Beowulf, openMGH, Heimskringla och Ynglingatal köras först.
Liber monstrorum har ingen egen tolk och registreras med ett kort utdrag ur I.2.

Samlingen innehåller:

- Hygelacs räd mot Frisland, med oberoende stöd hos Gregorius (skriven inom
  ett halvsekel) och i Liber monstrorum, och en senare krönika som bara
  återger Gregorius (`beroende_av`, inte `stoder`).
- Eadgils och Onela i Beowulf mot Aðils och Áli i Ynglinga saga — två
  oberoende traditioner om samma konflikt.
- Frågan om vilka gēatas var: götar, jutar eller en lärd litterär
  beteckning, med var sin forskares bedömning.
- Omstridda dateringar av Beowulf och Ynglingatal, där Snorres medeltida
  tillskrivning registreras som en bedömning bland andra.

Alla bedömningar är registrerade som ogranskade. Referenserna avser verkliga
publikationer, men ståndpunkterna är sammanfattade och ska kontrolleras mot
publikationerna innan de används som belägg. Beowulf citeras efter Harrison
& Sharp och Ynglinga saga efter Linder & Haggson (kap. 33 där är kap. 29 hos
Olson).

## Geografiska platser

```bash
.venv/bin/python platsregister.py hamta             # hämtar auktoriteter och Wikidata till data/platser
.venv/bin/python platsregister.py                   # läser in stommen
.venv/bin/python platser.py
.venv/bin/python platser.py --rapport rapport.txt   # orter som blev nya platser
```

Alla geografiska platser ska vara entiteter, från rike och landskap till socken,
gård och kloster. Källans ordalydelse behålls alltid. Kör `platser.py` efter varje
import av SDHK, runinskrifter eller auktoriteter.

Stommen är Riksantikvarieämbetets geografiska auktoriteter i K-samsök (CC0): 2 500
socknar, 290 kommuner, 21 län, 25 landskap och 250 länder, med koordinater från
Wikidata (CC0). Var en plats ligger i dag står i `plats_uppgift`, skilt från
källans namnform. Fältet `metod` säger hur uppgiften kom till och `granskad` om en
människa har kontrollerat den.

| Metod | Betydelse |
|---|---|
| `auktoritet` | Direkt ur RAÄ:s auktoriteter |
| `regel` | Härledd, t.ex. "Bredgatan i Lund", som ligger inne i Lund och får ortens läge som närmevärde. I "Klinteholm på Gotland" är Klinteholm platsen, och landskapet ger inget läge |
| `sprakmodell` | Två oberoende språkmodeller är överens; inte kontrollerad av människa |

Brevorter kontrolleras mot Riksarkivets historiska register: TORA, de äldre
geometriska kartorna och Rosenbergs lexikon, som hämtas med `platslexikon.py hamta`.
Samma namn finns på många håll, så ett namn räcker aldrig. Den överordnade enheten
ska stämma med brevet: häradet, eller att två oberoende bedömare valt samma kandidat
utifrån breven. Det avgörs brev för brev, och socken eller landskap räcker inte ensamma.

Besluten om brevorterna står i `data/platser`: `orter.tsv` (överens),
`orter_att_avgora.tsv` (oense, kopplas inte och väntar på mer underlag),
`lexikon_beslut.tsv` (häradsregeln), `brevgranskning.tsv` (bedömarnas beslut brev för
brev), `platskorrigeringar.tsv` och `platssammanslagningar.tsv`, `x_uppslag.tsv` (platser i "X i Y" med
eget läge från Wikidata) och `delade_orter.json` (namn som är
fördelade brev för brev, som Viborg i Jylland och Karelen). Ett namn som flera
platser delar, och som inte är fördelat, står kvar på en allmän entitet med
platserna som möjliga identifieringar.

Ortfältets parenteser (`harledd`) tolkas som att orten är tillagd av utgivaren och
inte står i brevet. SDHK:s dokumentation förklarar inte tecknen; tolkningen bygger
på brevens kommentarer och texter.

| Källa | Koppling |
|---|---|
| Brevens ort (`verk.utfardandeort`) | `verk_plats` med rollen `utfardandeort` |
| Runinskrifternas plats (`verk.extra`) | `verk_plats` med rollerna `fyndplats`, `socken`, `harad`, `kommun`, `omrade` och `forvaring` |
| Sätet i auktoritetslängderna (`auktoritet_titel.sate`) | `auktoritet_titel.sate_id` |
| Plats i ett påstående | `pastaende.plats_id` |

SDHK:s ortfält tolkas med regler. `(Lübeck.)` och `[Stockholm]` markeras som
härledda och `Rom?` som osäkert. `Tälje (= Södertälje)` blir Södertälje med Tälje
som namnform. `Visby eller Riga` blir två osäkra kopplingar och `Skanör och
Falsterbo` två säkra. `Rom, Peterskyrkan` och `Peterskyrkan, Rom` blir samma plats.

Kopplingen går på namnet. Den avgör inte vilken plats ett vanligt namn avser, så alla
brev från en ort som heter Vik hamnar på samma entitet, och Viborg avser både orten i
Danmark och den i Finland. Runinskrifternas socknar, härader och fyndplatser har
däremot område i id:t: Tuna sn i tre landskap är tre entiteter, och de slås aldrig upp
på namn. Fyndplatserna har Rundatas koordinater i `extra`. Koppling till nutida
orter och uppdelning av samma namn på flera platser återstår.

## Licens, proveniens och underlag

Varje passage hör till en utgåva med referens och licens; källsamlingen har
utgivare, adress, version och importdatum, och vittnena (handskrifter,
föremål) har signum och datering. `fornmed_hamta_passage` och sökträffarna
visar licensen (utgåvans, annars källsamlingens) och två länkar:

- `url` / `verk_url`: verket hos källan (SDHK:s brevsida, Rundatas
  inskriftssida, utgåvan på Wikisource, heimskringla.no, Perseus …),
- `underlag_url`: underlaget för just passagen, där texten kan kontrolleras
  manuellt:

| Källa | Underlag |
|---|---|
| openMGH (Adam, Vita Anskarii, Jordanes, Gregorius, LHF), Adams skolier | sidbilden i dMGH, efter MGH-sidan i adressen |
| Wikisource (Gutasagan, Gutalagen, längderna, Hednalagen), Saxo på latin | sidan på Wikisource, som visar de inskannade sidorna |
| heimskringla.no (sagorna, Eddorna, Snorres Edda, Ynglingatal, Saxo på danska) | sagans eller kvädets sida |
| Plinius, Prokopios | Scaife-läsaren (Perseus) på kapitlet |
| Germania | Perseus källfil (Scaife visar inte den latinska utgåvan) |
| Runinskrifter | Rundatas inskriftssida; verket listar dessutom länkar till fotografier (`bilder`) |

Maskinöversättningar har originalets underlag. SDHK, lagarna, OpenITI och
Liber monstrorum har bara verkslänken.

## Licenser

**Koden** har licensen i `LICENSE`.

**Källmaterialet** har sina egna licenser, som följer med varje text: utgåvan
anger sin licens, annars gäller källsamlingens. Varje samling registreras i
`kallsamling` med utgivare, licens och version. De viktigaste:

| Material | Licens |
|---|---|
| SDHK (Riksarkivet) | CC BY 4.0 |
| Runinskrifterna (Rundata.info, som bygger på Samnordisk runtextdatabas) | ODbL 1.0, innehållet DbCL 1.0, med Uppsala runforums tilläggsvillkor |
| Lagarna och de fornsvenska krönikorna (Fornsvenska textbanken via Språkbanken Text) | CC BY 4.0 |
| Schlyters och Söderwalls ordböcker (Språkbanken Text) | CC BY 4.0 |
| MGH (openMGH) | CC BY 4.0 |
| Transkriptioner från Wikisource, Perseus | CC BY-SA 4.0 |
| Arabiska källor (OpenITI) | CC BY-NC-SA 4.0 |
| Sagorna, Eddorna och Heimskringla (heimskringla.no, sagadb.org) | Fria utgåvor; normaliseringen i Guðni Jónssons utgåvor har upphovsrätt och används icke-kommersiellt |
| Äldre utgåvor ur Internet Archive och Project Runeberg | Fria från upphovsrätt |

Samnordisk runtextdatabas ska anges med namn och länk
(http://www.nordiska.uu.se/forskn/samnord.htm) varje gång uppgifter ur den
visas, och Uppsala runforum ska meddelas när databasen används i en annan
tillämpning.

**Det som projektet självt har tagit fram** finns i `data/` och har samma
licens som koden, med följande undantag:

- **Maskinöversättningarna** (`data/oversattningar/`) är bearbetningar av
  källtexterna och följer deras villkor. Översättningarna av OpenITI:s
  arabiska texter har CC BY-NC-SA 4.0, översättningarna av texter under
  CC BY-SA 4.0 har CC BY-SA 4.0, och översättningar av Guðni Jónssons
  normaliserade utgåvor får bara användas icke-kommersiellt. Alla är
  ogranskade och får inte citeras som översättning.
- **Biskopslängden** (`data/auktoriteter/biskopar.json`) bygger på svenska
  Wikipedia och har CC BY-SA 4.0; Wikidatas uppgifter har CC0.
- **Påståendena** (`data/pastaenden/`) citerar källtexterna ordagrant, och
  citaten har källans licens.

`data/raw/`, där tolkarna sparar det nedladdade källmaterialet, ingår inte i
repot. Tolkarna hämtar det själva.

Typsnitten i `grafisk_profil/` (Source Sans 3, EB Garamond, Texturina) har
SIL Open Font License 1.1; licenstexterna finns i `grafisk_profil/licenser/`.

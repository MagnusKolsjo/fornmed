# Ändringslogg — fornmed

Alla märkbara ändringar i projektet dokumenteras här.

Formatet följer [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/), och
versionerna [Semantic Versioning](https://semver.org/lang/sv/).

---

## [1.9.1] — 2026-11-10

### Tillagt

- `databasschema.py --pdf` skriver ut schemarapporten som PDF, och skriptet avbryter om en
  tabell eller kolumn i databasen saknar förklaring, grupp eller plats i diagrammet.

### Fixat

- Schemarapporten (`rapporter/databasschema.html` och `.pdf`) beskriver det aktuella schemat,
  med tabellen `extern_lank` och sökpostens alla kolumner.

## [1.9.0] — 2026-11-10

### Tillagt

- `quickstatements.py` skriver de entiteter som har ett Wikidata-id, i registret eller i
  längderna, som kommandon för QuickStatements, så att Wikidata-objekten kan få sitt
  Fornmed-id. Egenskapen anges med `--egenskap`. Ersatta entiteter tas inte med, och skriptet
  avbryter om ett objekt skulle få flera Fornmed-id. Med `--kontrollera` frågas Wikidata om
  varje objekt först.

## [1.8.0] — 2026-11-08

### Tillagt

- EDM-profil (`edm_export.py`): verken i Europeana Data Model, en gzippad RDF/XML-fil per
  källsamling, med datering, orter, utfärdare och genre och länkar till Wikidata. Metadatan är
  Fornmeds egen och CC0; regester och texter nås via verkets sida på fornmed.se, och
  `edm:rights` följer källsamlingens licens. Rundata och verk utan känt språk tas inte med.
- `/graf/{namn}` beskriver varje namngiven graf med titel, licens, källa och dumpfil.

### Ändrat

- Reglerna för w3id.org följer w3id:s krav (inga Options-direktiv, kontaktuppgifter i
  `.htaccess`).

## [1.7.0] — 2026-11-08

### Tillagt

- Länkade data: beständiga URI:er under `https://w3id.org/fornmed/id/`, CIDOC CRM, LRMoo och
  CRMinf som modell, Fornmeds egna klasser och egenskaper (`lankade_data/fornmed.ttl`) och
  vokabuläret som SKOS.
- Export av hela Fornmed som N-Quads (`rdf_export.py`), en gzippad fil per namngiven graf med
  en VoID-beskrivning och licens per graf.
- `/id/{typ}/{id}` skickar en webbläsare till postens sida och ger ett program Turtle, JSON-LD,
  N-Triples eller RDF/XML; `/def/` ger klasser och egenskaper. REST-API:ets verk, passager,
  utgåvor, entiteter och påståenden finns också i dessa format, och webbsidorna har
  Schema.org som JSON-LD.
- SPARQL-ändpunkt på `/sparql` (Oxigraph i läsläge) och dumpfilerna under `/data/rdf/`.
- Länkar till Wikidata, Kulturmiljöregistret, Samnordisk runtextdatabas, TORA och Kartverkets
  ortnamnsregister (`lankar.py`, tabellen `extern_lank`).
- Katalog för Mix'n'match och Wikidata-id för regenter, påvar och biskopar i längderna.
- SHACL-former (`lankade_data/former.ttl`) och validering av exporten (`rdf_validera.py`);
  leveransen avbryts om exporten bryter mot formerna.

### Ändrat

- Platser med samma Wikidata-objekt på samma nivå slås ihop, och personer som stod under två
  id:n hänvisar till ett. De gamla id:na finns kvar och fungerar.
- Hela datamängden anger ingen gemensam licens, eftersom graferna har olika licenser.

### Fixat

- Norska orter som placerats fel (Hviteseid, Tautra, Tuteröen, Hof p. Thoten, Lardal) och
  OCR-varianter av samma ort i Diplomatarium Islandicum.
- Felaktiga Wikidata-id för biskopar (ämbeten och listor i stället för personer), för
  orter i Islandicum och Norvegicum och för några av Riksantikvarieämbetets socknar.
- Datumintervall som slutade före de började, när slutet var en dag som inte finns.

## [1.6.0] — 2026-11-08

### Tillagt

- Påståendena på verkets sida: ett reglage visar påståendena ur brevet i en stenfärgad
  ruta med runröd kant, skild från källtexten. Svar visar det besvarade brevet och hur säker
  kopplingen är. Valet sparas i adressen och i webbläsaren, som för källkritisk hjälp.

### Fixat

- De isländska brevens sidor på webbplatsen (adresser som `di-4-696`) gav 404.

## [1.5.0] — 2026-11-08

### Tillagt

- Påståenden ur Diplomatarium Fennicums utfärdarfält och regester, på samma sätt som
  ur SDHK (`pastaenden_sdhk.py`). DF:s personer förs till SDHK:s när namn, ort eller
  ämbete stämmer, utan att något SDHK-id ändras.
- Predikaten `skriver_till` (missivets adressat) och `besvarar` (brevet svarar på ett
  tidigare brev), med bedömningsaspekten `brevkoppling` för hur säkert det besvarade
  brevet är identifierat.
- Påståenden ur Diplomatarium Norvegicum (`dn_regester.py`): utfärdare, ämbeten,
  gärningar, missivens adressater och svar ur de danska och norska regesterna, 26 271
  påståenden ur 17 891 brev. Vittnesbrevens gärningar får parterna i at-satsen som subjekt.
  DN läses i ett eget steg, så att inga sammanslagningar i SDHK eller DF tas bort.
- Påståenden ur Diplomatarium Islandicums rubriker (`di_regester.py`): utfärdare, ämbeten,
  gärningar och missivens adressater, 2 516 påståenden. Isländska namn i genitiv och dativ
  skrivs om till nominativ. DI läses i ett eget steg efter DN.
- Brevväxling i DI: svar känns igen i rubrikerna, och tre DI-svar är kopplade till det
  besvarade brevet (Henrik VI:s svar till Kristoffer av Bayern, biskop Gizurs svar till
  Jón Arason, biskop Hákons kvittens på Auðfinns brev). Ett DN-svar kopplas till ett brev i
  DI. Hänvisningar mellan DN- och DI-brev räknas, och en biskop utan säte i DN eller DI slås
  inte längre upp bland de svenska biskoparna.
- Fler svar kopplas till det brev de besvarar: brev daterade bara till månad eller år,
  adressater i genitiv ("rådets i Danzig brev"), datum som "24/9 (1429)" och FMU-nummer.
  Utgivarens nummer räknas bara när brevet har svarets parter, och en förläning samma dag
  räknas inte som ett besvarat brev. 28 svar är kopplade mot 23 tidigare; av de tidigare
  föll ett bort som fel (SDHK 33191) och ett pekade på fel brev (DF 1575, "n:o 1,574").
- DN:s svar känns igen i fler former ("besvarer et brev fra", "Modtagelsen af et Brev",
  verb i flertal), och sju svar i DN är kopplade till det besvarade brevet. Ett missiv
  vars adressat inte gick att identifiera räknas inte längre som besvarat brev, och
  "ang." avslutar inte en mening i SDHK:s regester.
- Personlista med levnadsår ur SBL och Wikidata (`bygg_personlista.py`,
  `data/auktoriteter/personer.json`, 1 121 personer). Brevpersoner kopplas till den när
  namn, levnadstid och släktnamn eller ämbete stämmer, och dödsåret är en bortre gräns.
  Wikidatas yrke, befattning och ätt räknas också. 170 personer har fått sina brev
  samlade; 921 tidigare id:n hänvisar till dem.
- `platsdubletter.py` och `data/platser/platsdubletter.tsv`: 217 platser som fanns under
  två id:n (brevort och fyndplats, brevens socken och RAÄ:s, olika stavningar) hänvisar
  nu till en och samma plats. De gamla id:na finns kvar och fungerar.
- Uppdragen bakom maskinöversättningarna (`data/oversattningar/promptar/`): de 209
  delagenternas uppdrag ordagrant ur sessionsloggarna, hjälpskripten, riktlinjernas första
  version och ett index från översättningsfil till uppdrag. Maskinöversättningarnas
  utgåvor har språkmodellen, Claude Opus 5.5 (`claude-opus-5-5`), som översättare.
- Metodsidan beskriver källkoden och underlaget på GitHub, och påståendesidan breven i alla
  fyra diplomatarierna.

### Ändrat

- Brevpersoner med samma släktnamn som klustringen höll isär slås ihop (893 id:n hänvisar
  nu till ett annat), och 2 551 personer med samma patronymikon inom tio år har fått en
  möjlig identifiering med varandra i stället för att slås ihop.
- Namnar där minst den ena saknar ort och ämbete slås ihop när de har en gemensam
  medaktör i två brev högst fem år isär, och den sammanslagna personen spänner över högst
  60 år (40 utan ort och ämbete). 615 id:n hänvisar därmed till ett annat.
- Klustringen föredrar den person som en förekomst hörde till förra körningen, bland de
  kandidater reglerna godtar, så att personer inte delas när nya förekomster läses in.
- Tyska ordens högmästare och Livländska ordensmästaren känns igen i fler former.
- `pastaenden_sdhk.py` raderar inte längre några entiteter, id-registret behåller nycklar
  som inte förekommer längre, och en förekomst vars form ändrats ärver sin gamla nyckels id.
  Registret skrivs till en tillfällig fil först.
- Brevpåståendenas orter slås upp med platsregistrets regler och i id-ordning, så att ett
  namn alltid ger samma plats och handregistrerade platser går före brevens egna
  (Bjälbo, Essunga, Gökhem). En ersatt plats följs till den nya, och `pastaenden_sdhk.py`
  raderar inte längre platser, eftersom `platser.py` flyttar påståendena efteråt.

## [1.4.3] — 2026-11-07

### Fixat

- Nya sidor på webbplatsen hamnade sist i menyn; de placeras nu i menyns ordning.

## [1.4.2] — 2026-11-07

### Ändrat

- Webbplatsens källförteckning redovisar Diplomatarium Fennicum, Norvegicum och Islandicum som en
  post var under sina formella namn, som SDHK, i stället för en post per brev. Titeln leder till
  sökningen i källsamlingen. Förstasidans antal medeltidsbrev omfattar alla fyra brevsamlingarna
  och räknar ett brev som finns i flera en gång.

### Fixat

- Webbplatsens skript ligger i egna filer (`webb.js`, `karta.js`) och tidslinjens staplar har
  höjden som CSS-klass, så att kartan, tidslinjen, menyn och den källkritiska hjälpen fungerar
  med innehållspolicyn, som inte tillåter inbäddade skript eller stilattribut.

## [1.4.1] — 2026-11-07

### Fixat

- `/register/` gav serverfel.

## [1.4.0] — 2026-11-07

### Tillagt

- Diplomatarium Norvegicum som källa: 19 113 brev ur band 1–23 med regester, brevtext, tillägg,
  noter och registerposter (`importera_dn.py`). Brevspråket bestäms maskinellt (`sprakklassning.py`,
  `sprak_urval.py`, `sprak_samla.py`), och utfärdandeorterna knyts till platser, med läge ur
  Kartverkets ortnamnsregister där namnet är entydigt (`hamta_ssr.py`) och med nutida namn som en
  språkmodell föreslagit och Kartverket eller Wikidata bekräftat (`dn_orter.py`).
- Diplomatarium Islandicum som källa: 8 723 brev ur band 1–16 med isländsk rubrik ur
  innehållsförteckningen och brevtext ur OCR (`importera_di.py`), maskinellt bestämt språk och
  orter med läge där en språkmodells nutida namn och sýsla bekräftas av Icelandic Saga Map eller
  Wikidata (`hamta_sagamap.py`, `di_orter.py`).
- Ett brev som finns i både SDHK och Diplomatarium Fennicum eller Norvegicum visas en gång i
  sökningen, med de andra utgåvorna i `samma_brev`.
- Danska regester indexeras med dansk stemming, och `texttyper='alla'` söker även i noter och
  registerposter.
- Sökindex (`sokindex.py`, tabellerna `sokpost` och `sokpost_plats`): varje verk och
  entitet med tillkomst, förlaga och händelsetid och med platser för händelse,
  tillkomst, förvaring och läge. Byggs om av `leverans.py`.
- `/v1/sok/objekt`: dokument och entiteter med filter på typ, källsamling, tidsaxel,
  plats och kartruta, och fasetter för typ, källsamling, sekel, land och landskap.
  Utan fråga listas urvalet i tidsordning. Med `karta=true` följer urvalets platser med läge
  och antal, och fasetten `decennium` ger underlaget för en tidslinje.
- `/v1/sok/objekt/{id}`: ett verks eller en entitets sökpost med tider och platser.
- Webbplatsen: söksida med filter, fasetter, karta och tidslinje, och sökruta på startsidan.
  Träffarna visar typ, tid och plats; textkritiska uppgifter (tillkomst, äldsta vittne,
  förvaring) visas på begäran. Breven har egna sidor under `/kallor/verk/sdhk-<nr>/`.
- Webbplatsen: registret med en sida per person, plats, institution, ämbete, folk och begrepp
  (`/register/<id med -- för kolon>/`), med påståenden som länkar till källan och till andra
  entiteter, identifieringar, namnar och namnformer. Alla sökträffar leder till en sida.
- Kartorna använder Leaflet 1.9.4 (BSD-2) och en baskarta ur Natural Earth (public domain)
  som ligger på webbplatsen själv (`webb/bygg_baskarta.py`); en sida gör inga anrop till
  andra servrar.
- Webbplatsens sidhuvud, sökträffar och statusetiketter följer den grafiska manualen.
- Brevsidorna och träffarnas källkritiska hjälp visar forskningens bedömningar av källan i klartext,
  med bedömare och motivering; en bedömning av ett vittne, som en förfalskad avskrift, anger vittnet.
- Felstavningstolerant sökning efter namn och termer (`stavning.py`) på söksidan och i
  `/v1/sok/objekt`, med tolkningen i svaret.
- `/v1/entiteter/{id}` och `fornmed_hamta_entitet`: påståendena har subjektets, objektets och
  platsens namn, platsens id, passagen och verket, och namnformerna har verket.
- `sok.Filter` har tidsaxel, källsamling, plats, platsroll, objekttyp, undertyp och
  kartruta; `/v1/sok` och `fornmed_sok` fungerar som förut.
- Per-Axel Wiktorssons utslag i *Falskt eller äkta: i brev från Sveriges medeltid* (Skara 2026)
  för 162 SDHK-brev, som egen bedömare med brevets nummer i boken
  (`data/sdhk/akthet_wiktorsson.tsv`).

### Ändrat

- SDHK:s äkthetsbedömningar kommer ur en granskad lista (`data/sdhk/akthet_granskning.tsv`,
  `sdhk_akthet.py`) i stället för en ordregel: 20 brev som inte är misstänkta har inte längre
  någon bedömning, 44 brev har fått den de saknade, värdena skiljer förfalskning, misstänkt
  förfalskning och interpolation, och tre brev redovisas som omstridda med båda
  ståndpunkterna. Motiveringarna är inte längre avkapade. Se `rapporter/akthet_sdhk.md`.
- En koppling mellan SDHK och Diplomatarium Fennicum kräver samma dag eller månad; samma år räcker
  bara när DF enbart anger året (`data/platser/df_fmu_osakra.tsv`).

## [1.3.1] — 2026-11-04

### Fixat

- Socknarna läses i fast ordning, så att samma körning alltid ger samma läge och id. 63 tidigare
  publicerade plats-id hänvisar till sina nya (`data/platser/platshanvisningar.tsv`).

## [1.3.0] — 2026-11-04

### Tillagt

- Diplomatarium Fennicum som källa: 6 876 brev med regester och brevtext (`hamta_df.py`,
  `importera_df.py`). Brev som SDHK anger som FMU och som har samma år får SDHK-numret i
  verkets uppgifter. Regester ur Auctoritate Papae tas inte med.
- DF:s platsregister: DF-breven knyts till platser, och SDHK-orter utan läge får läget när
  samma brev i DF anger platsen (`platser.py`). Platser som inte stämmer med befintliga
  blir egna, eftersom registrets koordinater antas gälla den ort som avses.
- Isofs Ortnamnsregister (CC BY) ger orter utan beslut socken och härad (`hamta_isof.py`).
  Nya beslut läggs till och fattade beslut står kvar.
- `data/platser/oklara_lagen.tsv`: brev vars läge ska granskas.

### Fixat

- Ekesjö är inte längre knuten till Eksjö.

## [1.2.1] — 2026-11-03

### Ändrat

- MCP-instruktionen säger att originalet ska citeras i stället för en maskinöversättning.

### Fixat

- En ort och en plats för enskilda brev i samma socken är samma entitet; de gamla id:na
  hänvisar vidare.

## [1.2.0] — 2026-11-03

### Tillagt

- Brevorter kontrolleras mot TORA, de äldre geometriska kartorna och Rosenbergs lexikon.
  En kandidat godtas bara om den överordnade enheten stämmer med brevet, och samma
  namn delas upp brev för brev (`platslexikon.py`).

### Fixat

- Brevorter som bara hade kopplats på namnet är rättade där breven pekar på annan
  plats, till exempel Erikstad, som var Erikstad i Dalsland men avser Bankekind och Vittaryd.

## [1.1.0] — 2026-11-03

### Tillagt

- Geografiska platser som entiteter: tabellen `verk_plats` kopplar breven och
  runinskrifterna till sina platser med roll och källans ordalydelse, och
  `auktoritet_titel.sate_id` kopplar sätena. Fylls av `platser.py`.
- Platsregister: `platsregister.py` läser in RAÄ:s socknar, kommuner, län, landskap
  och länder (CC0) som entiteter, och tabellen `plats_uppgift` anger nutida namn,
  land, län, kommun, socken och koordinater med metod och granskningsstatus.
- De flesta brevorter knyts till nutida platser genom två oberoende språkmodeller,
  ogranskade av människa. Viborg är uppdelat på Jylland och Karelen. Står socknen
  i brevet får brevet en egen plats, som "Viby (Hassle socken)".
- Runinskrifternas socknar och kommuner pekar på RAÄ:s, och deras förvaring är en ny
  platsroll med museer som egna entiteter.
- Filtret `plats` på `/v1/verk` omfattar platserna i en kommun, ett landskap eller ett land.
- Verkets platser i `/v1/verk/{id}` och `fornmed_hamta_verk`, filtret `plats` i
  `/v1/verk` och `sate_id` i `/v1/auktoriteter`.

## [1.0.0] — 2026-11-02

Första publiceringen. Databasschemat i den här versionen är bas-schemat; senare
ändringar görs som migrationer (se `db/schema_postgres.sql`).

### Källor

- Medeltidsbrev ur Riksarkivets SDHK (44 264 brev fram till 1540) med regester
  och originaltexter.
- Runinskrifter ur Rundata.info (6 815 inskrifter) med translitterering,
  normaliseringar och översättningar.
- Landskapslagarna, Magnus Erikssons land- och stadslag, Kristoffers landslag,
  Bjärköarätten, Hednalagen och Grágás.
- Eddorna, Heimskringla, islänningasagorna, fornaldarsagorna och kungasagorna.
- Saxo, Sven Aggesen, Adam av Bremen med skolier, Erikskrönikan, Karlskrönikan,
  Konungastyrelsen, Olaus Magnus och frankiska och tyska krönikor och annaler ur MGH.
- Romerska och arabiska källor om Norden.
- Schlyters och Söderwalls ordböcker och ett begreppsregister.
- Längder över regenter, biskopar och påvar.
- Svenska maskinöversättningar, märkta som ogranskade, där fria äldre
  översättningar saknas.

### Påståenden och bedömningar

- 87 090 regelbaserade påståenden ur SDHK:s utfärdarfält och regester, med
  identifiering av regenter, påvar och biskopar och stabila id:n.
- Pilot: 222 påståenden ur Västgötalagens längder, kontrollerade med en
  oberoende extraktion.
- Pilot: 2 235 påståenden om dråp, edsöre, jäv, lagstiftning och konungaval ur
  23 lagtexter, kontrollerade i sin helhet med en oberoende extraktion.
- Forskningens bedömningar med bedömare, publikation och granskningsstatus.

### Tjänster

- MCP-server med elva verktyg för sökning, läsning, entiteter, påståenden,
  begrepp och ordböcker, i stdio-läge och http-läge (med nyckel eller öppet
  läsläge).
- REST-API med OpenAPI: hela dokument, delar och språkversioner, sida vid
  sida-visning, listor med filter och svar som JSON, Markdown, text och CSV.
- Webbplats i Django och Wagtail med källförteckning, källtexterna som
  webbsidor och sidor om metod, påståendesamlingar, MCP och API.
- Installation på en Ubuntu-server med nginx, certifikat, Umami, GoAccess,
  hälsokontroll och databasbyten utan avbrott.

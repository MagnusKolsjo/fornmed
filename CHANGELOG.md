# Ändringslogg

Formatet följer [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/), och
versionerna [Semantic Versioning](https://semver.org/lang/sv/).

## [Ej utgivet]

### Tillagt

- Påståenden ur Diplomatarium Norvegicum (`dn_regester.py`): utfärdare, ämbeten,
  gärningar, missivens adressater och svar ur de danska och norska regesterna, 26 271
  påståenden ur 17 891 brev. Vittnesbrevens gärningar får parterna i at-satsen som subjekt.
  DN läses i ett eget steg, så att inga sammanslagningar i SDHK eller DF tas bort.

- Fler svar kopplas till det brev de besvarar: brev daterade bara till månad eller år,
  adressater i genitiv ("rådets i Danzig brev"), datum som "24/9 (1429)" och FMU-nummer.
  Utgivarens nummer räknas bara när brevet har svarets parter, och en förläning samma dag
  räknas inte som ett besvarat brev. 28 svar är kopplade mot 23 tidigare; av de tidigare
  föll ett bort som fel (SDHK 33191) och ett pekade på fel brev (DF 1575, "n:o 1,574").
- Tyska ordens högmästare och Livländska ordensmästaren känns igen i fler former.

- Personlista med levnadsår ur SBL och Wikidata (`bygg_personlista.py`,
  `data/auktoriteter/personer.json`, 1 121 personer). Brevpersoner kopplas till den när
  namn, levnadstid och släktnamn eller ämbete stämmer, och dödsåret är en bortre gräns.
  Wikidatas yrke, befattning och ätt räknas också. 170 personer har fått sina brev
  samlade; 921 tidigare id:n hänvisar till dem.

- Brevpersoner med samma släktnamn som klustringen höll isär slås ihop (893 id:n hänvisar
  nu till ett annat), och 2 551 personer med samma patronymikon inom tio år har fått en
  möjlig identifiering med varandra i stället för att slås ihop.
- Namnar där minst den ena saknar ort och ämbete slås ihop när de har en gemensam
  medaktör i två brev högst fem år isär, och den sammanslagna personen spänner över högst
  60 år (40 utan ort och ämbete). 615 id:n hänvisar därmed till ett annat.

- `platsdubletter.py` och `data/platser/platsdubletter.tsv`: 217 platser som fanns under
  två id:n (brevort och fyndplats, brevens socken och RAÄ:s, olika stavningar) hänvisar
  nu till en och samma plats. De gamla id:na finns kvar och fungerar.
- Påståenden ur Diplomatarium Fennicums utfärdarfält och regester, på samma sätt som
  ur SDHK (`pastaenden_sdhk.py`). DF:s personer förs till SDHK:s när namn, ort eller
  ämbete stämmer, utan att något SDHK-id ändras.
- Predikaten `skriver_till` (missivets adressat) och `besvarar` (brevet svarar på ett
  tidigare brev), med bedömningsaspekten `brevkoppling` för hur säkert det besvarade
  brevet är identifierat.

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
- Brevorter kontrolleras mot TORA, de äldre geometriska kartorna och Rosenbergs lexikon.
  En kandidat godtas bara om den överordnade enheten stämmer med brevet, och samma
  namn delas upp brev för brev (`platslexikon.py`).
- Diplomatarium Fennicum som källa: 6 876 brev med regester och brevtext (`hamta_df.py`,
  `importera_df.py`). Brev som SDHK anger som FMU och som har samma år får SDHK-numret i
  verkets uppgifter. Regester ur Auctoritate Papae tas inte med.
- DF:s platsregister: DF-breven knyts till platser, och SDHK-orter utan läge får läget när
  samma brev i DF anger platsen (`platser.py`). Platser som inte stämmer med befintliga
  blir egna, eftersom registrets koordinater antas gälla den ort som avses.
- Isofs Ortnamnsregister (CC BY) ger orter utan beslut socken och härad (`hamta_isof.py`).
  Nya beslut läggs till och fattade beslut står kvar.
- `data/platser/oklara_lagen.tsv`: brev vars läge ska granskas.
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
- Webbplatsen: söksida med filter, fasetter, karta och tidslinje, och sökruta på startsidan.
  Träffarna visar typ, tid och plats; textkritiska uppgifter (tillkomst, äldsta vittne,
  förvaring) visas på begäran. Breven har egna sidor under `/kallor/verk/sdhk-<nr>/`.
- Webbplatsen: registret med en sida per person, plats, institution, ämbete, folk och begrepp
  (`/register/<id med -- för kolon>/`), med påståenden som länkar till källan och till andra
  entiteter, identifieringar, namnar och namnformer. Alla sökträffar leder till en sida.
- `/v1/sok/objekt/{id}`: ett verks eller en entitets sökpost med tider och platser.
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

- `pastaenden_sdhk.py` raderar inte längre några entiteter, id-registret behåller nycklar
  som inte förekommer längre, och en förekomst vars form ändrats ärver sin gamla nyckels id.
  Registret skrivs till en tillfällig fil först.

- Brevpåståendenas orter slås upp med platsregistrets regler och i id-ordning, så att ett
  namn alltid ger samma plats och handregistrerade platser går före brevens egna
  (Bjälbo, Essunga, Gökhem). En ersatt plats följs till den nya, och `pastaenden_sdhk.py`
  raderar inte längre platser, eftersom `platser.py` flyttar påståendena efteråt.
- SDHK:s äkthetsbedömningar kommer ur en granskad lista (`data/sdhk/akthet_granskning.tsv`,
  `sdhk_akthet.py`) i stället för en ordregel: 20 brev som inte är misstänkta har inte längre
  någon bedömning, 44 brev har fått den de saknade, värdena skiljer förfalskning, misstänkt
  förfalskning och interpolation, och tre brev redovisas som omstridda med båda
  ståndpunkterna. Motiveringarna är inte längre avkapade. Se `rapporter/akthet_sdhk.md`.
- Ekesjö är inte längre knuten till Eksjö.
- Webbplatsens källförteckning redovisar Diplomatarium Fennicum, Norvegicum och Islandicum som en
  post var under sina formella namn, som SDHK, i stället för en post per brev. Titeln leder till
  sökningen i källsamlingen. Förstasidans antal medeltidsbrev omfattar alla fyra brevsamlingarna
  och räknar ett brev som finns i flera en gång.
- Webbplatsens skript ligger i egna filer (`webb.js`, `karta.js`) och tidslinjens staplar har
  höjden som CSS-klass, så att kartan, tidslinjen, menyn och den källkritiska hjälpen fungerar
  med innehållspolicyn, som inte tillåter inbäddade skript eller stilattribut.
- En koppling mellan SDHK och Diplomatarium Fennicum kräver samma dag eller månad; samma år räcker
  bara när DF enbart anger året (`data/platser/df_fmu_osakra.tsv`).
- Socknarna läses i fast ordning, så att samma körning alltid ger samma läge och id. 63 tidigare
  publicerade plats-id hänvisar till sina nya (`data/platser/platshanvisningar.tsv`).
- Brevorter som bara hade kopplats på namnet är rättade där breven pekar på annan
  plats, till exempel Erikstad, som var Erikstad i Dalsland men avser Bankekind och Vittaryd.
- Verkets platser i `/v1/verk/{id}` och `fornmed_hamta_verk`, filtret `plats` i
  `/v1/verk` och `sate_id` i `/v1/auktoriteter`.

## [1.0.0] – 2026-11-02

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

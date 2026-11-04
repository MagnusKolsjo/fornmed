# Ändringslogg

Formatet följer [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/), och
versionerna [Semantic Versioning](https://semver.org/lang/sv/).

## [Ej utgivet]

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

### Ändrat

- Ekesjö är inte längre knuten till Eksjö.
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

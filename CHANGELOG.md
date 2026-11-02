# Ändringslogg

Formatet följer [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/), och
versionerna [Semantic Versioning](https://semver.org/lang/sv/).

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

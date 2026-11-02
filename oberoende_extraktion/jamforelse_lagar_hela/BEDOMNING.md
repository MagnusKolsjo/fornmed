# Bedömning av skillnader mellan två extraktioner ur lagarna

Två språkmodeller har oberoende av varandra tagit ut normpåståenden om dråp, edsöre, jäv och lagstiftning ur samma lagflockar:

- **A** är projektets extraktion. Den finns i `data/pastaenden/lagar/` och för varje del i `jamforelse_lagar_hela/A_del_NN.json`.
- **B** är Codex extraktion, i `lagar_hela/del_NN/utdata_del_NN.json`.

Reglerna för extraktionen står i `lagar_hela/del_NN/PROMPT.md`. Läs den först. Den gäller båda versionerna.

Din uppgift är att bedöma varje skillnad mot lagtexten och avgöra vilken version som har rätt. Skillnaderna står i `jamforelse_lagar_hela/jamforelse_del_NN.json`. Varje skillnad har ett `id` och en av tre typer:

- `bara_A`: ett påstående som bara finns i A,
- `bara_B`: ett påstående som bara finns i B,
- `olika_varde`: samma passage, predikat, subjekt och objekt, men värdena är så olika att de kan säga olika saker.

Påståendena har formen `[passage, subjekt, predikat, objekt, plats, citat, anmärkning]`.

## Läsa texten

Flockens text finns i `lagar_hela/del_NN/indata_del_NN.json` under `passager`. Som läshjälp finns en maskinöversättning till svenska. Den kan vara fel och får aldrig citeras. Den hämtas med passagens id, med söktjänstens API igång lokalt (`python tjanst.py`):

```
curl "http://127.0.0.1:8424/v1/passager/PASSAGE_ID?sprak=swe&format=txt"
```

Med `sprak=fsv,swe` och `parallellt=true` på `/v1/verk/VERK_ID/text` visas original och översättning sida vid sida.

Grágás finns bara i dansk översättning. Den läses direkt ur indata.

## Beslut

Varje skillnad får exakt ett av dessa beslut:

| beslut | när | åtgärd |
|---|---|---|
| `samma_regel` | Den andra versionen säger samma sak med ett annat subjekt, objekt eller predikat, eller med andra ord. Gäller också när regeln är uppdelad på flera påståenden. | ingen |
| `A_ratt` | (bara_A) Påståendet stöds av citatet och texten och hör till ämnena. B har missat det. | ingen |
| `A_fel` | (bara_A, olika_varde) A har läst fel: fel påföljd, belopp, mottagare, roll eller villkor. | `ny_rad` med rättat påstående, eller `null` om det ska tas bort |
| `A_utanfor` | (bara_A) Påståendet hör inte till ämnena, till exempel sår, stöld eller arv som inte uttryckligen gäller dråp, edsöre eller jäv. | tas bort |
| `B_lagg_till` | (bara_B) B har hittat en regel som texten stöder och som A saknar helt. | `ny_rad` med påståendet, anpassat till konventionerna nedan |
| `B_fel` | (bara_B, olika_varde) B har läst fel eller modellerat orimligt. | ingen |
| `osaker` | Texten går att läsa på flera sätt, eller frågan är principiell. | förklara i motiveringen vad användaren ska avgöra |

Var sträng mot båda versionerna. Använd `samma_regel` bara när regeln verkligen redan finns i den andra versionen. Sök efter den i hela flockens påståenden i båda filerna, inte bara i skillnadslistan. Använd `B_lagg_till` bara för ny information, inte för en omformulering.

## Konventioner för ny_rad

- Bara id:n ur `kandidater` i indata. Inga nya entiteter.
- Citatet ska stå ordagrant i flockens text, tecken för tecken.
- Ett ogilt dödande: `begrepp:drap` `paforljd` `begrepp:ogild`, med villkoret i värdet.
- Att en gärning bryter edsöret: `begrepp:edsore` `definieras_som` `=…`.
- En fredlös eller dömd mans gods som delas: subjektet är `begrepp:forverkat_gods`.
- En jävsgrund som finns som begrepp är subjekt i `diskvalificerar`. Annars är subjektet `begrepp:jav` och grunden står i värdet.
- Den som stiftat lagen anges med person-id om personen nämns och finns bland kandidaterna.
- Anmärkningen avslutas med `Tillagt efter oberoende kontroll (Codex).` för `B_lagg_till`, eller `Rättat efter oberoende kontroll (Codex).` för `A_fel`.
- Två påståenden får inte ha samma passage, predikat, subjekt och objekt. Skilj dem i så fall åt i värdedelen.

## Utdata

Skriv en JSON-lista till `jamforelse_lagar_hela/bedomning_del_NN.json`, med ett objekt per skillnad i skillnadslistan:

```json
[{"id": 1, "beslut": "A_ratt", "motivering": "kort skäl, gärna med fornsvenskt ord", "ny_rad": null}]
```

Kontrollera till sist att varje `id` har ett beslut och att varje `ny_rad` har ett citat som står i flockens text. Det kan du göra med ett litet Python-skript.

Ändra inga andra filer. Läs inte in något i databasen.

Svara med högst 150 ord: antal av varje beslut, de viktigaste felen i A och de fall som är `osaker`.

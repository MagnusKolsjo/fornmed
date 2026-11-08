# Extrahera ur Kristoffers landslag

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/kristoffers_landslag.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt, särskilt regeln om Kristoffers landslag i avsnittet "Särskilda regler för vissa verk". Läs den först.

Uppdrag:
- Lag: Kristoffers landslag (1442), huvudverket `verk:lag:kristoffers_landslag`. Läs flockarna utan balk (prolog, stadfästelse), ' KgB ' och 'Konungx balker' (konungaval, eriksgata, eder — med `begrepp:konungaval`, `begrepp:eriksgata`, `utses_av`), ' EB ' (edsöre), ' TgB ' (tingmålabalken: jäv, nämnd), ' Dmv ' och ' Dvå ' (dråp med vilja och av våda).
- Kontrollera i delverken `verk:lag:kristoffers_landslag_innehallsligt_andrade_flockar_i_forhall` och `verk:lag:kristoffers_landslag_nyskrivna_flockar_i_forhallande_till_me` vilka av dessa flockar som är ändrade eller nya, och märk påståendena därefter i anmärkningen.
- Plats: `plats:sdhk:sverige`.
- Fil: <projektmapp>/data/pastaenden/lagar/kristoffers_landslag.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen, och nämn särskilt vad som ändrats jämfört med Magnus Erikssons landslag.
````

## Delagentens slutrapport

Filen `<projektmapp>/data/pastaenden/lagar/kristoffers_landslag.json` har 307 påståenden. `pastaenden_fil.py --kontrollera` ger inga fel. Ingenting är inläst i databasen och inga andra filer är ändrade.

**Per ämne:** dråp 135, edsöre och rån 90, jäv och förfarande 58, konungaval och eriksgata 21, `stiftar_lag` 3. Av påståendena är 38 märkta "ändrad" och 12 "nyskriven" i förhållande till MEL.

**Lästa flockar:** KgB 1–36, TgB 1–43, EB 1–44, Dmv 1–39 och Dvå 1–17, plus flockarna utan balk: B–P och Karl IX:s tryckningsedikt från 1608. Det finns ingen medeltida prolog eller stadfästelse. Uppgiften att Kristoffer stadfäste lagen 1442 kommer bara från ediktet. Eriks stadga från 1407 (B 6) står med som tillägg.

**Osäkert:** "trælbær man" (Dmv 15) och "haluo större" (Dvå 15). B–P är senare tillägg och är märkta så.

**Begrepp som saknades:** räfst, rättareting, våldgästning och dulsmål.

**Ändrat jämfört med MEL:**
- **Konungaval:** Öland, Värmland och Finland röstar nu, och Finland får egen ed på eriksgatan.
- **Edsöre:** målen avgörs direkt på häradsting av häradsnämnden i stället för på kungens räfst. Den fällde har en månad på sig att förlikas. Den som tas på färsk gärning får dödsstraff eller förlorar handen. Hemsökn utan skada kostar nu 40 marker, mot inga böter i MEL.
- **Rån:** rån för en halv mark eller mer, med gärningsmannen tagen på färsk gärning, ger dödsstraff (MEL: 40 marker).
- **Jäv:** vittneseden räknar nu upp rädsla, väld, avund, vänskap, mågskap och frändskap, och vittnena förhörs åtskilda. En nämndeman som tar muta får också 40 marker i böter. Man vädjar från häradsnämnd till lagmansnämnd och vidare till kungsnämnd.
- **Bötesdelning i Dmv** (avviker trots att delverken inte listar Dmv): dulgadråpsboten och mordgälden delas lika mellan kungen och arvingarna respektive målsäganden, mot två tredjedelar till kungen i MEL. Även boten för en fälla som inte lysts skiljer sig.

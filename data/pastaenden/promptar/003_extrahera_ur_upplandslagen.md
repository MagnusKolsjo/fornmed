# Extrahera ur Upplandslagen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/upplandslagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag:
- Lag: Upplandslagen i Schlyters utgåva (hskr A), verk-id `verk:lag:upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a`. Använd bara denna handskrift, inte hskr B.
- Läs flockarna utan balk (de innehåller prologen och kung Birgers stadfästelse 1296, som namnger lagmannen och lagkommittén; ta ut dem med `stiftar_lag`), balkarna ' Kgb ' (Kununx balkær, med edsöret) och ' Mb ' (Manhælghis balkær). Sök efter jäv-, nämnd- och tingsregler i ' Vb ' och övriga balkar med `--sok nämnd vittne frände jäv ed tylft domare`.
- Plats i varje påstående: `plats:sdhk:upland`.
- Skriv till: <projektmapp>/data/pastaenden/lagar/upplandslagen.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Filen <projektmapp>/data/pastaenden/lagar/upplandslagen.json har 162 påståenden. `pastaenden_fil.py --kontrollera` går igenom utan fel. Inget är inläst i databasen och inga andra filer är ändrade.

**Antal per ämne:** dråp ca 96, edsöre ca 42, jäv, nämnd och domare ca 16, `stiftar_lag` 8. Fördelningen är grovt räknad.

**Lästa flockar:**
- Stycke 2 (Birgers stadfästelse 1296) och stycke 3 (prologen).
- Kgb 1–12.
- Mb 1–20, 31, 46 och 47.
- Kkb 19 och 22, Kmb 11.
- Tingmålabalken. Den ligger i samma passage som `ul_vb_29`, efter Wiþærbo balkær.

**Osäkra läsningar och tolkningar:**
- "tiughum fiurum" har jag tolkat som fyra tiotal (40 mark), "tiughum attæ" som 80 och "hundræþum ok tiughum fiurum" som 140. Mb 14:s delning går jämnt upp till 140, vilket stöder tolkningen.
- Lagkommittén har elva namn, inte tolv.
- Viger spa kallas "laghæ yrkir", inte lagman.
- Tingmålabalken 9–10 är i passagen en hakparentes med text ur hskr C. Den har jag inte citerat.

**Begrepp som saknades:** kyrkan som mottagare, förverkat gods, tockabot, hållbane och fridsvittne.

**Att notera för jämförelsen:**
- Spårgälden ger 40 mark till arvingen och 13 1/3 vardera till kung och hundare. Hundragälden (140) delas mellan målsägande, länsman, kungens bord och folklandet.
- Edsöresgodset tredelas mellan målsägande, kung och "allir mæn".
- Jäv uttrycks som partskontroll: varje part råder över halva nämnden, eller båda ska säga ja till nämndemännen. Uttryckliga regler om frändskap saknas i hskr A.

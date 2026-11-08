# Normalisera övriga lagfiler

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/NORMALISERING_version_1.md](specifikationer/NORMALISERING_version_1.md)
- Utfiler: `data/pastaenden/lagar/bjarkoaratten.json`, `data/pastaenden/lagar/gragas.json`, `data/pastaenden/lagar/gutalagen.json`, `data/pastaenden/lagar/gutalagens_additamenta.json`, `data/pastaenden/lagar/kristoffers_landslag.json`, `data/pastaenden/lagar/magnus_erikssons_landslag.json`, `data/pastaenden/lagar/magnus_erikssons_stadslag.json`, `data/pastaenden/lagar/skanelagen.json`

## Uppdraget till delagenten

````text
Följ instruktionen i specifikationer/NORMALISERING_version_1.md exakt. Läs den först.

Dina filer (i <projektmapp>/data/pastaenden/lagar/): gutalagen.json, gutalagens_additamenta.json, skanelagen.json, bjarkoaratten.json, magnus_erikssons_stadslag.json, magnus_erikssons_landslag.json, kristoffers_landslag.json, gragas.json. (Grágás citeras efter dansk översättning; ändra inte citaten.)

Rör inga andra filer. Logg: <arbetsmapp>/lagpilot/normalisering_ovriga.md
````

## Delagentens slutrapport

Jag har gjort 101 byten i 5 av de 8 filerna. Alla 8 filerna går igenom `--kontrollera` utan fel. Inget är inläst i databasen. Bara subjekt och objekt har ändrats, och ingen dubblett uppstod.

**Per fil:**
- kristoffers_landslag 41
- magnus_erikssons_landslag 37
- skanelagen 13
- bjarkoaratten 6
- gutalagen 4
- gutalagens_additamenta, magnus_erikssons_stadslag och gragas 0. Grágás använde redan de nya begreppen.

**Per begrepp:** forverkat_gods 17, tvebot 17, forsat 10, kungsnamnd 10, dulgadrap 9, mordgald 7, radsbane 6, losker_man 6, jarnbord 5, fridsbrott 4, fridsbon 4, hallbane 2, kyrka 2, fiendskap 1, rafst 1.

**De viktigaste osäkra fallen:**
- **Halsbane:** jag har läst det som hållbane och bytt i två påståenden (MEL dmv_22, KrL dmv_21). Båda bör prövas.
- **Den biltoges gods (MEL eb_43, KrL eb_33):** godset förvaltas och överskottet går till fattiga och kyrka. Det är inte entydigt förverkande, så jag lät `fredloshet` stå kvar.
- **Jäv mot kungsnämnden (MEL kgb_32, KrL kgb_36):** objektet är `namnd`, och `kungsnamnd` är inte tillåtet som objekt i `diskvalificerar`. Grunden "vänskap, fejd, avund" är blandad, så `jav` står kvar.
- **Gutalagen gl_8:** dråp i kyrka och i fristad är troligen fridsbrott, men citaten nämner inte frid. Inte ändrat.
- **Fridsbönen:** där den står ihop med sårböter eller sköfling, eller där räfst står som alternativ till landsting, har jag inte bytt.

Loggen har hela ändringstabellen och alla osäkra fall: <arbetsmapp>/lagpilot/normalisering_ovriga.md

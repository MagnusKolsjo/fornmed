# Normalisera Svealands lagfiler

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/NORMALISERING_version_1.md](specifikationer/NORMALISERING_version_1.md)
- Utfiler: `data/pastaenden/lagar/dalalagen.json`, `data/pastaenden/lagar/halsingelagen.json`, `data/pastaenden/lagar/sodermannalagen.json`, `data/pastaenden/lagar/upplandslagen.json`, `data/pastaenden/lagar/upplandslagen_hskr_b.json`, `data/pastaenden/lagar/upplandslagen_tillagg.json`, `data/pastaenden/lagar/yngre_vastmannalagen.json`

## Uppdraget till delagenten

````text
Följ instruktionen i specifikationer/NORMALISERING_version_1.md exakt. Läs den först.

Dina filer (i <projektmapp>/data/pastaenden/lagar/): upplandslagen.json, upplandslagen_hskr_b.json, upplandslagen_tillagg.json, sodermannalagen.json, dalalagen.json, yngre_vastmannalagen.json, halsingelagen.json.

Rör inga andra filer. Logg: <arbetsmapp>/lagpilot/normalisering_svealand.md
````

## Delagentens slutrapport

Jag har ändrat 104 påståenden i de sju filerna. Alla klarar `--kontrollera`. Jag ändrade bara subjekt och objekt. Ett skript jämförde mot säkerhetskopian och bekräftade att passage, predikat, plats, citat och anmärkning är oförändrade, att texten efter `|` står kvar och att antalet påståenden är detsamma. Inget är inläst i databasen.

**Per fil:**
| fil | ändringar |
|---|---|
| upplandslagen | 26 |
| upplandslagen_hskr_b | 12 |
| upplandslagen_tillagg | 3 |
| sodermannalagen | 41 |
| dalalagen | 11 |
| yngre_vastmannalagen | 4 |
| halsingelagen | 7 |

**Per begrepp:** forverkat_gods 30, tvebot 18, dulgadrap 11, tockabot 11, trebot 11, sporgald 10, forsat 9, mordgald 2, hallbane 2, radsbane 2, tral 1, losker_man 1. Ett påstående som fick både nytt subjekt och nytt objekt räknas två gånger, så summan blir 108.

**De viktigaste fallen jag lät bli:**
- Arvingarna både skiftar boet och tar böterna (UL och hskr B, Kgb 5). Där står `boter` kvar.
- Dulgadråpsboten som tillfaller kungen (UL Kgb 3, DL Mb 5). Subjektet är boten, inte brottet, så jag bytte inte till `dulgadrap`.
- Dråp i ledungen med böter "fore friþ brut" (UL och SdmL Kgb 11). Det är oklart om subjektet ska vara `fridsbrott`.
- Påståenden som blandar bötesformer eller banemän, till exempel tvebot och spårgäld i samma påstående, eller flera banemän tillsammans (SdmL Mb 24, HL Mb 38).
- Mordgäld där ordet inte står i texten (HL Mb 5).
- Jäv med blandade grunder (SdmL Tb 9, YVmL Tb 17).
- Hundragäld, som saknar eget begrepp.

Säkerhetskopior av originalen ligger i <arbetsmapp>/lagpilot/norm_sv/backup/.

Logg: <arbetsmapp>/lagpilot/normalisering_svealand.md

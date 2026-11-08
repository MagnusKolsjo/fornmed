# Extrahera ur Upplandslagen hskr B

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/upplandslagen_hskr_b.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt. Läs den först.

Uppdrag:
- Lag: Upplandslagen enligt Codex Holm B 199 (Schlyters hskr B), verk-id `verk:lag:upplandslagen_enligt_codex_holm_b_199_schlyters_hskr_b`. Det är en andra handskrift av samma lag som redan tagits ut ur hskr A. Gör en självständig extraktion ur hskr B i samma delar: flockarna utan balk (prolog, stadfästelse), ' Kgb ' (edsöret), ' Mb ' (manhelgdsbalken) och tingmålabalken (sök med `--sok nämnd vittne frände jäv ed tylft domare` i ' Vb ').
- Läs inte filen för hskr A (data/pastaenden/lagar/upplandslagen.json); extraktionen ska vara oberoende av den.
- Plats: `plats:sdhk:upland`.
- Fil: <projektmapp>/data/pastaenden/lagar/upplandslagen_hskr_b.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Filen <projektmapp>/data/pastaenden/lagar/upplandslagen_hskr_b.json är skriven. Den har 98 påståenden och `pastaenden_fil.py --kontrollera` ger inga fel. Varje citat har kontrollerats maskinellt mot passagetexten. Inget är inläst i databasen och inga andra filer är ändrade. Filen för hskr A har jag inte läst.

**Antal per ämne:** dråp 46 (varav 5 nämndbevis i Mb), edsöre 32, jäv och oväld 17, stiftar_lag 3.

**Lästa flockar:**
- Prologen. Den ligger i passagen `innehallsforteckning`.
- Kgb 1–12.
- Mb 1–54. Påståenden finns ur Mb 1–6, 15–20, 25, 31, 32 och 46.
- Tingmålabalken. Den ligger inte i en egen balk utan inne i passagen `vb_29`. Sökningen `--sok` i ' Vb ' träffar därför bara Viderbobalken förutom den passagen.

**Osäkert:**
- I utgåvan är slutet av Mb 6 till början av Mb 15 supplerat ur hskr C. Där står bland annat sporgiæld, tvebot, hundragäld och hur den delas. Den delen har jag inte tagit ut.
- Hskr B har ingen stadfästelse. Prologen säger att kung Birger Magnusson "sænder" lagboken.
- 'allir mæn' i Kgb 9 har jag satt till `begrepp:landskap`.
- Läsningen 'næmpd giøræ wæræ' (nämnden har gjort fel) är osäker.

**Begrepp som saknades:** tackbot, spårgäld, herre som mottagare och hysande av fredlös.

**Att jämföra:** hskr B har inga jävsregler om frändskap eller mutor. Ovälden ligger i att vardera parten råder över halva nämnden och att båda måste godta nämndemännen. Vittnen ska vara fria, bofasta män från hundaret. Det förverkade godet vid edsöre delas på målsäganden, kungen och "allir mæn".

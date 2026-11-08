# Extrahera ur Gutalagen och Skånelagen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/gutalagen.json`, `data/pastaenden/lagar/skanelagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag: två lagar, en fil per lag. Lagarna saknar balkindelning i adressen, så hitta de relevanta flockarna med `--sok`, t.ex. `--sok dråp dräp mansbot bot ogild vådadråp fredlös edsöre nämnd vittne frände jäv ed tylft domare`, och läs flockarnas fornsvenska text.
1. Gutalagen, verk-id `verk:lag:gutalagen_enligt_holm_b_64`. Plats: `plats:gotland`. Fil: <projektmapp>/data/pastaenden/lagar/gutalagen.json. (Gotland hade allting och tredingar; använd `begrepp:ting` med värde, t.ex. `begrepp:ting|gutnalting`, när lagen nämner dem.)
2. Skånelagen, verk-id `verk:lag:skanelagen_enligt_holm_b_76`. Plats: `plats:skane`. Fil: <projektmapp>/data/pastaenden/lagar/skanelagen.json

Kontrollera varje fil med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med en sammanfattning enligt specifikationen för varje lag (högst 200 ord per lag).
````

## Delagentens slutrapport

Båda filerna är klara och `pastaenden_fil.py --kontrollera` ger inga fel för någon av dem. Inget är inläst i databasen och inga andra filer är ändrade.

**Gutalagen** (55 påståenden): <projektmapp>/data/pastaenden/lagar/gutalagen.json
- Per ämne: dråp 50, edsöre 5 (hemfrid/hemsökn, GL 12), jäv 0, stiftar_lag 0 (lagen nämner ingen stiftare).
- Lästa flockar: stycke 4 och GL 2, 8–18, 22, 28, 31, 32, 37, 38, 50, 51.
- Osäkra läsningar: "banda haldr" i GL 9 har jag tolkat som fridskretsens skydd, inte som bojor. "crafar vereldi" i GL 17 har en oklar inledning. "a þing firi alla lyþi" och "land" har jag tolkat som `begrepp:ting|gutnalting`.
- Saknade begrepp: prost, fridskrets (bandu), fristad.
- Att jämföra: Gutalagen har inget edsöre och ingen kungsrätt. I stället finns fridskretsar (mansfrid, allas frid, tingsfrid, hemfrid), och boten går till landet, sockenmännen, kyrkan och prästen. Lagen skiljer i mansboten mellan gute (tre marker guld) och icke-gute (tio marker silver). Den har inga jävsregler; edgärden ska bara vara jämbördig ("iem burnir").

**Skånelagen** (83 påståenden): <projektmapp>/data/pastaenden/lagar/skanelagen.json
- Per ämne: dråp 53, edsöre 16, jäv och nämnd 12, stiftar_lag 2.
- Edsöre har jag tolkat in: lagen säger aldrig edsöre. De 16 avser fyrtiomarksbrotten härverk (SkL 86, 87, 207) och kungens närvarofrid (SkL 89–90). De två stiftar_lag-påståendena gäller enskilda bestämmelser som en icke namngiven kung stadgat (SkL 84, 99), inte hela lagen.
- Lästa flockar: SkL 71, 84–124, 135, 138, 139, 141, 142, 145, 162, 163, 166, 204, 205, 207.
- Osäkra läsningar: "lotæ wætte" (tio män utsedda genom lott?) i SkL 105, "scra" i SkL 118 och ömsesidigheten i ättebot i SkL 91.
- Saknade begrepp: järnbörd, fiendskap, trygd, förverkat gods.
- Att jämföra: dråpsboten bärs av ätten enligt en halveringsskala, med kungens motivering i SkL 84. Jäv motiveras med ovänskap: den anklagade får underkänna högst tre nämndemän. Ederna utesluter gods, vänskap och avund. Edsmännen ska äga minst sex marker, och skälet anges uttryckligen (SkL 118). Jämnadseden svärs däremot med tolv män ur dråparens egen släkt.

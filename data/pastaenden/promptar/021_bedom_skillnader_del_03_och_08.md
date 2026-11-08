# Bedöm skillnader del 03 och 08

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: –
- Utfiler: `oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_03.json`, `oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_08.json`

## Uppdraget till delagenten

````text
Läs och följ <projektmapp>/oberoende_extraktion/jamforelse_lagar_hela/BEDOMNING.md. Dina delar: del_03 och del_08 (NN = 03 respektive 08), var och en för sig. Bedöm varje skillnad i jamforelse_del_03.json och jamforelse_del_08.json och skriv bedomning_del_03.json och bedomning_del_08.json. Svara på svenska, med sammanfattning per del.
````

## Delagentens slutrapport

Jag har bedömt alla skillnader i båda delarna och skrivit två filer: <projektmapp>/oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_03.json (215 skillnader) och .../bedomning_del_08.json (43 skillnader). Ett kontrollskript har körts. Varje id har ett tillåtet beslut, alla citat i ny_rad står ordagrant i flockens text, alla id:n finns bland kandidaterna och ingen ny rad krockar med A:s rader. Inga andra filer är ändrade och inget är inläst i databasen.

**Del 03**
- **Antal:** samma_regel 99, A_ratt 81, B_lagg_till 17, A_fel 8, B_fel 5, osaker 4, A_utanfor 1.
- **Viktigaste felen i A:**
  - ÖgL M 10: "en þæn lut taker kununger firi ensac sina" betyder att kungen tar lotten som sin ensak. A läste tvärtom, att han går miste om den.
  - Konventionerna bryts på flera ställen. Hemsökn och våldtäkt står som subjekt i stället för `drap paforljd ogild` och `edsore definieras_som`. `begrepp:arv` används för arvingar och `bonde` i stället för `landbo`.
  - A saknar konungavalet och eriksgatan i Kgb 1–2 helt. B:s rader läggs till.
- **B:s belopp är fel på två ställen:** "tiughum fiurum" är 40 mark, inte 24, och "tiughum attæ" är 80 mark, inte 28.
- **Osäkra fall:**
  - Fragmentet om edsöre i ÖgL C 6 (id 125).
  - Mb 3: om även den som kommer emellan dräps av våda (id 85).
  - Domvilla i Kkb 19 (id 201–202) är en principfråga.

**Del 08**
- **Antal:** samma_regel 16, B_lagg_till 15, A_ratt 8, A_fel 2, osaker 1, A_utanfor 1.
- **A:s fel:** Andligt släktskap står som `frandskap`, men ska ha `jav` som subjekt. Ofridshelighet står som `ogild definieras_som`, men ska vara `drap paforljd ogild`.
- **B:s tillägg:** Kvidjäv i kap. 35 (svågerskap, andligt släktskap, fattigdom, sjukdom). Godens utnämningar i kap. 24, 25 och 36. Moddomseden, egen sak och mutor i kap. 40, 42 och 44.
- **Utanför ämnena:** falska bevis på vårting.
- **Osäkert:** domare som vägrar döma (id 1), samma principfråga som domvillan i del 03.

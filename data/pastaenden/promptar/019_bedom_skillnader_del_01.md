# Bedöm skillnader del 01

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: –
- Utfiler: `oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_01.json`

## Uppdraget till delagenten

````text
Läs och följ <projektmapp>/oberoende_extraktion/jamforelse_lagar_hela/BEDOMNING.md. Din del: del_01 (NN = 01). Bedöm varje skillnad i jamforelse_del_01.json och skriv bedomning_del_01.json. Svara på svenska.
````

## Delagentens slutrapport

Del 01 är klar. Alla 258 skillnader i `<projektmapp>/oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_01.json` har fått ett beslut. Ett skript har kontrollerat att varje `ny_rad` har ordagrant citat och id:n ur kandidaterna, och att ingen nyckel dubbleras.

**Antal per beslut**

| beslut | antal |
|---|---|
| samma_regel | 153 |
| A_ratt | 58 |
| B_lagg_till | 37 |
| A_fel | 7 |
| osaker | 2 |
| B_fel | 1 |

**Viktigaste felen i A**
- Fem ogilda dödanden har fel subjekt (hor, hemsokn, stold, ran, ogild) i stället för `begrepp:drap`.
- Magnus Ladulås står som stiftare, men han nämns inte vid namn i Vidhemspr. 5. Rättat till `begrepp:kung`.
- Träl och fredlös stod som värde på en `begrepp:jav`-rad i stället för som egna subjekt.
- A saknar helt konungavalet (Rlb stycke 9), lagmanslängden (Lum, Alli, Eskil, Folke), Hednalagen-kommentaren och flera regler som A bara nämnt i anmärkningar.

**osaker**
- #19, Lydek. Rb 15: oklart om utlänningen som angriper en inländsk man för en förlikt sak hör till ogilt dödande.
- #37, YVgL Ob 1 §5: "Miþir" kan betyda lemlästa snarare än mörda.

# Översätt uppdrag 1 (Erikskrönikan)

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/kronikor/erikskronikan__0-142.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/sagaprompt.py 1
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:erikskronikan, passagerna 0–141 i ordning (79864 tecken) → data/oversattningar/kronikor/erikskronikan__0-142.json
  hämta: python hjalpskript/kalltext.py verk:erikskronikan --fran 0 --till 142 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/kronikor/erikskronikan__0-142.json verk:erikskronikan 0 142

SÄRSKILT FÖR FORNSVENSKA:
- Rimkrönikorna (Erikskrönikan, Karlskrönikan) har en versrad per rad. Översätt rad för rad till modern svenska prosa i versradens form: samma antal rader, samma radbrytningar, inget rim, inga sammanslagna rader.
- Konungastyrelsen och Prosaiska krönikan är prosa; behåll styckeindelningen.
- Kungar och kända personer i vedertagen svensk form (Magnus Ladulås, Birger Magnusson, hertig Erik, Karl Knutsson, Engelbrekt, drottning Margareta); orter i nutida form när identifieringen är entydig (Nyköping, Stockholm, Kalmar), annars textens form.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/saga_01/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

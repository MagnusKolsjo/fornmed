# Latin uppdrag 53

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/olaus_magnus/olaus_magnus__705-735.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/latinprompt.py 53
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter latinska medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, centrala fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text, och namnregeln (städer/biskopsstäder, länder och större floder i nutida namn; byar, gods, borgar, områden, mindre floder och folk i textens form; vedertagna svenska former går före, t.ex. Birka, Hedeby, Slesvig, Uppsala, svear, goter, daner, franker, sachsare, vender).

DITT JOBB:
- verk:olaus_magnus, passagerna 705–734 i ordning (79415 tecken) → data/oversattningar/olaus_magnus/olaus_magnus__705-735.json
  hämta: python hjalpskript/kalltext.py verk:olaus_magnus --fran 705 --till 735 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/olaus_magnus/olaus_magnus__705-735.json verk:olaus_magnus 705 735

SÄRSKILT FÖR DESSA TEXTER:
- Texterna är OCR av tryckta utgåvor (MGH, Storm 1880, Olaus Magnus 1555). OCR-fel i enstaka ord tolkas efter sammanhanget; är tolkningen osäker, sätt [osäker tolkning].
- Utgivarens fotnoter, textkritiska apparat (handskriftssiglor, varianter, tyska eller danska kommentarer, radnummer, sidhuvuden) ingår ibland i passagetexten. De översätts INTE och utelämnas; översätt bara den latinska källtexten. Olaus Magnus marginalanteckningar (korta stickord eller källnamn inne i raderna) är författarens egna: återge dem kort inom hakparentes där de står, t.ex. [I marginalen: Jordanes].
- Thietmars passager kan innehålla samma stycke två gånger, i Dresden- och Corveyversionen (utgåvan trycker dem på motstående sidor). Översätt allt som står, i den ordning det står.
- Nortmanni/Normanni översätts 'nordmän' (inte normander, som avser Normandies invånare); Dani 'daner'.
- Annalernas årtal står kvar som i texten (romerska tal skrivs om till arabiska siffror).
- Kungar och kejsare i vedertagen svensk form (Karl den store, Ludvig den fromme, Lothar, Otto den store, Harald Blåtand, Knut den store, Olav Tryggvason, Olav den helige); andra personer i textens latinska form utan böjning (nominativ), t.ex. Godofridus kan skrivas Godfred eftersom formen är vedertagen, men mindre kända personer behålls (Horic, Heriold).
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i samma katalog), läs dem och använd samma namnformer.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/latin_53/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än utfilen ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager; läs in befintlig fil först och översätt bara id som saknas.
- Kör kontrollera-kommandot när du är klar; det ska ge OK utan saknade, extra eller tomma id. Låg längdkvot är väntad där apparat utelämnats; kvoter under 0,6 ska förklaras i rapporten.

Avsluta med en kort rapport: antal passager, kontrollens resultat, antal [osäker tolkning], ungefär hur mycket apparat som utelämnats, och namnformer du valt för återkommande personer och platser.
````

# Översätt uppdrag 62

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/ansgarii_leverne__51-90.json`, `data/oversattningar/fornsvenska/olavslegenden__0-14.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_62.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt.py 62` ur `hjalpskript/uppdrag_fornaldarsagor_legender.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:ansgarii_leverne, passagerna 51–89 i ordning (55160 tecken) → data/oversattningar/fornsvenska/ansgarii_leverne__51-90.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:ansgarii_leverne --fran 51 --till 90 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/ansgarii_leverne__51-90.json verk:fsv:ansgarii_leverne 51 90
- verk:fsv:olavslegenden, passagerna 0–13 i ordning (14432 tecken) → data/oversattningar/fornsvenska/olavslegenden__0-14.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:olavslegenden --fran 0 --till 14 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/olavslegenden__0-14.json verk:fsv:olavslegenden 0 14

SÄRSKILT FÖR FORNSVENSKA:
- Texterna är prosa (legender och uppenbarelser); behåll styckeindelningen.
- Helgon, kungar och kyrkans män i vedertagen svensk form: Erik den helige, Olav den helige, Sigfrid, Ansgar, Rimbert, Birgitta, Katarina, Magnus jarl, biskop Henrik, Kristus, jungfru Maria, påven. Orter i nutida form när identifieringen är entydig (Uppsala, Birka, Sigtuna, Växjö, Vadstena, Rom, Orkneyöarna, Nidaros), annars textens form.
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion.
- Latinska inslag (rubriker, bibelcitat, böner) översätts också till svenska.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_62/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

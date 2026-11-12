# Översätt uppdrag 63

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/erikslegenden__0-6.json`, `data/oversattningar/fornsvenska/om_erik_den_helige__0-40.json`, `data/oversattningar/fornsvenska/katarina_av_sverige__51-65.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_63.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt.py 63` ur `hjalpskript/uppdrag_fornaldarsagor_legender.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:erikslegenden, passagerna 0–5 i ordning (6239 tecken) → data/oversattningar/fornsvenska/erikslegenden__0-6.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:erikslegenden --fran 0 --till 6 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/erikslegenden__0-6.json verk:fsv:erikslegenden 0 6
- verk:fsv:om_erik_den_helige, passagerna 0–39 i ordning (49037 tecken) → data/oversattningar/fornsvenska/om_erik_den_helige__0-40.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:om_erik_den_helige --fran 0 --till 40 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/om_erik_den_helige__0-40.json verk:fsv:om_erik_den_helige 0 40
- verk:fsv:katarina_av_sverige, passagerna 51–64 i ordning (19905 tecken) → data/oversattningar/fornsvenska/katarina_av_sverige__51-65.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:katarina_av_sverige --fran 51 --till 65 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/katarina_av_sverige__51-65.json verk:fsv:katarina_av_sverige 51 65

SÄRSKILT FÖR FORNSVENSKA:
- Texterna är prosa (legender och uppenbarelser); behåll styckeindelningen.
- Helgon, kungar och kyrkans män i vedertagen svensk form: Erik den helige, Olav den helige, Sigfrid, Ansgar, Rimbert, Birgitta, Katarina, Magnus jarl, biskop Henrik, Kristus, jungfru Maria, påven. Orter i nutida form när identifieringen är entydig (Uppsala, Birka, Sigtuna, Växjö, Vadstena, Rom, Orkneyöarna, Nidaros), annars textens form.
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion.
- Latinska inslag (rubriker, bibelcitat, böner) översätts också till svenska.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_63/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

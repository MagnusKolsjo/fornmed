# Översätt uppdrag 64

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/birgittas_liv__0-20.json`, `data/oversattningar/fornsvenska/sigfridslegenden__0-16.json`, `data/oversattningar/fornsvenska/birgittaautograferna__0-9.json`, `data/oversattningar/fornsvenska/magnus_jarl__0-6.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_64.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt.py 64` ur `hjalpskript/uppdrag_fornaldarsagor_legender.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:birgittas_liv, passagerna 0–19 i ordning (33869 tecken) → data/oversattningar/fornsvenska/birgittas_liv__0-20.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:birgittas_liv --fran 0 --till 20 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/birgittas_liv__0-20.json verk:fsv:birgittas_liv 0 20
- verk:fsv:sigfridslegenden, passagerna 0–15 i ordning (18162 tecken) → data/oversattningar/fornsvenska/sigfridslegenden__0-16.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:sigfridslegenden --fran 0 --till 16 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/sigfridslegenden__0-16.json verk:fsv:sigfridslegenden 0 16
- verk:fsv:birgittaautograferna, passagerna 0–8 i ordning (9889 tecken) → data/oversattningar/fornsvenska/birgittaautograferna__0-9.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:birgittaautograferna --fran 0 --till 9 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/birgittaautograferna__0-9.json verk:fsv:birgittaautograferna 0 9
- verk:fsv:magnus_jarl, passagerna 0–5 i ordning (6806 tecken) → data/oversattningar/fornsvenska/magnus_jarl__0-6.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:magnus_jarl --fran 0 --till 6 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/magnus_jarl__0-6.json verk:fsv:magnus_jarl 0 6

SÄRSKILT FÖR FORNSVENSKA:
- Texterna är prosa (legender och uppenbarelser); behåll styckeindelningen.
- Helgon, kungar och kyrkans män i vedertagen svensk form: Erik den helige, Olav den helige, Sigfrid, Ansgar, Rimbert, Birgitta, Katarina, Magnus jarl, biskop Henrik, Kristus, jungfru Maria, påven. Orter i nutida form när identifieringen är entydig (Uppsala, Birka, Sigtuna, Växjö, Vadstena, Rom, Orkneyöarna, Nidaros), annars textens form.
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion.
- Latinska inslag (rubriker, bibelcitat, böner) översätts också till svenska.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_64/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

# Översätt uppdrag 61

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/katarina_av_sverige__0-51.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_61.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt.py 61` ur `hjalpskript/uppdrag_fornaldarsagor_legender.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:katarina_av_sverige, passagerna 0–50 i ordning (70732 tecken) → data/oversattningar/fornsvenska/katarina_av_sverige__0-51.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:katarina_av_sverige --fran 0 --till 51 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/katarina_av_sverige__0-51.json verk:fsv:katarina_av_sverige 0 51

SÄRSKILT FÖR FORNSVENSKA:
- Texterna är prosa (legender och uppenbarelser); behåll styckeindelningen.
- Helgon, kungar och kyrkans män i vedertagen svensk form: Erik den helige, Olav den helige, Sigfrid, Ansgar, Rimbert, Birgitta, Katarina, Magnus jarl, biskop Henrik, Kristus, jungfru Maria, påven. Orter i nutida form när identifieringen är entydig (Uppsala, Birka, Sigtuna, Växjö, Vadstena, Rom, Orkneyöarna, Nidaros), annars textens form.
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion.
- Latinska inslag (rubriker, bibelcitat, böner) översätts också till svenska.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_61/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

## Rättat efteråt

Delagenten översatte två upprepningar i originalet bara en gång. Huvudsessionen lade in dem igen så att översättningen följer texten: i `s546` den upprepade satsen "Huru han doo ok huat tolamodh hans helga graff", i `s560` "ey annat ey annat".

# Översätt uppdrag 126

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/lakebok_2__0-43.json`, `data/oversattningar/fornsvenska/lakebok_11__0-15.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_126.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt2.py 126` ur `hjalpskript/uppdrag_fornsvenska_2.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:lakebok_2, passagerna 0–42 i ordning (49418 tecken) → data/oversattningar/fornsvenska/lakebok_2__0-43.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:lakebok_2 --fran 0 --till 43 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/lakebok_2__0-43.json verk:fsv:lakebok_2 0 43
- verk:fsv:lakebok_11, passagerna 0–14 i ordning (20022 tecken) → data/oversattningar/fornsvenska/lakebok_11__0-15.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:lakebok_11 --fran 0 --till 15 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/lakebok_11__0-15.json verk:fsv:lakebok_11 0 15

SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.
- Det är fackprosa (läkekonst, jordbruk). Växter, sjukdomar, kroppsdelar, mått och redskap får modern svensk benämning när identifieringen är säker, med originalordet inom parentes vid första förekomsten i passagen; annars textens ord följt av [osäker tolkning]. Mängder och enheter i recepten behålls (skålpund, lod, kvintin).
- Behåll receptens och kapitlens numrering och rubriker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_126/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

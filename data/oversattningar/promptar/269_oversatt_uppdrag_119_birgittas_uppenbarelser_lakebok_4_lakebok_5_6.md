# Översätt uppdrag 119

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/birgittas_uppenbarelser__1439-1459.json`, `data/oversattningar/fornsvenska/lakebok_4__0-9.json`, `data/oversattningar/fornsvenska/lakebok_5_6__0-19.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_119.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt2.py 119` ur `hjalpskript/uppdrag_fornsvenska_2.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:birgittas_uppenbarelser, passagerna 1439–1458 i ordning (28426 tecken) → data/oversattningar/fornsvenska/birgittas_uppenbarelser__1439-1459.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:birgittas_uppenbarelser --fran 1439 --till 1459 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/birgittas_uppenbarelser__1439-1459.json verk:fsv:birgittas_uppenbarelser 1439 1459
- verk:fsv:lakebok_4, passagerna 0–8 i ordning (12609 tecken) → data/oversattningar/fornsvenska/lakebok_4__0-9.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:lakebok_4 --fran 0 --till 9 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/lakebok_4__0-9.json verk:fsv:lakebok_4 0 9
- verk:fsv:lakebok_5_6, passagerna 0–18 i ordning (23664 tecken) → data/oversattningar/fornsvenska/lakebok_5_6__0-19.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:lakebok_5_6 --fran 0 --till 19 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/lakebok_5_6__0-19.json verk:fsv:lakebok_5_6 0 19

SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.
- Det är prosa; behåll styckeindelning, böckernas och kapitlens numrering och rubriker. Birgitta kallas i texten ofta "bruden" (brudhin); översätt ordet, byt inte ut det mot namnet. Guds Son, Kristus, jungfru Maria, påven, kejsaren, konung Magnus.
- Andra delar av verket översätts parallellt av andra; håll dig till formerna ovan.
- Det är fackprosa (läkekonst, jordbruk). Växter, sjukdomar, kroppsdelar, mått och redskap får modern svensk benämning när identifieringen är säker, med originalordet inom parentes vid första förekomsten i passagen; annars textens ord följt av [osäker tolkning]. Mängder och enheter i recepten behålls (skålpund, lod, kvintin).
- Behåll receptens och kapitlens numrering och rubriker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_119/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

# Översätt uppdrag 83

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/legendariet__147-191.json`, `data/oversattningar/fornsvenska/regula_salvatoris__104-118.json`, `data/oversattningar/fornsvenska/birgittas_uppenbarelser__1567-1569.json`, `data/oversattningar/fornsvenska/lakebok_benz_22__0-4.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_83.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt2.py 83` ur `hjalpskript/uppdrag_fornsvenska_2.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:legendariet, passagerna 147–190 i ordning (44483 tecken) → data/oversattningar/fornsvenska/legendariet__147-191.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:legendariet --fran 147 --till 191 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/legendariet__147-191.json verk:fsv:legendariet 147 191
- verk:fsv:regula_salvatoris, passagerna 104–117 i ordning (18718 tecken) → data/oversattningar/fornsvenska/regula_salvatoris__104-118.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:regula_salvatoris --fran 104 --till 118 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/regula_salvatoris__104-118.json verk:fsv:regula_salvatoris 104 118
- verk:fsv:birgittas_uppenbarelser, passagerna 1567–1568 i ordning (2400 tecken) → data/oversattningar/fornsvenska/birgittas_uppenbarelser__1567-1569.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:birgittas_uppenbarelser --fran 1567 --till 1569 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/birgittas_uppenbarelser__1567-1569.json verk:fsv:birgittas_uppenbarelser 1567 1569
- verk:fsv:lakebok_benz_22, passagerna 0–3 i ordning (3849 tecken) → data/oversattningar/fornsvenska/lakebok_benz_22__0-4.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:lakebok_benz_22 --fran 0 --till 4 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/lakebok_benz_22__0-4.json verk:fsv:lakebok_benz_22 0 4

SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.
- Texten är prosa; behåll styckeindelningen.
- Det är prosa; behåll styckeindelning, böckernas och kapitlens numrering och rubriker. Birgitta kallas i texten ofta "bruden" (brudhin); översätt ordet, byt inte ut det mot namnet. Guds Son, Kristus, jungfru Maria, påven, kejsaren, konung Magnus.
- Andra delar av verket översätts parallellt av andra; håll dig till formerna ovan.
- Det är fackprosa (läkekonst, jordbruk). Växter, sjukdomar, kroppsdelar, mått och redskap får modern svensk benämning när identifieringen är säker, med originalordet inom parentes vid första förekomsten i passagen; annars textens ord följt av [osäker tolkning]. Mängder och enheter i recepten behålls (skålpund, lod, kvintin).
- Behåll receptens och kapitlens numrering och rubriker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_83/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

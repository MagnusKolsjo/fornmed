# Översätt uppdrag 90

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/hertig_fredrik__118-170.json`, `data/oversattningar/fornsvenska/birgittas_uppenbarelser__1284-1297.json`, `data/oversattningar/fornsvenska/bondakonst__242-257.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_90.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt2.py 90` ur `hjalpskript/uppdrag_fornsvenska_2.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:hertig_fredrik, passagerna 118–169 i ordning (30614 tecken) → data/oversattningar/fornsvenska/hertig_fredrik__118-170.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:hertig_fredrik --fran 118 --till 170 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/hertig_fredrik__118-170.json verk:fsv:hertig_fredrik 118 170
- verk:fsv:birgittas_uppenbarelser, passagerna 1284–1296 i ordning (18797 tecken) → data/oversattningar/fornsvenska/birgittas_uppenbarelser__1284-1297.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:birgittas_uppenbarelser --fran 1284 --till 1297 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/birgittas_uppenbarelser__1284-1297.json verk:fsv:birgittas_uppenbarelser 1284 1297
- verk:fsv:bondakonst, passagerna 242–256 i ordning (16658 tecken) → data/oversattningar/fornsvenska/bondakonst__242-257.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:bondakonst --fran 242 --till 257 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/bondakonst__242-257.json verk:fsv:bondakonst 242 257

SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.
- Texten är vers med en versrad per rad. Översätt rad för rad till modern svensk prosa i versradens form: samma antal rader, samma radbrytningar, inget rim, inga sammanslagna rader.
- Personer i textens form (Ivan, Gawian, Lunet, Fredrik, Flores, Blanzeflor); kung Artur och drottning Eufemia i vedertagen form.
- Det är prosa; behåll styckeindelning, böckernas och kapitlens numrering och rubriker. Birgitta kallas i texten ofta "bruden" (brudhin); översätt ordet, byt inte ut det mot namnet. Guds Son, Kristus, jungfru Maria, påven, kejsaren, konung Magnus.
- Andra delar av verket översätts parallellt av andra; håll dig till formerna ovan.
- Det är fackprosa (läkekonst, jordbruk). Växter, sjukdomar, kroppsdelar, mått och redskap får modern svensk benämning när identifieringen är säker, med originalordet inom parentes vid första förekomsten i passagen; annars textens ord följt av [osäker tolkning]. Mängder och enheter i recepten behålls (skålpund, lod, kvintin).
- Behåll receptens och kapitlens numrering och rubriker.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_90/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

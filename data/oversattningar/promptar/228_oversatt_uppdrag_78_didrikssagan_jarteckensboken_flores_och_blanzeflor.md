# Översätt uppdrag 78

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/didrikssagan__165-205.json`, `data/oversattningar/fornsvenska/jarteckensboken__112-126.json`, `data/oversattningar/fornsvenska/flores_och_blanzeflor__138-141.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_78.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt2.py 78` ur `hjalpskript/uppdrag_fornsvenska_2.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:didrikssagan, passagerna 165–204 i ordning (50903 tecken) → data/oversattningar/fornsvenska/didrikssagan__165-205.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:didrikssagan --fran 165 --till 205 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/didrikssagan__165-205.json verk:fsv:didrikssagan 165 205
- verk:fsv:jarteckensboken, passagerna 112–125 i ordning (18241 tecken) → data/oversattningar/fornsvenska/jarteckensboken__112-126.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:jarteckensboken --fran 112 --till 126 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/jarteckensboken__112-126.json verk:fsv:jarteckensboken 112 126
- verk:fsv:flores_och_blanzeflor, passagerna 138–140 i ordning (1744 tecken) → data/oversattningar/fornsvenska/flores_och_blanzeflor__138-141.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:flores_och_blanzeflor --fran 138 --till 141 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/flores_och_blanzeflor__138-141.json verk:fsv:flores_och_blanzeflor 138 141

SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.
- Det är prosa; behåll styckeindelningen. Personerna i den form fornsvenska Didrikssagan har dem, enhetligt: Didrik av Bern, Hildebrand, Vidrik Verlandsson, Sigurd, Gunnar, Högne, Grimhild, Brynhild, Attila, Ermenrik, Sifka; andra i textens form.
- Andra delar av verket översätts parallellt av andra; håll dig därför till formerna ovan och till textens form.
- Texten är prosa; behåll styckeindelningen.
- Texten är vers med en versrad per rad. Översätt rad för rad till modern svensk prosa i versradens form: samma antal rader, samma radbrytningar, inget rim, inga sammanslagna rader.
- Personer i textens form (Ivan, Gawian, Lunet, Fredrik, Flores, Blanzeflor); kung Artur och drottning Eufemia i vedertagen form.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_78/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

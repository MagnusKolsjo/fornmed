# Översätt uppdrag 91

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/fornsvenska/flores_och_blanzeflor__0-138.json`

## Uppdraget till delagenten

````text
Läs filen <arbetsmapp>/prompt_91.txt och följ exakt instruktionen i den; den är ditt uppdrag.
````

## Instruktionen i uppdragsfilen

Filen skrevs av `hjalpskript/uppdragsprompt2.py 91` ur `hjalpskript/uppdrag_fornsvenska_2.json`.

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
- verk:fsv:flores_och_blanzeflor, passagerna 0–137 i ordning (71682 tecken) → data/oversattningar/fornsvenska/flores_och_blanzeflor__0-138.json
  hämta: python <arbetsmapp>/kalltext.py verk:fsv:flores_och_blanzeflor --fran 0 --till 138 --typer originaltext
  kontrollera: python <arbetsmapp>/kontrollera_oversattning.py data/oversattningar/fornsvenska/flores_och_blanzeflor__0-138.json verk:fsv:flores_och_blanzeflor 0 138

SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker.
- Texten är vers med en versrad per rad. Översätt rad för rad till modern svensk prosa i versradens form: samma antal rader, samma radbrytningar, inget rim, inga sammanslagna rader.
- Personer i textens form (Ivan, Gawian, Lunet, Fredrik, Flores, Blanzeflor); kung Artur och drottning Eufemia i vedertagen form.

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen <arbetsmapp>/jobb_91/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

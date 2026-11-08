# Översätt uppdrag 57

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/sagor/atla_saga_otryggssonar__0-15.json`, `data/oversattningar/sagor/gisls_thattr_illugasonar__0-5.json`, `data/oversattningar/sagor/jokuls_thattr_buasonar__0-3.json`, `data/oversattningar/sagor/thorgrims_thattr_hallasonar_ok_bjarna_gullbrarskalds__0-3.json`, `data/oversattningar/sagor/vodu_brands_thattr__0-5.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/sagaprompt.py 57
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornvästnordiska):
- verk:saga:atla_saga_otryggssonar, passagerna 0–14 i ordning (24903 tecken) → data/oversattningar/sagor/atla_saga_otryggssonar__0-15.json
  hämta: python hjalpskript/kalltext.py verk:saga:atla_saga_otryggssonar --fran 0 --till 15 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/atla_saga_otryggssonar__0-15.json verk:saga:atla_saga_otryggssonar 0 15
- verk:saga:vodu_brands_thattr, passagerna 0–4 i ordning (19634 tecken) → data/oversattningar/sagor/vodu_brands_thattr__0-5.json
  hämta: python hjalpskript/kalltext.py verk:saga:vodu_brands_thattr --fran 0 --till 5 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/vodu_brands_thattr__0-5.json verk:saga:vodu_brands_thattr 0 5
- verk:saga:jokuls_thattr_buasonar, passagerna 0–2 i ordning (19033 tecken) → data/oversattningar/sagor/jokuls_thattr_buasonar__0-3.json
  hämta: python hjalpskript/kalltext.py verk:saga:jokuls_thattr_buasonar --fran 0 --till 3 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/jokuls_thattr_buasonar__0-3.json verk:saga:jokuls_thattr_buasonar 0 3
- verk:saga:gisls_thattr_illugasonar, passagerna 0–4 i ordning (14142 tecken) → data/oversattningar/sagor/gisls_thattr_illugasonar__0-5.json
  hämta: python hjalpskript/kalltext.py verk:saga:gisls_thattr_illugasonar --fran 0 --till 5 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/gisls_thattr_illugasonar__0-5.json verk:saga:gisls_thattr_illugasonar 0 5
- verk:saga:thorgrims_thattr_hallasonar_ok_bjarna_gullbrarskalds, passagerna 0–2 i ordning (7226 tecken) → data/oversattningar/sagor/thorgrims_thattr_hallasonar_ok_bjarna_gullbrarskalds__0-3.json
  hämta: python hjalpskript/kalltext.py verk:saga:thorgrims_thattr_hallasonar_ok_bjarna_gullbrarskalds --fran 0 --till 3 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thorgrims_thattr_hallasonar_ok_bjarna_gullbrarskalds__0-3.json verk:saga:thorgrims_thattr_hallasonar_ok_bjarna_gullbrarskalds 0 3

SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Uppsala, Nidaros, Konstantinopel); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/saga_57/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller kronikor/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

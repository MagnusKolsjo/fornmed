# Översätt uppdrag 55

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/sagor/hemings_thattr_aslakssonar__0-15.json`, `data/oversattningar/sagor/hrafns_thattr_gudrunarsonar__0-6.json`, `data/oversattningar/sagor/thorsteins_saga_sidu_hallssonar__0-7.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/sagaprompt.py 55
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornvästnordiska):
- verk:saga:hemings_thattr_aslakssonar, passagerna 0–14 i ordning (32220 tecken) → data/oversattningar/sagor/hemings_thattr_aslakssonar__0-15.json
  hämta: python hjalpskript/kalltext.py verk:saga:hemings_thattr_aslakssonar --fran 0 --till 15 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/hemings_thattr_aslakssonar__0-15.json verk:saga:hemings_thattr_aslakssonar 0 15
- verk:saga:thorsteins_saga_sidu_hallssonar, passagerna 0–6 i ordning (29320 tecken) → data/oversattningar/sagor/thorsteins_saga_sidu_hallssonar__0-7.json
  hämta: python hjalpskript/kalltext.py verk:saga:thorsteins_saga_sidu_hallssonar --fran 0 --till 7 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thorsteins_saga_sidu_hallssonar__0-7.json verk:saga:thorsteins_saga_sidu_hallssonar 0 7
- verk:saga:hrafns_thattr_gudrunarsonar, passagerna 0–5 i ordning (22459 tecken) → data/oversattningar/sagor/hrafns_thattr_gudrunarsonar__0-6.json
  hämta: python hjalpskript/kalltext.py verk:saga:hrafns_thattr_gudrunarsonar --fran 0 --till 6 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/hrafns_thattr_gudrunarsonar__0-6.json verk:saga:hrafns_thattr_gudrunarsonar 0 6

SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Uppsala, Nidaros, Konstantinopel); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/saga_55/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller kronikor/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

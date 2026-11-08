# Översätt uppdrag 51

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/sagor/aevi_snorra_goda__0-1.json`, `data/oversattningar/sagor/gunnars_saga_keldugnupsfifls__0-10.json`, `data/oversattningar/sagor/morkinskinna__182-196.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/sagaprompt.py 51
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornvästnordiska):
- verk:morkinskinna, passagerna 182–195 i ordning (43039 tecken) → data/oversattningar/sagor/morkinskinna__182-196.json
  hämta: python hjalpskript/kalltext.py verk:morkinskinna --fran 182 --till 196 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/morkinskinna__182-196.json verk:morkinskinna 182 196
- verk:saga:gunnars_saga_keldugnupsfifls, passagerna 0–9 i ordning (39196 tecken) → data/oversattningar/sagor/gunnars_saga_keldugnupsfifls__0-10.json
  hämta: python hjalpskript/kalltext.py verk:saga:gunnars_saga_keldugnupsfifls --fran 0 --till 10 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/gunnars_saga_keldugnupsfifls__0-10.json verk:saga:gunnars_saga_keldugnupsfifls 0 10
- verk:saga:aevi_snorra_goda, passagerna 0–0 i ordning (1953 tecken) → data/oversattningar/sagor/aevi_snorra_goda__0-1.json
  hämta: python hjalpskript/kalltext.py verk:saga:aevi_snorra_goda --fran 0 --till 1 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/aevi_snorra_goda__0-1.json verk:saga:aevi_snorra_goda 0 1

SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Uppsala, Nidaros, Konstantinopel); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/saga_51/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller kronikor/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

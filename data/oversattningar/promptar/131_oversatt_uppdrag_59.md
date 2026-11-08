# Översätt uppdrag 59

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/sagor/agrip_jokuldaela_sogu__0-2.json`, `data/oversattningar/sagor/grims_thattr_grimstungu__0-3.json`, `data/oversattningar/sagor/islendings_thattr_oradga__0-3.json`, `data/oversattningar/sagor/ivars_thattr_ingimundarsonar__0-2.json`, `data/oversattningar/sagor/mana_thattr_skalds__0-1.json`, `data/oversattningar/sagor/ottars_thattr_svarta__0-1.json`, `data/oversattningar/sagor/sorla_thattr__0-2.json`, `data/oversattningar/sagor/stefnis_thattr_thorgilssonar__0-5.json`, `data/oversattningar/sagor/thorarins_thattr_ofsa__0-2.json`, `data/oversattningar/sagor/thorarins_thattr_stuttfeldar__0-2.json`, `data/oversattningar/sagor/thorsteins_thattr_forvitna__0-1.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/sagaprompt.py 59
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornvästnordiska):
- verk:saga:islendings_thattr_oradga, passagerna 0–2 i ordning (6169 tecken) → data/oversattningar/sagor/islendings_thattr_oradga__0-3.json
  hämta: python hjalpskript/kalltext.py verk:saga:islendings_thattr_oradga --fran 0 --till 3 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/islendings_thattr_oradga__0-3.json verk:saga:islendings_thattr_oradga 0 3
- verk:saga:stefnis_thattr_thorgilssonar, passagerna 0–4 i ordning (5922 tecken) → data/oversattningar/sagor/stefnis_thattr_thorgilssonar__0-5.json
  hämta: python hjalpskript/kalltext.py verk:saga:stefnis_thattr_thorgilssonar --fran 0 --till 5 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/stefnis_thattr_thorgilssonar__0-5.json verk:saga:stefnis_thattr_thorgilssonar 0 5
- verk:saga:thorarins_thattr_ofsa, passagerna 0–1 i ordning (5182 tecken) → data/oversattningar/sagor/thorarins_thattr_ofsa__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:thorarins_thattr_ofsa --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thorarins_thattr_ofsa__0-2.json verk:saga:thorarins_thattr_ofsa 0 2
- verk:saga:sorla_thattr, passagerna 0–1 i ordning (5170 tecken) → data/oversattningar/sagor/sorla_thattr__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:sorla_thattr --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/sorla_thattr__0-2.json verk:saga:sorla_thattr 0 2
- verk:saga:grims_thattr_grimstungu, passagerna 0–2 i ordning (4592 tecken) → data/oversattningar/sagor/grims_thattr_grimstungu__0-3.json
  hämta: python hjalpskript/kalltext.py verk:saga:grims_thattr_grimstungu --fran 0 --till 3 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/grims_thattr_grimstungu__0-3.json verk:saga:grims_thattr_grimstungu 0 3
- verk:saga:ivars_thattr_ingimundarsonar, passagerna 0–1 i ordning (4355 tecken) → data/oversattningar/sagor/ivars_thattr_ingimundarsonar__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:ivars_thattr_ingimundarsonar --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/ivars_thattr_ingimundarsonar__0-2.json verk:saga:ivars_thattr_ingimundarsonar 0 2
- verk:saga:thorarins_thattr_stuttfeldar, passagerna 0–1 i ordning (4162 tecken) → data/oversattningar/sagor/thorarins_thattr_stuttfeldar__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:thorarins_thattr_stuttfeldar --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thorarins_thattr_stuttfeldar__0-2.json verk:saga:thorarins_thattr_stuttfeldar 0 2
- verk:saga:agrip_jokuldaela_sogu, passagerna 0–1 i ordning (4072 tecken) → data/oversattningar/sagor/agrip_jokuldaela_sogu__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:agrip_jokuldaela_sogu --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/agrip_jokuldaela_sogu__0-2.json verk:saga:agrip_jokuldaela_sogu 0 2
- verk:saga:thorsteins_thattr_forvitna, passagerna 0–0 i ordning (3484 tecken) → data/oversattningar/sagor/thorsteins_thattr_forvitna__0-1.json
  hämta: python hjalpskript/kalltext.py verk:saga:thorsteins_thattr_forvitna --fran 0 --till 1 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thorsteins_thattr_forvitna__0-1.json verk:saga:thorsteins_thattr_forvitna 0 1
- verk:saga:ottars_thattr_svarta, passagerna 0–0 i ordning (3437 tecken) → data/oversattningar/sagor/ottars_thattr_svarta__0-1.json
  hämta: python hjalpskript/kalltext.py verk:saga:ottars_thattr_svarta --fran 0 --till 1 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/ottars_thattr_svarta__0-1.json verk:saga:ottars_thattr_svarta 0 1
- verk:saga:mana_thattr_skalds, passagerna 0–0 i ordning (2864 tecken) → data/oversattningar/sagor/mana_thattr_skalds__0-1.json
  hämta: python hjalpskript/kalltext.py verk:saga:mana_thattr_skalds --fran 0 --till 1 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/mana_thattr_skalds__0-1.json verk:saga:mana_thattr_skalds 0 1

SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Uppsala, Nidaros, Konstantinopel); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/saga_59/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller kronikor/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

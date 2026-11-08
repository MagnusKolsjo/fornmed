# Översätt uppdrag 58

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/sagor/asmundar_saga_atlasonar__0-6.json`, `data/oversattningar/sagor/hardar_saga_grimkelssonar_upphaf_eldri_gerdar__0-5.json`, `data/oversattningar/sagor/hellismanna_saga__32-33.json`, `data/oversattningar/sagor/ofeigs_thattr__0-2.json`, `data/oversattningar/sagor/stufs_thattr_inn_meiri__0-3.json`, `data/oversattningar/sagor/thoris_thattr_hasts_ok_bardar_birtu__0-4.json`, `data/oversattningar/sagor/thormodar_thattr__0-3.json`, `data/oversattningar/sagor/thorsteins_thattr_tjaldstaedings__0-4.json`, `data/oversattningar/sagor/volsa_thattr__0-2.json`

## Uppdraget till delagenten

````text
Kör kommandot nedan och följ exakt de instruktioner det skriver ut; de är ditt uppdrag.

python3 hjalpskript/sagaprompt.py 58
````

## Instruktionen som hjälpskriptet skrev ut

````text
Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornvästnordiska):
- verk:saga:thormodar_thattr, passagerna 0–2 i ordning (12975 tecken) → data/oversattningar/sagor/thormodar_thattr__0-3.json
  hämta: python hjalpskript/kalltext.py verk:saga:thormodar_thattr --fran 0 --till 3 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thormodar_thattr__0-3.json verk:saga:thormodar_thattr 0 3
- verk:saga:asmundar_saga_atlasonar, passagerna 0–5 i ordning (12857 tecken) → data/oversattningar/sagor/asmundar_saga_atlasonar__0-6.json
  hämta: python hjalpskript/kalltext.py verk:saga:asmundar_saga_atlasonar --fran 0 --till 6 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/asmundar_saga_atlasonar__0-6.json verk:saga:asmundar_saga_atlasonar 0 6
- verk:saga:thoris_thattr_hasts_ok_bardar_birtu, passagerna 0–3 i ordning (10371 tecken) → data/oversattningar/sagor/thoris_thattr_hasts_ok_bardar_birtu__0-4.json
  hämta: python hjalpskript/kalltext.py verk:saga:thoris_thattr_hasts_ok_bardar_birtu --fran 0 --till 4 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thoris_thattr_hasts_ok_bardar_birtu__0-4.json verk:saga:thoris_thattr_hasts_ok_bardar_birtu 0 4
- verk:saga:hardar_saga_grimkelssonar_upphaf_eldri_gerdar, passagerna 0–4 i ordning (8157 tecken) → data/oversattningar/sagor/hardar_saga_grimkelssonar_upphaf_eldri_gerdar__0-5.json
  hämta: python hjalpskript/kalltext.py verk:saga:hardar_saga_grimkelssonar_upphaf_eldri_gerdar --fran 0 --till 5 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/hardar_saga_grimkelssonar_upphaf_eldri_gerdar__0-5.json verk:saga:hardar_saga_grimkelssonar_upphaf_eldri_gerdar 0 5
- verk:saga:stufs_thattr_inn_meiri, passagerna 0–2 i ordning (8149 tecken) → data/oversattningar/sagor/stufs_thattr_inn_meiri__0-3.json
  hämta: python hjalpskript/kalltext.py verk:saga:stufs_thattr_inn_meiri --fran 0 --till 3 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/stufs_thattr_inn_meiri__0-3.json verk:saga:stufs_thattr_inn_meiri 0 3
- verk:saga:thorsteins_thattr_tjaldstaedings, passagerna 0–3 i ordning (8072 tecken) → data/oversattningar/sagor/thorsteins_thattr_tjaldstaedings__0-4.json
  hämta: python hjalpskript/kalltext.py verk:saga:thorsteins_thattr_tjaldstaedings --fran 0 --till 4 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/thorsteins_thattr_tjaldstaedings__0-4.json verk:saga:thorsteins_thattr_tjaldstaedings 0 4
- verk:saga:volsa_thattr, passagerna 0–1 i ordning (7763 tecken) → data/oversattningar/sagor/volsa_thattr__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:volsa_thattr --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/volsa_thattr__0-2.json verk:saga:volsa_thattr 0 2
- verk:saga:hellismanna_saga, passagerna 32–32 i ordning (7688 tecken) → data/oversattningar/sagor/hellismanna_saga__32-33.json
  hämta: python hjalpskript/kalltext.py verk:saga:hellismanna_saga --fran 32 --till 33 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/hellismanna_saga__32-33.json verk:saga:hellismanna_saga 32 33
- verk:saga:ofeigs_thattr, passagerna 0–1 i ordning (7291 tecken) → data/oversattningar/sagor/ofeigs_thattr__0-2.json
  hämta: python hjalpskript/kalltext.py verk:saga:ofeigs_thattr --fran 0 --till 2 --typer originaltext
  kontrollera: python hjalpskript/kontrollera_oversattning.py data/oversattningar/sagor/ofeigs_thattr__0-2.json verk:saga:ofeigs_thattr 0 2

SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Uppsala, Nidaros, Konstantinopel); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker.

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen <arbetsmapp>/saga_58/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {id: {adress, sprak, text}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {originalpassagens id: svensk översättning} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller kronikor/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser.
````

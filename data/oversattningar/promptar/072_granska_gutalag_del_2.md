# Granska Gutalag del 2

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/gutniska_sv.json`

## Uppdraget till delagenten

````text
Du granskar och reviderar äldre språkmodellsöversättningar till svenska i projektet <projektmapp> så att de följer riktlinjerna i data/oversattningar/RIKTLINJER.md. Läs RIKTLINJER.md först och följ den exakt.

DITT JOBB: i data/oversattningar/gutniska_sv.json nycklarna med index 38–70 i filens ordning (33 passager ur Gutalagen enligt Säve, forngutniska).

ARBETSKATALOG: använd ENDAST <arbetsmapp>/granskning_gutniska_b/ (skapa den). Skriv inga filer någon annanstans och ändra INTE projektfilen själv.

Hämta original och nuvarande översättning med (från projektroten):
python hjalpskript/granskpar.py data/oversattningar/gutniska_sv.json --fran N --till M
(ta några passager åt gången inom 38–71). Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det, eller jämföra med de redan granskade översättningarna av textbankens Gutalag i data/oversattningar/lagar/ (filnamn med gutalag) för terminologi.

Jämför översättningen mening för mening med originalet och rätta:
- felöversättningar, utelämnade satser eller tillägg som inte står i originalet,
- egna förklaringar, identifieringar eller underförstådda subjekt i parentes/hakparentes (ta bort),
- ställen där textens läsning bytts mot en annan (återställ; markera med [osäker tolkning] om den verkar fel),
- osäkra tolkningar som saknar markering: sätt "[osäker tolkning]" efter den troligaste tolkningen där tolkningen verkligen är osäker (ovanliga ord, omstridda ställen). De äldre översättningarna saknar helt markeringar, så räkna med att några behövs, men överdriv inte,
- egennamn enligt namnregeln,
- centrala rättstermer: modern betydelse med originalordet inom parentes vid första förekomst i passagen, t.ex. "böter (bot)", "ting (þing)". Mynt- och måttenheter som mark, öre, örtug behålls.
Behåll i övrigt den befintliga översättningen; skriv inte om bra text i onödan.

Skriv resultatet inkrementellt (json.dump efter varje passage eller grupp) till granskning_gutniska_b/gutniska_b.json med exakt de 33 nycklarna, och granskning_gutniska_b/andringar.md med en rad per ändrad passage (nyckel, vad som ändrades).

Avsluta med en kort rapport: antal ändrade passager, antal tillagda [osäker tolkning], och de viktigaste sakfelen du rättade.
````

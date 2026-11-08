# Granska romerska översättningar

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/romerska_sv.json`

## Uppdraget till delagenten

````text
Du granskar och reviderar äldre språkmodellsöversättningar till svenska i projektet <projektmapp> så att de följer riktlinjerna i data/oversattningar/RIKTLINJER.md. Läs RIKTLINJER.md först och följ den exakt.

DITT JOBB: översättningsfilen data/oversattningar/romerska_sv.json, alla 56 nycklar (Tacitus Germania, Plinius, Pomponius Mela på latin; Prokopios på grekiska).

ARBETSKATALOG: använd ENDAST <arbetsmapp>/granskning_romerska/ (skapa den). Skriv inga filer någon annanstans och ändra INTE projektfilen själv.

Hämta par av original och nuvarande översättning med:
python hjalpskript/granskpar.py data/oversattningar/romerska_sv.json --fran N --till M
(kör från projektroten; ta några passager åt gången).

För varje passage: jämför översättningen mening för mening med originalet och rätta:
- felöversättningar, utelämnade satser eller tillägg som inte står i originalet,
- egna förklaringar, identifieringar eller underförstådda subjekt i parentes/hakparentes (ta bort),
- ställen där textens läsning bytts mot en annan (återställ textens läsning; markera med [osäker tolkning] om den verkar fel),
- osäkra tolkningar som saknar markering: sätt "[osäker tolkning]" efter den troligaste tolkningen där tolkningen verkligen är osäker (omstridda ställen, korrupta ställen, ovanliga ord). Överdriv inte, men de äldre översättningarna saknar helt markeringar, så räkna med att några behövs,
- egennamn enligt namnregeln (folk och mindre orter i textens form, t.ex. Suiones, Sitones, Fenni, Aestii; vedertagna svenska former där sådana finns, t.ex. svioner går bra om det är vedertaget; länder, större floder i nutida namn: Rhen, Donau, Elbe),
- fackord: originalordet inom parentes vid första förekomst i passagen när det är ett centralt fackord.
Behåll i övrigt den befintliga översättningen; skriv inte om bra text i onödan.

Skriv resultatet inkrementellt (json.dump efter varje passage eller grupp) till granskning_romerska/romerska_sv.json med EXAKT samma nycklar som originalfilen (alla 56, även oförändrade). Skriv också granskning_romerska/andringar.md med en rad per ändrad passage: nyckel och kort vad som ändrades.

Avsluta med en kort rapport: antal ändrade passager, antal tillagda [osäker tolkning], och de viktigaste sakfelen du rättade.
````

# Granska Liber monstrorum

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/liber_monstrorum_sv.json`

## Uppdraget till delagenten

````text
Du granskar och reviderar äldre språkmodellsöversättningar till svenska i projektet <projektmapp> så att de följer riktlinjerna i data/oversattningar/RIKTLINJER.md. Läs RIKTLINJER.md först och följ den exakt.

DITT JOBB: data/oversattningar/liber_monstrorum_sv.json, alla 111 nycklar (Liber monstrorum, latin; innehåller bl.a. kung Hygelac av geaterna, 1.2).

ARBETSKATALOG: använd ENDAST <arbetsmapp>/granskning_liber/ (skapa den). Skriv inga filer någon annanstans och ändra INTE projektfilen själv.

Hämta original och nuvarande översättning med (från projektroten):
python hjalpskript/granskpar.py data/oversattningar/liber_monstrorum_sv.json --fran N --till M
(ta 15–20 passager åt gången).

Jämför översättningen mening för mening med latinet och rätta:
- felöversättningar, utelämnade satser eller tillägg som inte står i originalet,
- egna förklaringar, identifieringar eller underförstådda subjekt i parentes/hakparentes (ta bort),
- ställen där textens läsning bytts mot en annan (t.ex. ett namn "rättat" till en känd form; återställ textens form och markera med [osäker tolkning] om den verkar fel),
- osäkra tolkningar som saknar markering: sätt "[osäker tolkning]" efter den troligaste tolkningen där tolkningen verkligen är osäker (ovanliga ord, korrupta ställen). De äldre översättningarna saknar helt markeringar, så räkna med att några behövs, men överdriv inte,
- egennamn enligt namnregeln: folk, mindre orter och mytologiska namn i textens form (Hyglacus, Getae), vedertagna svenska former för kända gestalter och platser (Herkules, Indien, Nilen, Rhen),
Behåll i övrigt den befintliga översättningen; skriv inte om bra text i onödan.

Skriv resultatet inkrementellt (json.dump efter varje grupp) till granskning_liber/liber_monstrorum_sv.json med exakt samma 111 nycklar (även oförändrade), och granskning_liber/andringar.md med en rad per ändrad passage (nyckel, vad som ändrades).

Avsluta med en kort rapport: antal ändrade passager, antal tillagda [osäker tolkning], och de viktigaste sakfelen du rättade.
````

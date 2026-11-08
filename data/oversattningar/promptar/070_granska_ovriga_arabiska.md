# Granska övriga arabiska

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/arabiska_sv.json`

## Uppdraget till delagenten

````text
Du granskar och reviderar äldre språkmodellsöversättningar till svenska i projektet <projektmapp> så att de följer riktlinjerna i data/oversattningar/RIKTLINJER.md. Läs RIKTLINJER.md först och följ den exakt.

DITT JOBB: i data/oversattningar/arabiska_sv.json de 13 nycklarna som INTE börjar med ibn_fadlan: ibn_khurradadhbih:1:sv, ibn_rusta:1:sv, ibn_rusta:2:sv, masudi:1:sv, masudi:2:sv, masudi:3:sv, masudi:4:sv, idrisi:1:sv, idrisi:2:sv, qazwini:1:sv, qazwini:2:sv, qazwini:3:sv, ibn_hawqal:1:sv (arabiska ur OpenITI). ibn_hawqal:1 är lång; arbeta i avsnitt.

ARBETSKATALOG: använd ENDAST <arbetsmapp>/granskning_arabiska_ovr/ (skapa den). Skriv inga filer någon annanstans och ändra INTE projektfilen själv.

Hämta original och nuvarande översättning med (från projektroten):
python hjalpskript/granskpar.py data/oversattningar/arabiska_sv.json --nycklar <kommaseparerade nycklar>

Jämför översättningen mening för mening med arabiskan och rätta:
- felöversättningar, utelämnade satser eller tillägg som inte står i originalet (kontrollera särskilt att inget hoppats över eller sammanfattats),
- egna förklaringar, identifieringar eller underförstådda subjekt i parentes/hakparentes (ta bort),
- ställen där textens läsning bytts mot en annan (återställ; markera med [osäker tolkning] om den verkar fel),
- osäkra tolkningar som saknar markering: sätt "[osäker tolkning]" efter den troligaste tolkningen där tolkningen verkligen är osäker (ovanliga ord, oklara folk- och ortnamn, korrupta ställen). De äldre översättningarna saknar helt markeringar, så räkna med att några behövs, men överdriv inte,
- egennamn enligt namnregeln: folk och orter i textens form i enkel, konsekvent translitterering (rus, saqaliba, Bulghar, Itil, Shlswq för Hedeby om texten skriver så; ersätt aldrig textens namn med en modern identifiering), vedertagna svenska former där sådana finns (Bagdad, Konstantinopel),
- fackord (titlar, mynt, mått) med originalordet translittererat inom parentes vid första förekomst i passagen.
Behåll i övrigt den befintliga översättningen; skriv inte om bra text i onödan.

Skriv resultatet inkrementellt (json.dump efter varje passage) till granskning_arabiska_ovr/arabiska_ovr.json med exakt dessa 13 nycklar, och granskning_arabiska_ovr/andringar.md med en rad per ändring (nyckel, vad som ändrades).

Avsluta med en kort rapport: antal ändrade passager, antal tillagda [osäker tolkning], och de viktigaste sakfelen eller utelämningarna du rättade.
````

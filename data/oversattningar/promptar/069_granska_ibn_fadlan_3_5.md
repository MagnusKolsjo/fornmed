# Granska Ibn Fadlan 3–5

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/arabiska_sv.json`

## Uppdraget till delagenten

````text
Du granskar och reviderar äldre språkmodellsöversättningar till svenska i projektet <projektmapp> så att de följer riktlinjerna i data/oversattningar/RIKTLINJER.md. Läs RIKTLINJER.md först och följ den exakt.

DITT JOBB: i data/oversattningar/arabiska_sv.json nycklarna ibn_fadlan:3:sv, ibn_fadlan:4:sv och ibn_fadlan:5:sv (Ibn Fadlans reseberättelse, arabiska ur OpenITI; här finns bland annat avsnittet om rus och skeppsbegravningen). Passage 3 är lång (cirka 18 000 tecken arabiska); arbeta igenom den i avsnitt.

ARBETSKATALOG: använd ENDAST <arbetsmapp>/granskning_fadlan_b/ (skapa den). Skriv inga filer någon annanstans och ändra INTE projektfilen själv.

Hämta original och nuvarande översättning med (från projektroten):
python hjalpskript/granskpar.py data/oversattningar/arabiska_sv.json --nycklar ibn_fadlan:3:sv,ibn_fadlan:4:sv,ibn_fadlan:5:sv
Spara gärna utdata i din arbetskatalog och läs den i delar.

Jämför översättningen mening för mening med arabiskan och rätta:
- felöversättningar, utelämnade satser eller tillägg som inte står i originalet (kontrollera särskilt att inget avsnitt hoppats över eller sammanfattats),
- egna förklaringar, identifieringar eller underförstådda subjekt i parentes/hakparentes (ta bort),
- ställen där textens läsning bytts mot en annan (återställ; markera med [osäker tolkning] om den verkar fel),
- osäkra tolkningar som saknar markering: sätt "[osäker tolkning]" efter den troligaste tolkningen där tolkningen verkligen är osäker (ovanliga ord, oklara folk- och ortnamn, korrupta ställen). De äldre översättningarna saknar helt markeringar, så räkna med att några behövs, men överdriv inte,
- egennamn enligt namnregeln: folk och orter i textens form i enkel, konsekvent translitterering (t.ex. rus, Bulghar, Khazarer/khazar, Itil), vedertagna svenska former där sådana finns,
- fackord (titlar, mynt, mått) med originalordet translittererat inom parentes vid första förekomst i passagen.
Behåll i övrigt den befintliga översättningen; skriv inte om bra text i onödan.

Skriv resultatet inkrementellt (json.dump efter varje avsnitt) till granskning_fadlan_b/fadlan_b.json med exakt nycklarna ibn_fadlan:3:sv, ibn_fadlan:4:sv och ibn_fadlan:5:sv, och granskning_fadlan_b/andringar.md med en rad per ändring (nyckel, ställe, vad som ändrades).

Avsluta med en kort rapport: antal ändringar, antal tillagda [osäker tolkning], och de viktigaste sakfelen eller utelämningarna du rättade.
````

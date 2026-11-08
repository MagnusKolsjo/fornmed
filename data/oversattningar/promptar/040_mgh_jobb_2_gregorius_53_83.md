# MGH-jobb 2: Gregorius 53–83

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/historia_francorum__53-84.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
För latinska texter gäller dessutom: centrala termer (ämbeten, folkslag, kyrkliga och rättsliga begrepp) står med det latinska ordet inom parentes vid första förekomsten i en passage, t.ex. "hertigen (dux)". Egennamn återges i vedertagen svensk form där en sådan finns (Chlodovech/Klodvig, Paris), annars i den form texten har. Bibelcitat översätts som de står i texten.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_02/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad och har tidigare importerat varandras skript, så att översättningar hamnade i fel fil. Kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen):
- verk:historia_francorum (Gregorius av Tours, Decem libri historiarum), originaltexten, passagerna 53–83 i ordning (kommando med --fran 53 --till 84 --typer originaltext), 68078 tecken → data/oversattningar/openmgh/historia_francorum__53-84.json

Skriv utfilen som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också kapitelförteckningar, rubriker och korta poster. Behåll kapitelnummer och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att filen är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

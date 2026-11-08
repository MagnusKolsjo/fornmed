# MGH-jobb 14: Gregorius 444 + Jordanes 82–85

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/historia_francorum__444-445.json`, `data/oversattningar/openmgh/jordanes_getica__82-86.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt: osäkra tolkningar markeras i texten med "[osäker tolkning]" efter den troligaste tolkningen; lägg inte till egna förklaringar eller identifieringar inom hak- eller rundparentes; byt aldrig ut textens läsning eller ortnamn mot en annan form eller en modern identifiering.
För latinska texter gäller dessutom: centrala termer (ämbeten, folkslag, kyrkliga och rättsliga begrepp) står med det latinska ordet inom parentes vid första förekomsten i en passage, t.ex. "hertigen (dux)". Egennamn återges i vedertagen svensk form där en sådan finns (Chlodovech/Klodvig, Paris), annars i den form texten har. Bibelcitat översätts som de står i texten.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_14/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad; kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen <projektmapp>):
- verk:historia_francorum (Gregorius av Tours), originaltexten, passagen 444 (kommando med --fran 444 --till 445 --typer originaltext; en lång passage), 16070 tecken → data/oversattningar/openmgh/historia_francorum__444-445.json
- verk:jordanes_getica (Jordanes, De origine actibusque Getarum), originaltexten, passagerna 82–85 (kommando med --fran 82 --till 86 --typer originaltext), 7756 tecken → data/oversattningar/openmgh/jordanes_getica__82-86.json

Skriv varje utfil som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar och lägg till i filen efter hand.

Varje passage ska ha en översättning. Behåll kapitelnummer och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att varje fil är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager per fil, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

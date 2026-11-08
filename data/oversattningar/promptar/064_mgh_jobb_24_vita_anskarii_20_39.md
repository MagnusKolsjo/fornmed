# MGH-jobb 24: Vita Anskarii 20–39

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/vita_anskarii__20-40.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt reglerna om egennamn och om att inte göra egna tillägg: Birca, Sueones, Dani får återges som Birka, svear, daner; Sueonia som Svitjod; städer i nutida namn (Hamburg, Bremen, Köln); mindre orter och folk i textens form; inga förklaringar eller identifieringar inom parentes; byt aldrig ut textens läsning; osäkra tolkningar markeras i texten med "[osäker tolkning]" (obligatoriskt där du är osäker).
Centrala termer (ämbeten, kyrkliga begrepp) står med det latinska ordet inom parentes vid första förekomsten i en passage. Bibelcitat översätts som de står i texten.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_24/ (skapa den). Andra agenter arbetar parallellt; kör skript med absolut sökväg i din katalog och importera aldrig moduler från scratchpadens rot. Kontrollera innan varje skrivning att nycklarna tillhör ditt verk och intervall.

Ditt jobb (sökvägar relativa till <projektmapp>):
- verk:vita_anskarii (Rimbert, Vita Anskarii), originaltexten, passagerna 20–39 i ordning (kommando med --fran 20 --till 40 --typer originaltext), 69857 tecken → data/oversattningar/openmgh/vita_anskarii__20-40.json

Skriv utfilen som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), i omgångar. Varje passage ska ha en översättning; behåll kapitelnummer; sammanfatta aldrig. Kontrollera till sist att filen är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager, och högst tre ställen där tolkningen var särskilt osäker.
````

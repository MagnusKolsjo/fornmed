# MGH-jobb 25: LHF 0–31

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/liber_historiae_francorum__0-32.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt reglerna om egennamn (städer, länder och större floder i nutida namn: Paris, Soissons, Reims, Köln, Seine, Rhen; mindre orter, gods, skogar och folk i textens form) och om att inte göra egna tillägg: inga förklaringar eller identifieringar inom parentes; byt aldrig ut textens läsning; osäkra tolkningar markeras i texten med "[osäker tolkning]" (obligatoriskt där du är osäker). Namnformer för frankiska kungar som i de redan översatta filerna: Klodvig (Chlodovechus), Chilperik, Sigibert, Guntram, Fredegund, Brunhild.
Centrala termer står med det latinska ordet inom parentes vid första förekomsten i en passage.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_25/ (skapa den). Andra agenter arbetar parallellt; kör skript med absolut sökväg i din katalog och importera aldrig moduler från scratchpadens rot. Kontrollera innan varje skrivning att nycklarna tillhör ditt verk och intervall.

Ditt jobb (sökvägar relativa till <projektmapp>):
- verk:liber_historiae_francorum (Liber historiae Francorum), originaltexten, passagerna 0–31 i ordning (kommando med --fran 0 --till 32 --typer originaltext), 69617 tecken → data/oversattningar/openmgh/liber_historiae_francorum__0-32.json. Lösa "A." mitt i texten är spaltmarkeringar i utgåvan och kan utelämnas, som i den redan översatta filen för kap. 34–53.

Skriv utfilen som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), i omgångar. Varje passage ska ha en översättning; behåll kapitelnummer; sammanfatta aldrig. Kontrollera till sist att filen är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager, och högst tre ställen där tolkningen var särskilt osäker.
````

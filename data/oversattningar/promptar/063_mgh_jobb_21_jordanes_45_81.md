# MGH-jobb 21: Jordanes 45–81

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/jordanes_getica__45-82.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta senantik latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt reglerna om egennamn (städer och större floder i nutida namn; mindre orter och folk i textens form) och om att inte göra egna tillägg: inga förklaringar eller identifieringar inom parentes; byt aldrig ut textens läsning; osäkra tolkningar markeras i texten med "[osäker tolkning]" (detta är obligatoriskt där du är osäker).
För latinska texter gäller dessutom: centrala termer står med det latinska ordet inom parentes vid första förekomsten i en passage. Citat ur andra författare översätts som de står i texten.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_21/ (skapa den). Andra agenter arbetar parallellt; kör skript med absolut sökväg i din katalog och importera aldrig moduler från scratchpadens rot. Kontrollera innan varje skrivning att nycklarna tillhör ditt verk och intervall.

Ditt jobb (sökvägar relativa till <projektmapp>):
- verk:jordanes_getica (Jordanes, De origine actibusque Getarum), originaltexten, passagerna 45–81 i ordning (kommando med --fran 45 --till 82 --typer originaltext), 69475 tecken → data/oversattningar/openmgh/jordanes_getica__45-82.json. Passagerna är sidbaserade och börjar och slutar ofta mitt i meningar; följ samma brytpunkter.

Skriv utfilen som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), i omgångar. Varje passage ska ha en översättning; sammanfatta aldrig. Kontrollera till sist att filen är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager, och högst tre ställen där tolkningen var särskilt osäker.
````

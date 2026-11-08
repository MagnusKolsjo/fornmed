# MGH-jobb 20: Jordanes 0–44

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/jordanes_getica__0-45.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta senantik latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt reglerna om egennamn (städer och större floder i nutida namn; mindre orter och folk i textens form; Scandza står som Scandza) och om att inte göra egna tillägg: inga förklaringar eller identifieringar inom parentes; byt aldrig ut textens läsning; osäkra tolkningar markeras med "[osäker tolkning]". Jordanes folknamn i Scandza-avsnittet (Suehans, Suetidi, Gauthigoth m.fl.) står i textens form; identifiera dem inte med svear, götar osv.
För latinska texter gäller dessutom: centrala termer (ämbeten, folkslag, rättsliga begrepp) står med det latinska ordet inom parentes vid första förekomsten i en passage. Citat ur andra författare översätts som de står i texten.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_20/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad; kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen <projektmapp>):
- verk:jordanes_getica (Jordanes, De origine actibusque Getarum), originaltexten, passagerna 0–44 i ordning (kommando med --fran 0 --till 45 --typer originaltext), 68797 tecken → data/oversattningar/openmgh/jordanes_getica__0-45.json. Passagerna är sidbaserade (MGH-sidor) och börjar och slutar ofta mitt i meningar; följ samma brytpunkter.

Skriv utfilen som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt.

Varje passage ska ha en översättning. Behåll paragrafnummer och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att filen är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

# Namngranskning Gregorius del 1–5

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/historia_francorum__0-53.json`, `data/oversattningar/openmgh/historia_francorum__126-167.json`, `data/oversattningar/openmgh/historia_francorum__167-198.json`, `data/oversattningar/openmgh/historia_francorum__53-84.json`, `data/oversattningar/openmgh/historia_francorum__84-126.json`

## Uppdraget till delagenten

````text
Du ska granska och rätta egennamn i befintliga svenska maskinöversättningar av Gregorius av Tours, Historia Francorum. Översättningarna har gjorts av andra agenter som ibland bytt ut textens ortnamn mot moderna identifieringar (t.ex. "villam Rodoialensim" översatt som "godset Rueil"), vilket strider mot riktlinjerna.

Läs riktlinjerna: <projektmapp>/data/oversattningar/RIKTLINJER.md (särskilt punkterna om egennamn och om inga egna tillägg).

Regeln: större städer, länder och floder med allmänt brukat nutida namn får stå i den formen (Paris, Tours, Poitiers, Rouen, Lyon, Bordeaux, Loire, Rhône, Italien, Spanien). Mindre orter, gods (villa), borgar (castrum), byar (vicus), skogar, mindre floder, områden (pagus) och folk ska stå i textens form, gärna med typen och det latinska ordet: "godset Calensis (villa)", "byn Briva (vicus)", "gabaliternas stad". En modern identifiering får aldrig ersätta textens namn, inte heller med [osäker tolkning]. Ta också bort egna förklaringar eller identifieringar inom hak- eller rundparentes som inte står i texten (latinska termer inom parentes enligt riktlinjerna får stå).

Filer att granska (relativt <projektmapp>):
- data/oversattningar/openmgh/historia_francorum__0-53.json (passagerna 0–52)
- data/oversattningar/openmgh/historia_francorum__53-84.json (53–83)
- data/oversattningar/openmgh/historia_francorum__84-126.json (84–125)
- data/oversattningar/openmgh/historia_francorum__126-167.json (126–166)
- data/oversattningar/openmgh/historia_francorum__167-198.json (167–197)

Latinet hämtar du med
  python hjalpskript/kalltext.py verk:historia_francorum --fran N --till M --typer originaltext
från projektkatalogen. Läs bara från databasen.

Arbeta med skript i en egen katalog: <arbetsmapp>/namn_1_5/ (skapa den; importera inget från scratchpadens rot). Gör ersättningar med exakt strängbyte i rätt passage, kontrollera att varje sträng finns exakt en gång, och att varje fil efteråt har samma id-mängd som före. Ändra ingenting annat i översättningarna.

Rapportera per fil vilka namn du ändrade (från → till), och hur många ändringar totalt.
````

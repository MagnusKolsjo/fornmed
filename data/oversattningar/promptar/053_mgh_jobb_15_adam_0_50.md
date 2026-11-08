# MGH-jobb 15: Adam 0–50

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/adam_av_bremen__0-51.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida latinsk prosa till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt reglerna om egennamn och om att inte göra egna tillägg: mindre orter och folk står i textens form (Adam: Birca, Sictona, Ubsola, Sueones osv. får återges i vedertagen svensk form Birka, Sigtuna, Uppsala, svear eftersom sådana finns, men okända orter i textens form); inga förklaringar inom parentes; osäkra tolkningar markeras med "[osäker tolkning]".
För latinska texter gäller dessutom: centrala termer (ämbeten, folkslag, kyrkliga och rättsliga begrepp) står med det latinska ordet inom parentes vid första förekomsten i en passage, t.ex. "ärkebiskopen (archiepiscopus)". Bibelcitat och citat ur klassiska författare översätts som de står i texten.

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M --typer originaltext
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_15/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad; kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen <projektmapp>):
- verk:adam_av_bremen (Adam av Bremen, Gesta Hammaburgensis ecclesiae pontificum), huvudtexten, passagerna 0–50 i ordning (kommando med --fran 0 --till 51 --typer originaltext), 67781 tecken → data/oversattningar/openmgh/adam_av_bremen__0-51.json

Skriv utfilen som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också inledningar, rubriker och korta poster. Behåll kapitelnummer och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att filen är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

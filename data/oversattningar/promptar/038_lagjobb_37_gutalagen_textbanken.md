# Lagjobb 37: Gutalagen (textbanken)

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/lagar/gutalagen_enligt_holm_b_64.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta en medeltida lagtext på forngutniska till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/jobb_37/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad och har tidigare importerat varandras skript, så att översättningar hamnade i fel fil. Kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Texten är Gutalagen enligt Holm B 64 i Fornsvenska textbankens utskrift. Verket innehåller också Säves utgåva (id som börjar med gutalagen_save) med en befintlig översättning; den ska du inte använda eller kopiera. Ditt intervall 0–68 omfattar bara textbankens passager (id som börjar med lag:gutalagen_enligt_holm_b_64:). Översätt självständigt från den text du får.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen):
- verk:lag:gutalagen_enligt_holm_b_64, passagerna 0–68 i ordning (kommando med --fran 0 --till 69), 64929 tecken → data/oversattningar/lagar/gutalagen_enligt_holm_b_64.json

Skriv varje utfil som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också innehållsförteckningar, rubriker och korta poster. Behåll paragrafmarkeringar (§ 1) och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att varje fil är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall (alla ska börja med lag:gutalagen_enligt_holm_b_64:).

Rapportera kort: antal passager per fil, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

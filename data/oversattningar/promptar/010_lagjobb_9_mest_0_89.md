# Lagjobb 9: MESt 0–89

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/lagar/magnus_erikssons_stadslag_exklusiva_stadslagsflockar__0-90.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida svenska lagtexter (fornsvenska) till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/jobb_09/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad; använd aldrig filer utanför din katalog utom kalltext.py.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen):
- verk:lag:magnus_erikssons_stadslag_exklusiva_stadslagsflockar, passagerna 0–89 i ordning (kommando med --fran 0 --till 90), 79703 tecken → data/oversattningar/lagar/magnus_erikssons_stadslag_exklusiva_stadslagsflockar__0-90.json

Skriv varje utfil som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också innehållsförteckningar, rubriker och korta poster. Behåll paragrafmarkeringar (§ 1) och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att varje fil är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager per fil, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

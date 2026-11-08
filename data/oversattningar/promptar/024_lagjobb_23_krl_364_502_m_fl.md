# Lagjobb 23: KrL 364–502 m.fl.

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/lagar/dalalagen_aldre_vastmannalagen__143-155.json`, `data/oversattningar/lagar/kristoffers_landslag__364-503.json`, `data/oversattningar/lagar/sodermannalagen_stadsfastelse_confirmatio_enligt_nks_2237.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida svenska lagtexter (fornsvenska) till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/jobb_23/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad och har tidigare importerat varandras skript, så att översättningar hamnade i fel fil. Kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen):
- verk:lag:kristoffers_landslag, passagerna 364–502 i ordning (kommando med --fran 364 --till 503), 70330 tecken → data/oversattningar/lagar/kristoffers_landslag__364-503.json
- verk:lag:sodermannalagen_stadsfastelse_confirmatio_enligt_nks_2237, passagerna 0–1 i ordning (kommando med --fran 0 --till 2), 4116 tecken → data/oversattningar/lagar/sodermannalagen_stadsfastelse_confirmatio_enligt_nks_2237.json
- verk:lag:dalalagen_aldre_vastmannalagen, passagerna 143–154 i ordning (kommando med --fran 143 --till 155), 3957 tecken → data/oversattningar/lagar/dalalagen_aldre_vastmannalagen__143-155.json

Skriv varje utfil som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också innehållsförteckningar, rubriker och korta poster. Behåll paragrafmarkeringar (§ 1) och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att varje fil är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager per fil, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

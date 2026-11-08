# Lagjobb 21: UL A 130–179 + ÖgL fr. D

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/lagar/ostgotalagen_fragment_d_ur_holm_b_24.json`, `data/oversattningar/lagar/upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a__130-180.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida svenska lagtexter (fornsvenska) till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/jobb_21/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad och har tidigare importerat varandras skript, så att översättningar hamnade i fel fil. Kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen):
- verk:lag:upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a, passagerna 130–179 i ordning (kommando med --fran 130 --till 180), 72963 tecken → data/oversattningar/lagar/upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a__130-180.json
- verk:lag:ostgotalagen_fragment_d_ur_holm_b_24, passagerna 0–5 i ordning (kommando med --fran 0 --till 6), 6637 tecken → data/oversattningar/lagar/ostgotalagen_fragment_d_ur_holm_b_24.json

Skriv varje utfil som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också innehållsförteckningar, rubriker och korta poster. Behåll paragrafmarkeringar (§ 1) och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att varje fil är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager per fil, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

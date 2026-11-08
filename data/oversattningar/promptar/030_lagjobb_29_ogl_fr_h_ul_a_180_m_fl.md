# Lagjobb 29: ÖgL fr. H + UL A 180 m.fl.

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/lagar/ostgotalagen_fragment_h_ur_kyrkobalken_ur_skokloster_avdl_i_.json`, `data/oversattningar/lagar/tillagg_till_upplandslagen_hskr_a_ups_b_12.json`, `data/oversattningar/lagar/upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a__180-181.json`, `data/oversattningar/lagar/yngre_vastmannalagen_enl_holm_b_57__73-98.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida svenska lagtexter (fornsvenska) till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med
  python hjalpskript/kalltext.py <verk_id> --fran N --till M
från katalogen <projektmapp>. Läs bara från databasen; skriv aldrig till den, och rör inga andra filer än dina utfiler.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/jobb_29/ (skapa den). Andra agenter arbetar parallellt i samma scratchpad och har tidigare importerat varandras skript, så att översättningar hamnade i fel fil. Kör skript med absolut sökväg i din katalog, importera aldrig moduler från scratchpadens rot, och använd inga filer utanför din katalog utom kalltext.py. Kontrollera innan varje skrivning att nycklarna du skriver tillhör ditt verk och intervall.

Ditt jobb (sökvägar till utfilerna är relativa till projektkatalogen):
- verk:lag:ostgotalagen_fragment_h_ur_kyrkobalken_ur_skokloster_avdl_i_, passagerna 0–53 i ordning (kommando med --fran 0 --till 54), 24594 tecken → data/oversattningar/lagar/ostgotalagen_fragment_h_ur_kyrkobalken_ur_skokloster_avdl_i_.json
- verk:lag:upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a, passagen 180 (kommando med --fran 180 --till 181; en lång passage), 22488 tecken → data/oversattningar/lagar/upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a__180-181.json
- verk:lag:yngre_vastmannalagen_enl_holm_b_57, passagerna 73–97 i ordning (kommando med --fran 73 --till 98), 21752 tecken → data/oversattningar/lagar/yngre_vastmannalagen_enl_holm_b_57__73-98.json
- verk:lag:tillagg_till_upplandslagen_hskr_a_ups_b_12, passagerna 0–18 i ordning (kommando med --fran 0 --till 19), 3625 tecken → data/oversattningar/lagar/tillagg_till_upplandslagen_hskr_a_ups_b_12.json

Skriv varje utfil som ett JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) med ett Python-skript (json.dump), inte för hand. Arbeta i omgångar om några passager i taget: översätt, lägg till i filen (läs in befintligt innehåll, uppdatera, skriv om), fortsätt. Då går inget förlorat om du avbryts, och du kan fortsätta där filen slutar.

Varje passage ska ha en översättning, också innehållsförteckningar, rubriker och korta poster. Behåll paragrafmarkeringar (§ 1) och styckeindelning. Översätt hela texten; sammanfatta aldrig. Kontrollera till sist att varje fil är giltig JSON och att nycklarna är exakt originalpassagernas id i ditt intervall.

Rapportera kort: antal passager per fil, och högst tre ställen där tolkningen var särskilt osäker (passage-id och vad som var svårt).
````

# Pilotöversättning lagar m.m.

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/beowulf_sv.json`, `data/oversattningar/eddan_sv.json`, `data/oversattningar/lagar/smalandslagens_kyrkobalk.json`, `data/oversattningar/langder_hednalagen_sv.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta medeltida texter till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md

Hämta originaltexterna (JSON med id, adress, språk och text per passage) med:
  python hjalpskript/kalltext.py <verk_id>
(kör från katalogen <projektmapp>). Läs bara från databasen; skriv aldrig till den.

Översätt dessa verk och skriv resultatet som JSON-objekt {originalpassagens id: översättning} (UTF-8, ensure_ascii=False, indent=1) till angivna filer:

1. verk:lag:smalandslagens_kyrkobalk (fornsvenska, Smålandslagens kyrkobalk, 18 passager) → data/oversattningar/lagar/smalandslagens_kyrkobalk.json
2. verk:hednalagen (2 passager: lagtexten på fornsvenska i Olavus Petris avskrift med runan ᛘ för 'man', och Olavus Petris kommentar på 1500-talssvenska), verk:vastgotalagens_lagmanslangd, verk:vastgotalagens_konungalangd, verk:vastgotalagens_biskopslangd (fornsvenska) → alla i samma fil data/oversattningar/langder_hednalagen_sv.json
3. verk:edda:voluspa_hin_skamma (fornvästnordiska, eddadikt) → data/oversattningar/eddan_sv.json
4. verk:finnsburg (fornengelska, Finnsburgfragmentet) → data/oversattningar/beowulf_sv.json

Varje passage ska ha en översättning, även inledningar och korta poster. Dikter översätts radvis med radbrytningarna kvar; strofnummer behålls. Skriv filerna med ett Python-skript (json.dump), inte för hand, så att citattecken och radbrytningar blir rätt. Kontrollera efteråt att varje fil är giltig JSON och att antalet nycklar är lika med antalet originalpassager.

Rapportera kort: antal passager per fil, och 3–5 ställen där tolkningen var osäker (med passage-id och vad som var svårt). Ingen annan text behövs.
````

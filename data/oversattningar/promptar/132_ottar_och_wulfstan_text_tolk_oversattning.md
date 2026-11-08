# Ottar och Wulfstan: text, tolk, översättning

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/ottar_wulfstan_sv.json`

## Uppdraget till delagenten

````text
Uppgift i projektet <projektmapp> (fornmed, databas och MCP-server över medeltida nordiska källor). Lägg till Ottars (Ohthere) och Wulfstans reseberättelser samt den fornengelska Orosius beskrivning av Europas norra folk (avsnittet där Cwenland, Sweon, Scridefinnas, Osti m.fl. nämns) som en ny källa.

KÄLLOR (public domain, Internet Archive):
1. Fornengelsk text: Henry Sweet (utg.), Extracts from Alfred's Orosius, Oxford 1885, id extractsfromalfr00alfruoft. OCR redan nedladdad: <arbetsmapp>/ottar/extractsfromalfr00alfruoft.txt. Relevant: avsnitt III (Europe, slutet med de nordliga folken; i OCR:en ungefär före tecken 22808), IV Ohthere's Voyage (från tecken ~22808) och V Wulfstan's Voyage (~30397 till ~34837). OCR:en har förvanskat þ och ð (f>, |?, ]?, J>, £> m.m.), æ (ae, a3, se) och ⁊ (7), och blandar in Sweets textkritiska noter och radnummer. Hela Sweets 1883-utgåva (EETS 79) finns som id kingalfredsorosi79oros (OCR i samma katalog) och kan användas som jämförelse.
2. Engelsk översättning: Richard Hakluyt / E. Goldsmid (utg.), The Discovery of Muscovy ... with the Voyages of Ohthere and Wulfstan from King Alfred's Orosius, 1889, id discoveryofmusco00hakluoft (hämta https://archive.org/download/discoveryofmusco00hakluoft/discoveryofmusco00hakluoft_djvu.txt). Kontrollera att den innehåller en engelsk översättning av Ohthere och Wulfstan; ta i så fall med den som översättning (sprak eng). Om den inte finns, hoppa över engelskan.

GÖR:
a) Rensa den fornengelska texten till läsbar normaliserad form efter Sweet: återställ þ/ð, æ, ⁊ (skriv "and" eller ⁊ konsekvent – välj ⁊ som i utgåvan), ta bort radnummer, sidhuvuden och noter. Följ Sweets ordalydelse; rekonstruera inte fritt. Där OCR:en är oläslig och du inte säkert kan återställa, skriv [oläslig]. Spara rensad text i data/transkriptioner/ottar_wulfstan.json som {id: text} och notera i en kommentar/beskrivning att den är rensad av språkmodell från OCR och ogranskad.
b) Skriv tolken tolkar/ottar_wulfstan.py enligt projektets mönster (läs kallpaket.py och t.ex. tolkar/liber_monstrorum.py och tolkar/adam_skolier.py för hur OCR och transkriptioner hanteras). Verk: verk:ottar_wulfstan, titel "Ottars och Wulfstans berättelser (ur den fornengelska Orosius)", genre "geografi", sprak ["ang"], datering 0890/0899. Passager: dela per stycke i Sweets text (t.ex. ottar_wulfstan:europa:1, ottar:1…, wulfstan:1…), adress med Sweets sida och rader, typ originaltext, sprak "ang". Engelsk översättning som egen utgåva, typ oversattning, sprak "eng", passager parade per avsnitt om det går, annars per stycke. Utgåvereferenser och licens "Public domain". Kallsamling id "ottar_wulfstan". argparse med --torr. Svensk docstring och svenska kommentarer som förklarar varför.
c) Maskinöversätt den fornengelska texten till svenska enligt data/oversattningar/RIKTLINJER.md (läs den först och följ exakt: troget och fullständigt, fackord med originalordet inom parentes, [osäker tolkning], inga egna tillägg eller identifieringar; folk och mindre orter i textens form, t.ex. Cwenas, Beormas, Terfinnas, Scridefinnas, Sweon, Osti, Estmere, Truso, Sciringes heal, men vedertagna svenska former där sådana finns, t.ex. Hedeby för æt Hæþum, Gotland för Gotland, Blekinge för Blekinga eg, Möre, Öland, Bornholm). Spara som data/oversattningar/ottar_wulfstan_sv.json {originalpassagens id: svensk text} och låt tolken ladda den med paket.lagg_till_maskinoversattningar(fil, "fornengelskan").
d) Testa med python -m tolkar.ottar_wulfstan --torr och ladda sedan i dev (utan --torr; projektets .env pekar på dev-databasen; skriv aldrig i <produktionsmapp>). Kontrollera att varje svensk översättning har sitt originals id och rimlig längd.

Ändra inga andra befintliga filer än de nya. Använd scratchpad-katalogen ovan (undermapp ottar/) för hjälpfiler.

Rapportera: antal passager per utgåva, exempel (kort) på rensad fornengelsk text, osäkra ställen, och om Hakluyts engelska fanns med.
````

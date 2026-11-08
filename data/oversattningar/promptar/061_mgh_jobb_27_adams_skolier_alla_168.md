# MGH-jobb 27: Adams skolier (alla 168)

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/adam_skolier_lappenberg_sv.json`, `data/oversattningar/adam_skolier_sv.json`

## Uppdraget till delagenten

````text
Du ska maskinöversätta skolierna (marginaltilläggen) till Adam av Bremens Gesta Hammaburgensis ecclesiae pontificum från latin till modern svenska för en forskningsdatabas. Översättningarna gör texterna sökbara; de märks som ogranskade maskinöversättningar.

Läs först riktlinjerna och följ dem exakt: <projektmapp>/data/oversattningar/RIKTLINJER.md
Observera särskilt reglerna om egennamn (Birca, Sictona, Ubsola, Sueones får återges som Birka, Sigtuna, Uppsala, svear; städer i nutida namn; mindre orter och folk i textens form) och om att inte göra egna tillägg: inga förklaringar inom parentes; byt aldrig ut textens läsning; osäkra tolkningar markeras med "[osäker tolkning]", skadad text med "[oklart]".
Centrala termer står med det latinska ordet inom parentes vid första förekomsten i en passage.

Hämta originaltexterna med
  python hjalpskript/kalltext.py verk:adam_av_bremen --fran 0 --till 1000 --typer skolion
från katalogen <projektmapp>. Det ger alla 168 skolier från tre källor: 110 ur Schmeidlers utgåva (OCR), 48 ur samma utgåva transkriberade från sidbilderna, och 10 ur Lappenbergs utgåva (id med skolion_lappenberg). ALLA ska översättas, oavsett källa. Vissa är ofullständiga i källan; översätt det som står och markera avbrott med [oklart]. Läs bara från databasen; skriv aldrig till den.

VIKTIGT: Lägg alla dina hjälpskript och mellanfiler i en egen katalog: <arbetsmapp>/mgh_27/ (skapa den). Andra agenter arbetar parallellt; kör skript med absolut sökväg i din katalog och importera aldrig moduler från scratchpadens rot.

Utfiler (relativt projektkatalogen), JSON-objekt {originalpassagens id: översättning}, UTF-8, ensure_ascii=False, indent=1, skrivna med json.dump i omgångar:
- de 158 skolierna med id adam_av_bremen:skolion:N → data/oversattningar/adam_skolier_sv.json
- de 10 skolierna med id adam_av_bremen:skolion_lappenberg:N → data/oversattningar/adam_skolier_lappenberg_sv.json

Kontrollera till sist att filerna är giltig JSON och tillsammans har exakt alla 168 id (158 + 10), utan andra nycklar.

Rapportera kort: antal per fil, och högst tre ställen där tolkningen var särskilt osäker.
````

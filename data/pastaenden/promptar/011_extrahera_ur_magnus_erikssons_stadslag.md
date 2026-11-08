# Extrahera ur Magnus Erikssons stadslag

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/magnus_erikssons_stadslag.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt, inklusive avsnittet "Särskilda regler för vissa verk" (om städerna). Läs den först.

Uppdrag:
- Lag: Magnus Erikssons stadslag (de flockar som är exklusiva för stadslagen), verk-id `verk:lag:magnus_erikssons_stadslag_exklusiva_stadslagsflockar`. Läs flockarna utan balk och balkarna ' KgB ' (konungabalken: borgmästare, råd, fogde, val), ' EB ' (edsöre), ' RB ' (rådstugubalken: rätten, domare, jäv, vittnen) och ' SkB '. Sök efter dråp i övriga balkar med `--sok dråp dräp mansbot`.
- Plats: `plats:sdhk:sverige`. Skriv i filens beskrivning att lagen gäller rikets städer.
- Fil: <projektmapp>/data/pastaenden/lagar/magnus_erikssons_stadslag.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Filen är skriven och kontrollen ger inga fel: 57 påståenden, `--kontrollera` utan anmärkningar. Ingenting är inläst i databasen och inga andra filer är ändrade.

Fil: <projektmapp>/data/pastaenden/lagar/magnus_erikssons_stadslag.json

**Antal per ämne:**
- Jäv och oväld: 20
- Edsöre: 23
- Dråp: 13
- `stiftar_lag`: 1

**Lästa flockar:** stycke 1 (bara rubrik), KgB 1–8, 12–13, 15–26, RB 1–8, 12–23, 26–28, 30–35, EB 16, 23, 26, 27 och SkB 1–20. Sökningen på dråp gav SkB 2 och 5, RB 26 samt EB 26 och 27. I GB, ÄB, JB, BB, KpB och TjB finns inget om de tre ämnena.

**Osäkra läsningar:**
- I RB 13 står "iæff". Ordet betyder sannolikt tvivel och inte jäv, så jag har inte tagit ut det.
- I SkB 9 har jag läst "fordærffwas" som "omkommer" och tagit det som vådadråp.
- I SkB 5 har jag läst "manna wækt" som dråp.
- I EB 27 ligger dråpbalkens text "[DB Vl 1]" i samma passage som stadgan. Jag har tagit ut den därifrån.
- SkB 2 (frid i skeppet som i gården) har jag tolkat som hemfrid, alltså under edsöre.

**Begrepp som saknades:** flock och samnad, frid i skepp, behörighetsvillkor (ärvd egendom, nationalitet).

**För jämförelsen med de andra lagarna:**
- Staden har häradets plats. Edsöresboten är 60 marker till målsäganden, 60 till kungen och 40 till staden, och den skyldige ska inte rymma riket.
- Jäv gäller rådet: högst fyra av samma släkt, inte två bröder samtidigt, och domareden förbjuder att döma för frändskaps eller vänskaps skull. Mutor ger 40 marker delade i tredjedelar och avsättning ur rådet. Landsbor får vittna i staden om dråp men inte om gäld.
- Stadgan från 1357 är utfärdad av Erik Magnusson. Den gäller bara ett tillägg, inte hela stadslagen.

# Extrahera ur Magnus Erikssons landslag

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/magnus_erikssons_landslag.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag:
- Lag: Magnus Erikssons landslag, verk-id `verk:lag:magnus_erikssons_landslag`, flockarna utan balk (prolog), balkarna ' KgB ' (Kununga balkrin: konungaval, eriksgata, kungens och folkets eder — ta ut dem med `begrepp:konungaval`, `begrepp:eriksgata`, `utses_av` m.fl.), ' EB ' (Eþzöris balker), ' TgB ' (Þingmala balkenum, med jäv och nämnd), ' Dmv ' (Drapæ balker meþ vilia) och ' Dvå ' (Drapæ balker meþ vaþa).
- Plats i varje påstående: `plats:sdhk:sverige`.
- Skriv till: <projektmapp>/data/pastaenden/lagar/magnus_erikssons_landslag.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klart. 245 påståenden ligger i <projektmapp>/data/pastaenden/lagar/magnus_erikssons_landslag.json. `pastaenden_fil.py --kontrollera` ger 0 fel. Inget är inläst i databasen och inga andra filer är ändrade.

**Per ämne:** dråp 116, edsöre 65, jäv/nämnd 47, statsrätt (konungaval, eriksgata, eder) 17, `stiftar_lag` 0.

**Lästa flockar:** stycke 1–3 och innehållsförteckningen, KgB 1–33, EB 1–45, TgB 1–39, Dmv 1–42 och Dvå 1–19.
- Prologen innehåller bara titlar och ingen stadfästelse, därför inget `stiftar_lag`.
- Vissa passager innehåller två flockar (t.ex. kgb_15, eb_6, eb_36, eb_45, dmv_30). Det står i anmärkningen.

**Osäkra läsningar:**
- I Dmv 41 (försåt) är det oklart vem "þen firi ær" och "han til komber" syftar på.
- I Dmv 16 är ordet "þrælkær/þrælbær" oklart.
- I EB 9 gör utgåvans "{ei}" det osäkert om landbon har fridsbönen.
- EB 17 har jag tolkat som edsöre, fast flocken inte uttryckligen säger att edsöret är brutet.
- För brottet att hysa en fredlös använde jag `begrepp:fredloshet` som subjekt, och likaså för den biltoges gods.

**Saknade begrepp:** jordägare, kungsnämnd, försåt, dulgadråp, mordgäld, tvebot, halsbane/rådsbane, fridsbön, sköfling och lösker man.

**Att jämföra med andra lagar:**
- Edsöresgodset delas i tre lika delar: jordägaren, kungen och häradet.
- Kungens dråpsrätt är högst 13 marker 8 örtugar, och häradet får lika mycket.
- När ett barn mellan 7 och 15 år dräper med vilja delas 20 marker: 14 till målsäganden, 3 till kungen och 3 till häradet.
- Jäv motiveras med en lång lista grunder i både domareden och nämndeden: frändskap, svågerskap, vänskap, fejd, avund, rädsla, penninggirighet och väld.
- Part kan jäva högst tre av kungsnämndens tolv ledamöter.
- Domare, nämndemän och vittnen ska vara bofasta.
- Den som tar muta förlorar ämbetet för alltid.
- Lagmannen, häradshövdingen och kungen själva ska väljas genom treförslag.

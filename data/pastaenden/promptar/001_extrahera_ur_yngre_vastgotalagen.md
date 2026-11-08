# Extrahera ur Yngre Västgötalagen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/yngre_vastgotalagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag:
- Lag: Yngre Västgötalagen, verk-id `verk:lag:yngre_vastgotalagen_enligt_holm_b_58`, balkarna ' Db ' (Dræpare bolkær), ' Frb ' (Friþ balkær), ' Ob ' (Orbotæ mal), ' Rlb ', samt flockar utan balk (prolog m.m.). Sök efter jäv-, nämnd- och edsregler i resten med `--sok nämnd vittne frände jäv ed tylft`.
- Dessutom tilläggen, verk-id `verk:lag:yngre_vastgotalagen_tillagg_enligt_holm_b_58` (innehåller edsöresstadgar; läs hela, ca 41 000 tecken).
- Plats i varje påstående: `plats:sdhk:vastergotland`.
- Skriv till: <projektmapp>/data/pastaenden/lagar/yngre_vastgotalagen.json (båda verken i samma fil).

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klart. Jag har skrivit 167 påståenden till <projektmapp>/data/pastaenden/lagar/yngre_vastgotalagen.json. Båda verken ligger i filen. `pastaenden_fil.py --kontrollera` går igenom utan fel. Inget är inläst i databasen och inga andra filer är ändrade.

**Påståenden per ämne:**
- Dråp: cirka 98, inräknat nidingsverk och dråp i kyrka.
- Edsöre och orbotamål: 55.
- Jäv och nämnd: 13.
- `stiftar_lag`: 1.

**Flockar jag läste:**
- Hela Db, Frb, Ob och Rlb samt flockarna utan balk. Där finns ingen egentlig prolog.
- Från sökningen i resten tog jag Kkb 5, 22 och 52, Äb 14 och Tjb 17.
- Hela tilläggsverket, Add. 1–31. Passagen `yvgl_add_31` innehåller också avsnitten 8–13 om arv, stämning och eder.

**Osäkra läsningar och tolkningar:**
- Db 8 saknas som egen passage. Texten står i passagen `innehallsforteckning`, så den citeras därifrån.
- Rlb 3 ("kononger skal nempþ firi sik sætiæ") har jag läst som att kungen sätter nämnd, men läsningen är osäker.
- Db 4: det är oklart om de tolv markerna är häradshövdingens böter eller hans andel.
- Db 23–39 har jag klassat som `vadadrap`, men lagen använder inte ordet våda där.
- Frb 12: "firi giær" har jag tolkat som att döda med trolldom eller gift.
- Add. 31: "konon byrghir" har jag läst som kung Birger. Lagen säger inte vilken Birger.

**Begrepp som saknades:** hustru eller husfru som mottagare. Jag skrev det som fritt värde. Halvbane, rådsbane, biltog och fridhelig man finns inte heller som egna begrepp.

**Att notera vid jämförelsen:**
- Ättebot delas 6/6 mellan arvingarna och ätten, och för ättens del 3/3 på fädernet och mödernet.
- Edsöret delas i tredjedelar mellan målsäganden, kungen och häradet, sedan hustrun först tagit sin del.
- Kungen får ingen andel av halvbanes och rådsbanes bot.
- Jäv motiveras med mutor (Add. 1). Domare och ämbetsmän mister ämbetet, nämndemannen böter 40 marker.
- Bannlysta, biltoga, fridlösa, trälar och omyndiga får inte stå i ed eller nämnd. Kvinnor får inte vittna, utom om nöddop.
- För rådsbanesak krävs däremot edgärd bland fränder, tolft på fädernet och halv tolft på mödernet, var och en inom sjätte led. Det är motsatsen till jäv.
- Lagen ger egna motiveringar: dråp på ting och i kyrka är edsöre "ty där ska alla ha frid". Kvinnan kan inte bryta edsöret eftersom hon inte kan bli biltog. Hustruns lott förverkas inte, ty var och en böter för sin egen sak.
- Add. 28 säger att en ensam man inte kunde göra hemsökn förrän edsöret gavs.

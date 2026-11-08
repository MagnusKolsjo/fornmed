# Extrahera ur Södermannalagen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/sodermannalagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag:
- Lag: Södermannalagen, verk-id `verk:lag:sodermannalagen_enligt_codex_iuris_sudermannici`, flockarna utan balk och balkarna ' Kgb ' (Kununx balker), ' Mb ' (Manhælghis balker) och ' Tb ' (Þingmala balker).
- Dessutom stadfästelsen, verk-id `verk:lag:sodermannalagen_stadsfastelse_confirmatio_enligt_nks_2237` (ta ut vem som stadfäste lagen med `stiftar_lag`), och tilläggen `verk:lag:sodermannalagens_additamenta_efter_nks_2237` om de berör ämnena.
- Plats i varje påstående: `plats:sdhk:sodermanland`.
- Skriv till: <projektmapp>/data/pastaenden/lagar/sodermannalagen.json (alla tre verken i samma fil).

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klart. <projektmapp>/data/pastaenden/lagar/sodermannalagen.json har 178 påståenden och `pastaenden_fil.py --kontrollera` ger inga fel. Ingenting är inläst i databasen och inga andra filer är ändrade.

**Antal påståenden per ämne:** dråp 118 (varav trolldomsdråp och mord), edsöre 30 (hemsökn, våldtäkt och fredlöshet räknade hit), jäv och nämnd 22, `stiftar_lag` 8.

**Lästa flockar:** stycke 1–3 (prologen), Kgb 1–12, Mb 1–36 och Tb 1–11. I databasen saknas Mb 12 och 17 samt Tb 3. Dessutom stadfästelsen (stycke 2) och tilläggen Add. 1, 3, 6, 8 och 12.

**Osäkra läsningar och tolkningar:**
- Add. 8 (våldsgärning mot bonde i flock och följe) har jag lagt under `begrepp:hemsokn`, fast ordet inte står i texten.
- Add. 12 (1325) säger inte vem som stadfäste. Jag satte `begrepp:lagman` som subjekt med biskopen nämnd i anmärkningen.
- Mb 19 "halwre bot", maltmæle i Mb 26 och Tb 2 om den som dömer i en annan domares ställe är osäkra.
- Mb 18 och Mb 26 §7 säger olika om dråp av omyndig: vådabot respektive en fjärdedel av full bot.

**Begrepp som saknades:** fridsbrott, sporgäld, tvebot och trebot, tackebot, rådsbane och hållbane, mordvapen, folklandsnämnd, den anklagade (parten), skeppslag och förverkat gods. De är skrivna som fria värden. För förverkat gods har jag använt brottet som subjekt och förklarat det i anmärkningen.

**Att notera för jämförelsen:**
- Edsöret delar förverkat gods i tre lika delar mellan målsägande, kung och hundare.
- Tvebot ger målsäganden först hälften och sedan en tredjedel av resten. Trebot delas lika mellan målsäganden å ena sidan och kung och hundare å andra.
- Biskopen tar tre mark i varje dråp utom vid våda.
- Jäv motiveras inte uttryckligen. I stället delas nämnden så att vardera parten råder över halva (Kgb 9, Tb 2, 6 och 10, Add. 6). Vittnen ska vara fria, fridvita och bygdefasta (Tb 9).
- Stadfästelsen namnger lagman Laurens Ulfsson, tolv riddare och kung Magnus Eriksson (Söderköping 1327).

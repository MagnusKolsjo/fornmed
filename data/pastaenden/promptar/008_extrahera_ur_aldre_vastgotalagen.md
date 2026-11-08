# Extrahera ur Äldre Västgötalagen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/aldre_vastgotalagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag:
- Lag: Äldre Västgötalagen, verk-id `verk:lag:aldre_vastgotalagen` (hela lagen är bara ca 78 000 tecken).
- Läs särskilt balkarna ' Md ' (Af mandrapi), ' Bd ' (bardaghæ), ' Rlb ' (Rætlosæ bolkær), ' Kkb ' (dråp i kyrka), ' Vs ' och sök efter jäv-, nämnd- och edsregler i resten med `--sok nämnd vittne frände jäv ed tylft`.
- Plats i varje påstående: `plats:sdhk:vastergotland`.
- Skriv till: <projektmapp>/data/pastaenden/lagar/aldre_vastgotalagen.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klart. 76 påståenden ligger i <projektmapp>/data/pastaenden/lagar/aldre_vastgotalagen.json. `pastaenden_fil.py --kontrollera` ger inga fel, och alla citat är maskinellt kontrollerade som ordagranna delsträngar av flockarnas fornsvenska text. Inget är inläst i databasen och inga andra filer är ändrade.

**Per ämne:** Dråp 71, varav 13 gäller nidingsverk och orbotamål. Edsöre 0. Jäv och nämnd 5. `stiftar_lag` 0, eftersom lagen saknar prolog och stadfästelse.

**Lästa flockar:**
- Md 1–15, Bd 1–9, Rlb 1–13, Vs 1–5 och Conongs bolkær.
- I Kkb flockarna om dråp och frid: 3, 7, 12 och 22.
- Sökträffar: Äb 11, 15 och 18, Mlb 1–6, Tjb 6, Gb 5 och 9, Jb 16, Fb 4 och 11.

**Osäkra läsningar:**
- Md 5 §1: jag läser "ok sva allir mæn" som att även landet får nio marker.
- Md 5 §4: "eigh ma frid flyia" kan läsas åt två håll.
- Md 12 och 15: att flockarna gäller vådadråp är min tolkning, ordet står inte där.
- Bd 7: ordningen i tredelningen av den fredlöses gods är osäker.
- Bd 8: "firigær" kan betyda förgörande, alltså trolldom eller gift.
- Rlb 3: att lagmannen sätter nämnd på tinget är en tolkning.

**Saknade begrepp:** rådsbane och hållbane, sägnarting, förverkat gods, orbotamål och sluten häradsnämnd ("lukt hæraþsnæmd").

**För jämförelsen:**
- Lagen har ingen edsörelagstiftning. Uppräkningen av nidingsverk som orbotamål (dråp i kyrka och på ting, på kvinna, på sovande) fyller den funktionen.
- Det finns inga egentliga jävsregler. Ätteboten delas lika mellan arvingen och ätten.
- Kungen tar nio marker vid dråp men har ingen andel i rådsbanes och hållbanes böter.
- Om dråparen är okänd faller ansvaret på grannarna, byn och till sist häradet.

# Extrahera ur Östgötalagen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/ostgotalagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag:
- Lag: Östgötalagen A, verk-id `verk:lag:ostgotalagen_a_ur_holm_b_50`, balkarna ' Kgb ' (Kunungx eþzsöre), ' Db ' (Drapa balkær), ' Rb ' (Ræfsta balkær) och flockar utan balk (prolog m.m.). Sök efter jäv-, nämnd- och edsregler i övriga balkar med `--sok nämnd vittne frände jäv ed tylft`.
- Plats i varje påstående: `plats:sdhk:ostergotland`.
- Skriv till: <projektmapp>/data/pastaenden/lagar/ostgotalagen.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klar. Jag har skrivit 176 påståenden till <projektmapp>/data/pastaenden/lagar/ostgotalagen.json. `pastaenden_fil.py --kontrollera` går igenom utan fel. Inget är inläst i databasen.

**Per ämne:** dråp och våda 87, edsöre 42, jäv/nämnd/ed 43, `stiftar_lag` 4.

**Lästa flockar:**
- hela Kgb (1–34), Db (1–21) och Rb (1–26)
- delar utan balk: innehållsförteckningen, "stycke 1" och tre rubrikstycken i Gipta balkær. Ingen av dem innehåller prolog eller stadfästelse.
- via sökningen: Kkb 13–18 och 25 samt Vm 1–3, 6, 8, 9 och 31.

**Osäkra läsningar:**
- "siaxtantighi" har jag tolkat som 160 marker.
- "utan wærþ ok uaku" (Kgb 34) är osäkert tolkat.
- Negationen i Kgb 29 ("egh bo hans skiptis. ok lif hans…") är tvetydig.
- Ordet "uilin" om domaren i Rb 22 kan betyda partisk eller ovillig.
- Rb 3 gäller bötesdelning efter räfst "i götlandi".
- Kgb 30–32 (landsförräderi, mordbrand, agnabak) har jag inte tagit ut, eftersom de ligger utanför ämnena.

**Avvikelse från listan:** jag använde `begrepp:jarl`, som finns i databasen men inte i din lista, som subjekt för tre stiftar_lag-påståenden om Birger jarl. Det fjärde gäller kung Erik.

**Begrepp som saknades:** räfst, mordgäld, gislingabrott, tack ("þokke"), ensak och borgesman ("taki"). Öransbot har jag skrivit som `attebot`.

**För jämförelsen mellan lagarna:**
- Edsöresgodset delas i tre: målsäganden, kungen och häradet.
- Vid dråp får kungen och häradet vardera 13 marker och 8 örtugar.
- Öransbot betalas med två delar från fädernet och en tredjedel från mödernet.
- Jäv i nämnden gäller motparter, deras gunstlingar ("uilda mæn") och deras fränder. I biskopens nämnd är också sakföraren jävig.
- Edsöret motiveras med att den skyldige blir biltog. Därför kan varken kvinna eller träl bryta det.

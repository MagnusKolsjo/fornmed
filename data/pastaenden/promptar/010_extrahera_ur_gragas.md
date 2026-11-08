# Extrahera ur Grágás

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/gragas.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt, särskilt regeln om Grágás i avsnittet "Särskilda regler för vissa verk". Läs den först.

Uppdrag:
- Verk: Grágás, verk-id `verk:gragas`. Den finns bara i dansk översättning; läs med `--oversattning`. Översättningen har avsnitt som Kristenretsafsnittet, Thingsordningsafsnittet och (sannolikt) Drabsafsnittet. Lista först avsnitten med `lagtext.py verk:gragas --oversattning | grep '^###'` och läs sedan de avsnitt som rör dråp (drab, manddrab, bod, fredløs/skovgang), fridsbrott och tingets ordning, nämnd och domare (inhabilitet, nævninger, dommere, vidner, slægtskab).
- Plats: `plats:island` (definiera den enligt specifikationen).
- Fil: <projektmapp>/data/pastaenden/lagar/gragas.json
- Grágás saknar edsöre i svensk mening; ta ut motsvarande fridsbrott och fredlöshet (skovgang) under dråp eller med `begrepp:fredloshet`.

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klart. Filen <projektmapp>/data/pastaenden/lagar/gragas.json har 73 påståenden. `pastaenden_fil.py --kontrollera` ger inga fel. Ingenting är inläst i databasen och inga andra filer är ändrade. Alla citat är kontrollerade med skript mot respektive kapitels danska text.

**Antal per ämne:** dråp 39, fridsbrott (motsvarar edsöre) 6, jäv och oväld 28, stiftar_lag 0. Grágás har ingen prolog eller stadfästelse.

**Lästa avsnitt:**
- Hela Manddrab: gragas:3:dan:86–112.
- Ring-Opregning: 4:dan:113–115.
- Thingsordning: 2:dan:20, 25, 26, 35, 41, 43, 45, 55, 59, 70.
- Lovsigemand: 5:dan:1.
- Ord: 14:dan:237, genomläst men inget uttaget.

**Osäkra läsningar och tolkningar:**
- Jag har tolkat "Næstsødskendebørn" som tremänningar.
- Landsforvisning/Fjørbaugsgaard har jag satt till `landsflykt` och skovgang till `fredloshet`.
- Kvid har jag satt till `namnd`. Tylfterkvid är en tolvmannakvid som goden utser, inte en tylftered.
- "Bøder for Drab" har jag satt till `mansbot`. Lovsigemand har jag satt till `lagman`, vilket är tveksamt.
- Fridsbrott: dråp på tinget och dråp efter givet fredslöfte står under `fridsbrott`. Lejdebrottet i kap. 114 står bara med ett `tillfaller`-påstående.

**Begrepp som saknades:** gode/godord, andligt släktskap (står nu under frändskap), lagsagoman, fjärdingsdomstol, personlig bot (réttr), huvudpris för fredlös och lysning.

**Att notera inför jämförelsen:**
- Dråp leder till fredlöshet, inte till böter som går till kung och härad.
- Fränderboten går i fyra ringar mellan motsvarande grader i båda ätterna. Fredslöfte (trygd) krävs i gengäld.
- Jäv motiveras med släktskap upp till tremänning, svågerskap, andligt släktskap och ouppgjorda dråpsaker. Dessutom krävs förmögenhet och färdighet att resa till tinget.
- Det finns ett språkkrav på domare: de ska kunna "danska tungan".

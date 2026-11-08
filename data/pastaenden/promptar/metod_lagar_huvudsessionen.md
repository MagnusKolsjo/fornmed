# Metod: det i lagpåståendena som huvudsessionen gjorde själv

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/pastaenden/lagar/*.json`, `begreppsregister.py`

De flesta lagpåståendena togs ut av delagenter, med uppdragen `001`–`018` här och specifikationerna i `specifikationer/`. Fyra delar av arbetet gjordes i stället direkt av huvudsessionen, och för dem fanns ingen prompt. Den här beskrivningen är skriven i efterhand ur arbetsloggen.

## 1. Hednalagen

- **Underlag:** `data/pastaenden/lagar/hednalagen.json` har 9 påståenden. De togs ut medan delagenterna arbetade med de övriga lagarna, efter samma specifikation, [SPEC_version_1](specifikationer/SPEC_version_1.md).
- **Texten:** Hednalagen finns bara i Olavus Petris avskrift i Ängsökodexen. Lagtexten är en enda passage, och den lästes i sin helhet. Olavus Petris kommentar från 1500-talet är en senare tolkning och togs inte ut.
- **Innehåll:** påståendena gäller ärekränkning (okvädinsord), tvekamp och dråp. Den som faller i tvekampen ligger ogill, och den som uteblir från tvekampen förlorar rätten att gå ed och vittna.
- **Plats:** Västergötland, enligt verkbeskrivningen.

## 2. Begrepp

Begreppsregistret byggdes ut i två omgångar, direkt i `begreppsregister.py`. Koden är redovisningen. Varje begrepp har termer och, där sådana finns, Schlyters och Söderwalls ordboksartiklar.

- **Första omgången:** brottsrubriceringar, påföljder, jäv och oväld, statsrätt (konungaval, eriksgata) och förfarande.
- **Andra omgången:** 24 begrepp som extraktionen visat att den saknade. Exempel är dulgadråp, försåt, rådsbane, hållbane, tvebot, mordgäld, förverkat gods, sägnarting, kungsnämnd, räfst, järnbörd, fiendskap och lösker man.
- **Normalisering:** de fria värdena i lagfilerna byttes sedan mot de nya begreppen av tre delagenter. Uppdragen är `016`–`018`, och instruktionen är [NORMALISERING_version_1](specifikationer/NORMALISERING_version_1.md).
- **Senare tillägg:** `begrepp:arvinge` kom till efter kontrollen, sedan det visat sig att `begrepp:arv` betyder egendom och inte arvingarna.

## 3. Personerna bakom lagarna

Specifikationen lät delagenterna skriva den som stiftat eller stadfäst en lag med ämbetet som subjekt och namnet i värdet, till exempel `begrepp:kung` med "=kung Birger stadfäste lagen". Huvudsessionen bytte sedan ämbetet mot personens entitet där lagtexten namnger personen. Det gjordes för 31 påståenden. Personerna togs ur auktoritetslistorna, eller ur SDHK:s personregister för lagmännen.

| person | i |
|---|---|
| Birger Magnusson | UL (hskr A och B), YVgL, DL, VmL |
| Magnus Eriksson | SdmL |
| Birger jarl | ÖgL; Erik den helige, Birger jarl och Magnus Ladulås i UL:s prolog |
| lagman Birger Persson och Lars Ulfsson | UL |
| Viger spa | UL:s prolog (ny entitet) |
| Erik av Pommern, Kristofer av Bayern och Karl IX | KrL (Karl IX ny entitet) |
| Erik Magnusson | MESt |
| Magnus Ladulås | Vidhemsprästens anteckningar (Alsnö stadga) |

Några lagstiftare kopplades inte, eftersom identiteten är osäker: "kung Erik" i ÖgL och biskoparna i Alsnö stadga. De står kvar med ämbetet som subjekt och namnet i värdet.

## 4. Kontrollens resultat

Den oberoende kontrollen har instruktioner och beslut i `oberoende_extraktion/`. Delagenternas bedömningar har uppdragen `019`–`025`. Huvudsessionen förde sedan in resultatet i lagfilerna:

- **Stickprovet:** 21 påståenden som ChatGPT hittat och som saknades lades till, och tre som låg utanför ämnena togs bort. Underlaget är `oberoende_extraktion/jamforelse_lagar/beslut.md`.
- **Hela materialet:** delagenternas beslut om att lägga till (189), rätta (58) och ta bort (67) fördes in med [hjalpskript/genomfor_bedomning.py](hjalpskript/genomfor_bedomning.py). Två avsteg gjordes:
  - kopplingen till Magnus Ladulås i Alsnö stadga behölls, mot en delagents förslag,
  - `begrepp:arv` som mottagare ersattes överallt med `begrepp:arvinge`.

  Varje ändring står i `oberoende_extraktion/jamforelse_lagar_hela/genomforda_andringar.md`.
- **Principfrågorna:** de 45 osäkra fallen avgjordes av användaren, och besluten fördes in för hand. Besluten står i `oberoende_extraktion/jamforelse_lagar_hela/beslut.md`, och ändringarna i `principbeslut_logg.json`.

Tillagda och rättade påståenden har en anmärkning om att de kommer ur den oberoende kontrollen.

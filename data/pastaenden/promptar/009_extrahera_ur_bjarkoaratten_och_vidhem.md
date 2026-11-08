# Extrahera ur Bjärköarätten och Vidhem

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/bjarkoaratten.json`, `data/pastaenden/lagar/vidhemsprastens_anteckningar.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt, inklusive avsnittet "Särskilda regler för vissa verk". Läs den först.

Uppdrag: två verk, en fil per verk. Läs hela texten (båda är ca 30 000 tecken).
1. Bjärköarätten, verk-id `verk:lag:bjarkoaratten`. Plats: `plats:sdhk:stockholm` (texten är bevarad som Stockholms stadsrätt; skriv det i filens beskrivning). Fil: <projektmapp>/data/pastaenden/lagar/bjarkoaratten.json
2. Vidhemsprästens anteckningar, verk-id `verk:lag:vidhemsprastens_anteckningar`. Plats: `plats:sdhk:vastergotland`. Fil: <projektmapp>/data/pastaenden/lagar/vidhemsprastens_anteckningar.json. Konunga-, lagmans- och biskopslängderna är redan uttagna ur andra verk; ta här bara ut rättsliga notiser om ämnena. Hittar du inget om ämnena skriver du en fil med tom lista och säger det.

Kontrollera varje fil med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen för varje verk.
````

## Delagentens slutrapport

Båda filerna är skrivna och `pastaenden_fil.py --kontrollera` ger inga fel. Ingenting är inläst i databasen och inga andra filer är ändrade. Ett eget skript bekräftade att varje citat står ordagrant i sin passage och att inga påståenden är dubbletter.

**1. Bjärköarätten**
Fil: <projektmapp>/data/pastaenden/lagar/bjarkoaratten.json
Plats: `plats:sdhk:stockholm`. Beskrivningen säger att texten är bevarad som Stockholms stadsrätt.

- **Antal påståenden:** 47 i alla. Dråp och mord 36, edsöre 8 (hemsökn, våld i kyrka, våldtäkt), jäv/nämnd 3 (hur nämnden utses och kravet på bymän och rådmän), stiftare 0.
- **Lästa flockar:** hela texten, BjR 1–41. Påståenden kommer ur BjR 12, 14, 15, 21 och 36.
- **Osäkra läsningar:**
  - "hwarn wæghin" (sex mäns vittne åt vardera hållet).
  - "raþi halwi næmþ hwar þeræ", tolkat som att vardera parten utser hälften av de tolv.
  - "doz drapum".
  - "forgauor", tolkat som gift och fört under mord.
  - BjR 15: att mannen har makt över horkarlens liv är fört som `ogild`.
- **Begrepp som saknades:** inga utöver dem som spec:en tillåter för städer (`stad`, `fogde`). "Treskifte" och "tvåböte" (dubbel bot) står som fria värden.
- **För jämförelsen:** boten delas mellan målsäganden och "fogden och staden", inte häradet. Det heter edsöre bara om hemgång och om våld i kyrka. Ena halvan av edsöresboten, 40 mark, går till kungen särskilt och den andra till treskifte. Flera dråp ger dubbel bot: i badstuga, i försåt, på en kvinna, på stadens utsände. Tolv rådmän står i edgärden.

**2. Vidhemsprästens anteckningar**
Fil: <projektmapp>/data/pastaenden/lagar/vidhemsprastens_anteckningar.json
Plats: `plats:sdhk:vastergotland`. Filen har innehåll, alltså ingen tom lista.

- **Antal påståenden:** 24 i alla. Dråp 5 (lejt dråp, dråp i kyrka), edsöre 11 (avskriften av Alsnö stadga 1285), jäv 5 (domarregeln), stiftare 3. Stiftarna är kung Magnus två gånger och biskoparna i Alsnö stadga. Lagmanslängden är inte uttagen.
- **Lästa flockar:** hela texten.
- **Viktigt om passagerna:** passagen `vidhemspr_4` rymmer i ett stycke domarregeln, sockenindelningen, alla tre längderna, stöldflockarna och inledningen till Magnus brev.
- **Osäkra läsningar:**
  - "vgillær" (den lejde dråparen), tolkat som ogill.
  - Domarregelns fyra hinder (kärlek, hat, gåvor, rädsla) står som `diskvalificerar` för `domare`, men de är en förmaning, inte en formell jävsregel. Det står i anmärkningarna.
  - Det förverkade godet vid edsöre har `begrepp:edsore` som subjekt, eftersom det saknas ett begrepp för förverkat gods.
- **Begrepp som saknades:** förverkat gods, grid ("gangær a gruþ"), riddare.
- **Utelämnat:** skrokvittne (falskt vittne: 3 mark delat mellan biskop, kung och härad) och nämnden i stöldmål. De ligger utanför ämnena.
- **För jämförelsen:** i Alsnö stadga skiftas godset i tre lotter, till kung, härad och saksökare. Därtill kommer fredlöshet tills den skadade ber för gärningsmannen, och 40 mark till kungen. Hel häradsnämnd prövar målet, med motiveringen att stadgan ska hållas lika över hela riket.

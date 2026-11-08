# Uppdragen och metoderna bakom påståendena

Här redovisas hur de påståenden som inte är regelbaserade togs fram. Det gäller lagpåståendena i `data/pastaenden/lagar/` och Västgötalagens längder i `data/pastaenden/`. Underlaget räcker för att kontrollera arbetet eller göra om det.

Arbetet gjordes antingen av delagenter med ett eget uppdrag eller direkt av huvudsessionen. Alla körde på samma modell, Claude Opus 5.5 (`claude-opus-5-5`). Uppdragen är återskapade ordagrant ur sessionsloggarna. Där inget uppdrag fanns beskriver en metodbeskrivning, skriven i efterhand, hur arbetet gick till.

De regelbaserade påståendena ur SDHK, DF, DN och DI redovisas av sin kod, till exempel `pastaenden_sdhk.py` och `dn_regester.py`. Hygelac-kretsen är handregistrerad i `pastaenden_hygelac.py`.

## Innehåll

- **`NNN_….md`** innehåller ett uppdrag per delagent, i den ordning de gavs:
  - `001`–`015`: extraktionen ur lagarna, en eller flera lagar per delagent,
  - `016`–`018`: normaliseringen, där fria värden byttes mot de nya begreppen,
  - `019`–`025`: bedömningen av skillnaderna mot Codex oberoende extraktion.

  Varje fil anger modellen, specifikationen delagenten läste, utfilerna, uppdraget ordagrant och delagentens slutrapport. Slutrapporten sammanfattar vad delagenten gjorde och vilka fall den var osäker på.
- **`specifikationer/`** innehåller de instruktioner som uppdragen hänvisar till, i den version delagenterna faktiskt läste:
  - `SPEC_version_1.md` gällde den första omgången lagar och Hednalagen,
  - `SPEC_version_2.md` gällde den andra omgången, med särskilda regler för Grágás, Kristoffers landslag och stadslagarna,
  - `NORMALISERING_version_1.md` gällde normaliseringen.

  Instruktionen för bedömningen är `oberoende_extraktion/jamforelse_lagar_hela/BEDOMNING.md`.
- **`metod_vastgotalagens_langder.md`** beskriver längdernas grundpåståenden och gärningar, som huvudsessionen tog ut själv.
- **`metod_lagar_huvudsessionen.md`** beskriver det i lagarbetet som huvudsessionen gjorde själv: Hednalagen, begreppen, kopplingen av personerna bakom lagarna och införandet av kontrollens resultat.
- **`hjalpskript/`** innehåller de hjälpskript som användes:
  - `lagtext.py` skrev ut lagtexten för de flockar delagenten valde,
  - `genomfor_bedomning.py` förde in bedömningarna i lagfilerna.
- **`INDEX.md`** visar för varje påståendefil vilka uppdrag och metodbeskrivningar som ligger bakom den.

Den oberoende kontrollen redovisas för sig i `oberoende_extraktion/`. Där finns ChatGPT:s och Codex instruktioner, jämförelserna och besluten.

## Platshållare

Lokala sökvägar är ersatta med platshållare. Uppdragen är i övrigt ordagranna.

- `<projektmapp>` är projektets rotmapp.
- `<arbetsmapp>` är den tillfälliga arbetsmapp där delagenterna lade sina hjälpfiler.
- `<produktionsmapp>` är mappen med den driftsatta servern.
- `python` står för projektets Python-miljö.

Hjälpfilerna i arbetsmappen finns inte kvar. Det gäller också normaliseringsagenternas ändringsloggar. Ändringarna syns i stället i påståendefilerna, och agenternas slutrapporter sammanfattar dem.

## Nya påståendesamlingar

Varje ny påståendesamling som tas fram med språkmodell redovisas här på samma sätt:

- ett uppdrag per delagent som en egen fil `NNN_<jobb>.md`, i löpnummerordning efter de befintliga, med modell, specifikation och utfiler överst, sedan uppdraget ordagrant och delagentens slutrapport;
- specifikationen i `specifikationer/`, med en ny version varje gång den ändras;
- hjälpskripten i `hjalpskript/`;
- en metodbeskrivning `metod_<arbete>.md` när arbetet görs utan delagent;
- en rad i `INDEX.md` för varje ny eller ändrad påståendefil.

Uppdraget sparas när jobbet startas, inte efteråt. Tid och sessions-id tas inte med.

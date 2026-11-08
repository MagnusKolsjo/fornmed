# Normalisering: fria värden till begrepp i lagfilerna

Lagfilerna i `<projektmapp>/data/pastaenden/lagar/` togs ut innan några begrepp fanns i registret. Där skrev extraktionen ett fritt värde (`=…`) eller använde ett för allmänt begrepp. Nu finns begreppen, och din uppgift är att byta till dem där det är entydigt rätt.

Filformatet beskrivs i `<arbetsmapp>/lagpilot/SPEC.md`. Varje påstående är `[passage, subjekt, predikat, objekt, plats, citat, anmärkning]`.

## Vad du får ändra

Bara **subjekt** och **objekt**, och bara till ett id i listan nedan.

- Ändra aldrig passage, predikat, plats, citat eller anmärkning.
- Ett fritt värde blir `begrepp:X|<samma text>`. Texten behålls oförändrad efter `|`.
- Ett objekt som redan är `begrepp:Y|text` får bli `begrepp:X|text` om X är det rätta begreppet.
- Lägg aldrig till eller ta bort påståenden.

## Nya begrepp

| id | när |
|---|---|
| `begrepp:forverkat_gods` | den dömdes egendom som förverkas och delas. Som **subjekt** i `tillfaller` när det som delas är godset (i dag ofta `begrepp:boter`, `begrepp:fredloshet` eller `begrepp:edsore` som subjekt med godset i värde eller anmärkning). Som **objekt** i `paforljd` när påföljden är att godet förverkas. |
| `begrepp:radsbane`, `begrepp:hallbane`, `begrepp:asyna_man` | som **subjekt** när påståendet gäller rådsbanens, hållbanens eller den åsyna mannens påföljd eller bevis (i dag ofta `begrepp:drap` med rådsbane i värdet) |
| `begrepp:dulgadrap`, `begrepp:forsat`, `begrepp:fridsbrott`, `begrepp:orbotamal` | som **subjekt** när påståendet gäller just dulgadråp (okänd gärningsman, dulsmål), dråp i försåt, ett fridsbrott eller orbotamål |
| `begrepp:tvebot`, `begrepp:trebot`, `begrepp:mordgald`, `begrepp:sporgald`, `begrepp:tockabot` | som **objekt** i `paforljd` när påföljden är just den boten, och som **subjekt** i `tillfaller` när det som delas är den boten. "Tack" eller "þokke" till kungen eller herren är `tockabot`. |
| `begrepp:sagnarting`, `begrepp:kungsnamnd`, `begrepp:rafst`, `begrepp:jarnbord`, `begrepp:trygd`, `begrepp:fridsbon`, `begrepp:borgesman` | som **objekt** i `handlaggs_vid` och `kraver`, eller som subjekt när påståendet gäller förfarandet självt. Räfsteting och kungens räfst är `rafst`. |
| `begrepp:kyrka`, `begrepp:hustru` | som **objekt** i `tillfaller` när mottagaren är kyrkan eller hustrun |
| `begrepp:losker_man`, `begrepp:fiendskap` | som **subjekt** i `diskvalificerar` när jävsgrunden är att vara lösker eller utan fast bo, respektive ovänskap |

## Jävsgrunden som subjekt

I `diskvalificerar` ska subjektet vara jävsgrunden och objektet rollen. Har extraktionen `begrepp:jav` som subjekt och grunden i värdet, flytta grunden till subjektet när den är något av följande:
`begrepp:frandskap`, `begrepp:svagerskap`, `begrepp:muta`, `begrepp:fiendskap`, `begrepp:losker_man`, `begrepp:fredloshet` (fredlös eller biltog), `begrepp:tral` (ofri eller träl).
Låt `begrepp:jav` stå kvar när grunden är något annat, till exempel kön, ålder, egen sak, partiskhet eller att ha stått i en tidigare ed.

## Regler

- Byt bara när det är entydigt. Är du osäker, låt påståendet vara och notera det i loggen.
- Ett byte får inte ge två påståenden med samma passage, predikat, subjekt och objekt; kontrollen avvisar det. Behåll då originalet och notera det.
- Kontrollera varje fil efter ändringarna tills inga fel återstår:
  `cd <projektmapp> && python pastaenden_fil.py --kontrollera data/pastaenden/lagar/<fil>.json`
  Läs inte in i databasen.
- Skriv om filen med samma struktur och samma nycklar. Ett påstående per rad går bra.

## Logg

Skriv en ändringslogg till den fil uppdraget anger. Logga varje ändring som en rad i en markdowntabell:

`| fil | passage | predikat | före | efter | skäl |`

Lista därefter de fall där du var osäker och lät bli.

Svara till sist med antal ändringar per fil och per nytt begrepp, och de viktigaste osäkra fallen. Högst 200 ord.

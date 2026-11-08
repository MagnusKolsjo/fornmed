# Metod: Västgötalagens längder

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/pastaenden/vastgotalagens_langder.json` (166 påståenden), `data/pastaenden/vastgotalagens_langder_garningar.json` (56 påståenden)
- Kontroll: `oberoende_extraktion/PROMPT.md` och `oberoende_extraktion/garningar/PROMPT.md`, med jämförelserna `jamforelse.md` i samma mappar

Påståendena togs inte ut av en delagent med ett uppdrag. Huvudsessionen gjorde arbetet direkt, och det fanns därför ingen prompt att spara. Den här beskrivningen är skriven i efterhand ur arbetsloggen.

## Underlag

- **Källa:** konunga-, lagmans- och biskopslängden i Holm B 59 (1320–1335), i Collin & Schlyters utgåva (1827) efter transkriptionen på svenska Wikisource. Databasen har den som 53 poster: en per kung, lagman och biskop.
- **Läsningen:** alla poster lästes i sin helhet, med den fornsvenska texten och den svenska maskinöversättningen intill. Översättningen användes bara som läshjälp. Varje citat är ur originaltexten.
- **Identiteter:** personerna identifierades mot projektets auktoritetslistor, `data/auktoriteter/regenter.json` och `data/auktoriteter/biskopar.json`, som har fasta id:n och Wikidata-id. Det gav samma entitet som i SDHK. Platserna slogs upp i databasens platsregister. Där en kungs identitet behövde stöd kontrollerades den mot svenska Wikipedia.

## Grundpåståendena (166)

Predikaten och deras antal:

| predikat | antal |
|---|---|
| `innehar_ambete` | 56 |
| `eftertrader` | 51 |
| `begravd_i` | 20 |
| `dor` | 15 |
| `foralder_till` | 10 |
| `fodd` | 5 |
| `dodar` | 4 |
| `syskon_till` | 3 |
| `styr_over` | 2 |

Reglerna:

- **Citat:** ett påstående per uppgift, med det kortaste ordagranna citat som täcker den. Laddaren `pastaenden_fil.py` kontrollerar att citatet står i passagen.
- **`eftertrader`** följer längdens numrering ("Annar konongær war …"). Det säger inget om att ämbetet övergick direkt. Där längden räknar en kung utan egen post, som Magnus Henriksson som den fjortonde, följer påståendena numreringen och anmärkningen säger det.
- **Plats:** kungarna, lagmännen och biskoparna får som plats det rike, landskap eller säte som längden avser, också där posten inte nämner det.
- **Dödsuppgifter:** dödsorsak och dödsplats skrivs som fritt värde på modern svenska, till exempel "förgiftad med en ond dryck". Platsen står bara där texten anger den. En underförstådd plats har en anmärkning.
- **Identifieringar:** där längden inte ger tillnamn, som "Erekær konongær", motiveras identifieringen i anmärkningen. Två identifieringar är registrerade som egna poster.

## Gärningarna (56)

Gärningarna togs ut i en andra genomgång, sedan predikaten för gärningar hade lagts in i vokabulären: grunda, låta bygga, viga, döpas av, stifta lag, fastställa gräns, införa pålaga, erövra, förlora, fly till, skänka, mista ämbete, döma och härkomst. De står i en egen fil, så att de kunde kontrolleras och jämföras för sig.

Reglerna:

- Subjektet är den som handlar. Står den som handlar inte i texten tas gärningen inte ut.
- Kyrkor är institutioner. Kyrkogårdar, broar och vägar är platser.
- Flera gärningar av samma slag i en post, till exempel flera byggen, får var sitt påstående med eget citat.
- Personer och ämbeten står i grundfilen. Gärningsfilen lägger bara till de platser och institutioner som gärningarna behöver.

## Kontroll

ChatGPT gjorde båda filerna en gång till, oberoende och med samma regler. Uppdragen står i `oberoende_extraktion/PROMPT.md` och `oberoende_extraktion/garningar/PROMPT.md`.

- **Grundpåståendena:** de två versionerna var överens om 157 av 162 påståenden.
- **Gärningarna:** skillnaderna var till största delen modelleringsfrågor.
- **Avgörandet:** användaren avgjorde skillnaderna, och rättelserna fördes in. Besluten står i jämförelsefilerna.

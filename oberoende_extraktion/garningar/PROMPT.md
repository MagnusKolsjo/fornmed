# Oberoende extraktion av gärningar ur Västgötalagens längder

Du ska ta ut **gärningar** ur tre fornsvenska förteckningar i Västgötalagens handskrift Holm B 59 från omkring 1320–1335: konungalängden, lagmanslängden och biskopslängden. Exempel på gärningar är grundanden, byggen, vigningar, gåvor, lagstiftning och erövringar. Resultatet blir en JSON-fil. Den ska jämföras med en annan extraktion som gjorts oberoende av din, så arbeta bara utifrån texten och reglerna nedan. Läs inga andra filer än de två som nämns här.

Personernas ämbeten, släktskap, födelse, död och gravplatser är redan uttagna. Ta **inte** ut dem igen.

## Filer

- `indata_vastgotalagens_langder_garningar.json` innehåller allt du behöver:
  - `passager` är de 54 posterna i fornsvensk originaltext,
  - `kandidater` är personer, platser, institutioner och ämbeten med fasta id:n, bland dem alla personer i längderna,
  - `predikat` är de tillåtna predikaten.
- `kontrollera.py` kontrollerar din fil. Kör det och rätta tills det inte rapporterar några fel:
  ```
  python kontrollera.py indata_vastgotalagens_langder_garningar.json utdata_vastgotalagens_langder_garningar.json
  ```

Skriv resultatet till `utdata_vastgotalagens_langder_garningar.json`.

## Utdatans form

```json
{
 "beskrivning": "En mening om hur extraktionen gjordes.",
 "extraherad_av": "språkmodell (ange modell) – oberoende kontrollextraktion av gärningar",
 "passager": {"K": "vastgotalagens_konungalangd:", "L": "vastgotalagens_lagmanslangd:", "B": "vastgotalagens_biskopslangd:"},
 "entiteter": [
  ["plats:ortnamn", "plats", "Ortnamn på modern svenska", "Kort beskrivning", null]
 ],
 "identifieringar": [],
 "pastaenden": [
  ["B4", "person:subjekt", "predikat", "objekt", "plats eller null", "ordagrant citat", "anmärkning (valfri)"]
 ]
}
```

- **passage** skrivs kort som `K4`, `L13` eller `B2`.
- **subjekt** är den som utför gärningen, alltid ett entitets-id.
- **objekt** är ett entitets-id eller ett fritt värde som inleds med `=` och är skrivet på modern svenska.
- **plats** är ett entitets-id eller `null`.
- **citat** är ett ordagrant utdrag ur postens fornsvenska originaltext. Det ska vara så kort som möjligt men täcka gärningen. Kopiera tecken för tecken, med interpunktion och felstavningar som de står. Normalisera eller sätt ihop utdrag aldrig. Har en post flera gärningar av samma slag, till exempel flera byggen, får varje gärning ett eget påstående med sitt eget citat.
- **anmärkning** är valfri. Använd den för vad objektet är när det inte framgår av id:t (en kyrka, en bro, klockor), och för tolkningar och osäkra läsningar.

## Entiteter

- Använd kandidaternas id:n när personen, platsen eller institutionen finns bland dem.
- Saknas en plats eller institution definierar du den under `entiteter`. Id:t ska vara läsbart, med gemener och understreck, t.ex. `plats:ortnamn` eller `institution:namn_pa_kyrka`. Använd `null` som wikidata-id om du inte är säker.
- Samma plats eller institution i flera poster ska ha samma id.

## Predikat för gärningar

| predikat | används för | objekt | plats |
|---|---|---|---|
| `grundar` | grundar ett kloster, stift, en kyrka, skola, stad eller borg | det grundade | orten |
| `later_bygga` | låter bygga eller fullborda kyrka, bro, väg, borg | byggnaden eller platsen | orten om den inte är objektet |
| `viger` | viger kyrka, kyrkogård eller person | det vigda | orten om den inte är objektet |
| `dops_av` | subjektet döps av objektet | den som döper | dopplatsen |
| `offrar`, `forrattar_rit` | hedniska offer och riter | guden eller `=` riten | kultplatsen |
| `stiftar_lag` | gör, ändrar eller förkunnar lag | `=` vad som görs med lagen | landet |
| `faststaller_grans` | drar gräns mot ett annat rike eller land | det andra riket | – |
| `indelar` | delar in ett rike eller land i områden | det indelade | – |
| `infor_palaga` | inför skatt, tionde eller avgift | `=` pålagan | landet |
| `utnamner` | utnämner någon | den utnämnde | ansvarsområdet |
| `mister_ambete` | förlorar ämbete eller titel | ämbetet | landet |
| `domer`, `avrattar`, `fangslar`, `landsforvisar`, `benadar` | rättskipning | den som drabbas eller `=` utfallet | – |
| `erovrar`, `forlorar` | erövrar eller förlorar ett rike, land, en borg eller ett slag | det erövrade eller förlorade | – |
| `flyr_till` | flyr till | landet eller orten | – |
| `skanker` | skänker något | mottagaren | orten |
| `overlater`, `saljer`, `byter`, `pantsatter`, `testamenterar`, `upplater` | överlåtelser av egendom | motparten | orten |
| `harkomst` | härstammar från | landet, orten eller folket | – |

Regler:

- **Aktiva predikat:** subjektet är den som handlar. Nämner texten inte den som handlar tar du inte ut gärningen. Undantaget är `mister_ambete`, där subjektet är den som förlorar ämbetet.
- **Bara gärningar:** ta inte ut omdömen om karaktär ("god", "grym"), fromma önskningar, ämbeten, släktskap, födelse, död eller begravning.
- **Bara texten:** lägg aldrig till uppgifter som inte står i texten. Kunskap får bara användas för att identifiera personer och platser.

## Arbetsordning

1. Läs alla poster innan du börjar.
2. Ta ut gärningarna post för post.
3. Kör `kontrollera.py` och rätta alla fel.
4. Lämna filen när kontrollen inte rapporterar några fel. Skriv sist en kort sammanfattning av vilka avgöranden du var osäker på.

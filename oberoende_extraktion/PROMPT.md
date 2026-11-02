# Oberoende extraktion av påståenden ur Västgötalagens längder

Du ska ta ut påståenden ur tre fornsvenska förteckningar. De finns i Västgötalagens handskrift Holm B 59 från omkring 1320–1335: konungalängden, lagmanslängden och biskopslängden. Resultatet blir en JSON-fil. Den ska jämföras med en annan extraktion som gjorts oberoende av din, så arbeta bara utifrån texten och reglerna nedan. Läs inga andra filer än de två som nämns här.

## Filer

- `indata_vastgotalagens_langder.json` innehåller allt du behöver:
  - `passager` är de 54 posterna med id, adress och fornsvensk originaltext,
  - `kandidater` är personer, platser och ämbeten som redan har fasta id:n i databasen,
  - `predikat` är de tillåtna predikaten.
- `kontrollera.py` kontrollerar din fil. Kör det och rätta tills det inte rapporterar några fel:
  ```
  python kontrollera.py indata_vastgotalagens_langder.json utdata_vastgotalagens_langder.json
  ```

Skriv resultatet till `utdata_vastgotalagens_langder.json`.

## Utdatans form

```json
{
 "beskrivning": "En mening om hur extraktionen gjordes.",
 "extraherad_av": "språkmodell (ange modell) – oberoende kontrollextraktion",
 "passager": {"K": "vastgotalagens_konungalangd:", "L": "vastgotalagens_lagmanslangd:", "B": "vastgotalagens_biskopslangd:"},
 "entiteter": [
  ["person:exempel_id", "person", "Namn på modern svenska", "Kort beskrivning", null]
 ],
 "identifieringar": [
  ["person:exempel_id", "person:kandidat_id", "sannolik", "Motivering"]
 ],
 "pastaenden": [
  ["K4", "person:subjekt", "predikat", "objekt", "plats eller null", "ordagrant citat", "anmärkning (valfri)"]
 ]
}
```

- **passage** skrivs kort som `K4` (konungalängden post 4), `L13` eller `B2`. Det fullständiga id:t står i indata.
- **subjekt** är ett entitets-id.
- **objekt** är ett entitets-id eller ett fritt värde som inleds med `=`, t.ex. `"=dör i strid"`. Fria värden skrivs på modern svenska.
- **plats** är ett entitets-id eller `null`.
- **citat** är ett ordagrant utdrag ur postens fornsvenska originaltext. Det ska vara så kort som möjligt men täcka det påståendet bygger på. Kopiera tecken för tecken, med interpunktion, `ſ`, `ð`, `þ` och felstavningar som de står. Normalisera, översätt eller sätt ihop utdrag ur olika delar av texten aldrig. Om påståendet bygger på två ställen väljer du det avgörande och förklarar resten i anmärkningen.
- **anmärkning** är valfri. Skriv en anmärkning när påståendet bygger på en tolkning: en underförstådd plats, vem ett "hans" syftar på, en ordning som bara följer av numreringen, eller en osäker läsning.

## Entiteter

- Använd kandidatens id när du är säker på att personen, platsen eller ämbetet är densamma, t.ex. en kung vars identitet är okontroversiell eller en biskop med samma namn och plats i ordningen.
- Saknas personen eller platsen bland kandidaterna definierar du en ny entitet under `entiteter`. Id:t ska vara läsbart, med gemener och understreck, t.ex. `person:ragnar_fran_ortnamn` eller `plats:ortnamn`. Använd `null` som wikidata-id om du inte är säker.
- Är identiteten med en kandidat sannolik men inte säker definierar du en egen entitet för längdens person och lägger identifieringen under `identifieringar` med bedömningen `saker`, `sannolik` eller `mojlig` och en motivering. Det gäller t.ex. när längden ger ett annat namn än den gängse identifieringen.
- Samma person i flera poster ska ha samma id.

## Vad som ska tas ut

Ta bara ut följande typer av påståenden:

| predikat | används för | objekt | plats |
|---|---|---|---|
| `innehar_ambete` | att personen är kung, lagman, biskop, ärkebiskop osv. | ämbetets id, t.ex. `begrepp:kung` | riket, landskapet eller sätet |
| `eftertrader` | att personen följer efter föregångaren i längden | föregångarens id | – |
| `foralder_till` | förälder till | barnets id (subjektet är föräldern) | – |
| `syskon_till` | syskon till | syskonets id | – |
| `fodd` | födelse | `=` och kort beskrivning, t.ex. `=född i X` | födelseorten |
| `dor` | död | `=` och dödssättet, t.ex. `=dör i strid` | dödsplatsen om den anges |
| `dodar` | att subjektet dödar någon | den dödades id | platsen om den anges |
| `begravd_i` | gravplats | gravplatsens id | – |
| `styr_over` | att någon styr ett rike eller land | rikets eller landets id | – |

Regler:

- **`innehar_ambete`:** varje person i en längd får ett påstående. Platsen är det rike, landskap eller säte som längden avser, också när posten inte nämner det. Konungalängden gäller Sverige, lagmanslängden Västergötland och biskopslängden stiftet i Västergötland med säte i Skara, där längden inte säger något annat.
- **`eftertrader`:** följer längdens numrering ("den andre", "den tredje" …), inte historisk kunskap. Står ordningen i strid med historien skriver du det i anmärkningen men tar ändå ut påståendet som längden säger.
- **Inga gärningar:** ta inte ut kyrkbyggen, donationer, brobyggen, lagstiftning, omdömen om karaktär eller liknande.
- **Bara texten:** lägg aldrig till uppgifter som inte står i texten, även om du vet dem. Kunskap får bara användas för att avgöra vem en person är.
- **Subjektet i `dodar`:** saknar mördaren namn tar du ut ett `dor`-påstående för offret i stället, med dödssättet i objektet.

## Arbetsordning

1. Läs alla poster i en längd innan du börjar, så att du ser numreringen och vilka personer som återkommer.
2. Ta ut påståendena post för post.
3. Kör `kontrollera.py` och rätta alla fel. De vanligaste är citat som inte står ordagrant och entiteter som inte är definierade.
4. Lämna filen när kontrollen inte rapporterar några fel. Skriv sist en kort sammanfattning av vilka avgöranden du var osäker på.

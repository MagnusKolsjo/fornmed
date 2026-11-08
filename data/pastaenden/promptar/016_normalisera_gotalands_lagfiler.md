# Normalisera Götalands lagfiler

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/NORMALISERING_version_1.md](specifikationer/NORMALISERING_version_1.md)
- Utfiler: `data/pastaenden/lagar/aldre_vastgotalagen.json`, `data/pastaenden/lagar/hednalagen.json`, `data/pastaenden/lagar/lydekini.json`, `data/pastaenden/lagar/ostgotalagen.json`, `data/pastaenden/lagar/ostgotalagen_fragment.json`, `data/pastaenden/lagar/smalandslagens_kyrkobalk.json`, `data/pastaenden/lagar/vidhemsprastens_anteckningar.json`, `data/pastaenden/lagar/yngre_vastgotalagen.json`

## Uppdraget till delagenten

````text
Följ instruktionen i specifikationer/NORMALISERING_version_1.md exakt. Läs den först.

Dina filer (i <projektmapp>/data/pastaenden/lagar/): hednalagen.json, aldre_vastgotalagen.json, vidhemsprastens_anteckningar.json, lydekini.json, yngre_vastgotalagen.json, ostgotalagen.json, ostgotalagen_fragment.json, smalandslagens_kyrkobalk.json.

Rör inga andra filer. Logg: <arbetsmapp>/lagpilot/normalisering_gotaland.md
````

## Delagentens slutrapport

Klart. Jag har gjort 69 ändringar i fyra av de åtta filerna. Alla åtta filer går igenom `pastaenden_fil.py --kontrollera` utan fel. Inga påståenden är tillagda eller borttagna, och bara subjekt och objekt är ändrade. Inget är inläst i databasen.

**Per fil:**
- Äldre Västgötalagen: 12
- Yngre Västgötalagen: 27
- Östgötalagen: 25
- Vidhemsprästens anteckningar: 5
- Hednalagen, Lydekini, Östgötalagen (fragment) och Smålandslagens kyrkobalk: 0

**Per begrepp:** forverkat_gods 31, dulgadrap 12, radsbane 5, mordgald 5, rafst 4, hallbane 2, hustru 2, losker_man 2, sagnarting 1, tvebot 1, tockabot 1, fiendskap 1. Dessutom två jävsgrunder flyttade till subjekt med befintliga begrepp: fredloshet 1 och tral 1.

**Viktigaste osäkra fallen:**
- **Ändrade trots tveksamhet:** Dråp i ölstuga och mellan byar är ändrade till dulgadrap, eftersom banemannen inte fås fram, men ordet dulgadråp står inte i texten. Vidhemsprästens "hat" är ändrat till fiendskap, men det står i domarregeln, som är en förmaning och ingen formell jävsregel.
- **Lämnade orörda:**
  - Åsyna mans bötesdelning (predikatet `tillfaller`).
  - Orbotamål som objekt, och "försåt" i edsöresdefinitionerna.
  - "Taki" (ÖgL Rb 6 och fragmentets stycke 10): ändrades inte till borgesman, eftersom citatet visar ett verb.
  - Jävspåståenden med flera grunder i samma påstående (träl, omyndig och fridlös tillsammans).

Loggen med alla ändringar och osäkra fall: <arbetsmapp>/lagpilot/normalisering_gotaland.md

Säkerhetskopior av originalfilerna ligger i <arbetsmapp>/lagpilot/norm_got/backup/

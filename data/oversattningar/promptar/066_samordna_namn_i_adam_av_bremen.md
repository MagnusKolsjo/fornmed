# Samordna namn i Adam av Bremen

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: `data/oversattningar/openmgh/adam_av_bremen__0-51.json`

## Uppdraget till delagenten

````text
Du ska samordna egennamnen i de svenska maskinöversättningarna av Adam av Bremens Gesta Hammaburgensis ecclesiae pontificum (huvudtexten), så att samma latinska namn återges likadant i alla fem filer. Fem olika agenter har översatt delarna och valt olika former, t.ex. Sueonia som både "Svearike" och "Svitjod", och Sliaswig som både "Slesvig" och "Schleswig".

Regel (se också punkten om egennamn i <projektmapp>/data/oversattningar/RIKTLINJER.md):
1. Vedertagna svenska former för nordiska orter, länder och folk: Birka, Sigtuna, Uppsala, Skara, Lund, Hedeby, Slesvig, Ribe, Århus, Skåne, Hälsingborg, Trondheim, svear, götar, daner, nordmän. Sueonia/Suedia/Suigia → Svitjod (genomgående). Nortmannia → Norge där sammanhanget är nordiskt, Normandie bara där det uttryckligen gäller normanderna i Frankrike; där det inte går att avgöra står "Nortmannia".
2. Städer (civitates/biskopsstäder) i nutida namn: Hamburg, Bremen, Köln, Rom, Magdeburg.
3. Mindre orter, gods, borgar, öar och folk utan vedertagen svensk form står i textens form (Iumne, Hulmo, Farria, Halsingland i textens stavning om texten skriver så, Wendila, Aestland, Pinnedi). Ingen modern identifiering av sådana namn.
4. Inga egna förklaringar eller identifieringar inom parentes, utom textens latinska namn eller term.

Filer (relativt <projektmapp>): data/oversattningar/openmgh/adam_av_bremen__0-51.json, __51-116.json, __116-168.json, __168-216.json, __216-235.json. Latinet hämtar du med
  python hjalpskript/kalltext.py verk:adam_av_bremen --fran 0 --till 235 --typer originaltext
från projektkatalogen (bara läsning).

Arbetssätt: samla alla namn per latinsk form över filerna, välj en form enligt regeln, och gör exakta strängbyten i rätt passage (kontrollera att strängen finns exakt en gång, och att varje fil efteråt har samma id-mängd). Ändra inget annat än namn och otillåtna parenteser. Arbeta i en egen katalog <arbetsmapp>/namn_adam/ (skapa den; importera inget från scratchpadens rot) och spara säkerhetskopior där innan du ändrar.

Rapportera: antal ändringar per fil och en lista över namn som förekom i flera former och hur de nu skrivs.
````

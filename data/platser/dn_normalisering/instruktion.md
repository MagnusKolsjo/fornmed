# Nutida namn för ortnamn i Diplomatarium Norvegicum

Varje rad i indatafilen är JSON med `namn` (utfärdandeorten som utgåvan skriver den), antal `brev`, årtal (`ar`)
och upp till två `exempel` ur breven. Föreslå ortens nutida namn så som det skrivs i dag i sitt land, så att
det kan slås upp i Kartverkets ortnamnsregister (Norge) eller Wikidata (övriga länder).

- Ange `land` som ISO 3166-1 alfa-2 (`no`, `se`, `dk`, `de`, `nl`, `be`, `gb`, `it`, `fr` …).
- Ange `typ`: `stad`, `socken`, `bygd`, `gard`, `borg`, `kloster`, `region` (landskap, härad, fylke) eller `okand`.
- För andra länder än Norge: ange Wikidatas Q-nummer i `wikidata` bara om du är säker; annars tomt.
- Gissa inte. Är orten okänd eller namnet för vanligt för att avgöras, ange `typ: okand` och lämna `nutida` tomt.
- `sakerhet`: `hog`, `medel` eller `lag`. `motivering`: högst 12 ord.

Exempel: "Eker" → Eiker, no, bygd. "Thelemarken" → Telemark, no, region. "Lynn" → King's Lynn, gb, stad.
"Köln v. Spree" → Cölln, del av Berlin: nutida "Berlin", de, stad.

Skriv JSON Lines, en rad per indatarad i samma ordning, med fälten `namn`, `nutida`, `land`, `typ`, `wikidata`,
`sakerhet`, `motivering`.

# Nutida namn för ortnamn i Diplomatarium Islandicum

Varje rad i indatafilen är JSON med `namn` (utfärdandeorten som den står i OCR-texten, ofta i dativ och med
läsfel: "Hólum", "Skálliolti", "Ókrum" för Ökrum, "Kaúpmannahöfn"), antal `brev`, ett årtal och upp till två
`exempel` (brevens isländska rubriker). Föreslå ortens nutida namn i nominativ, så som det skrivs i dag.

- `land`: ISO 3166-1 alfa-2 (`is`, `no`, `dk`, `de`, `gb` …).
- `typ`: `gard`, `kyrkostad`, `kloster`, `biskopssate`, `tingsplats`, `stad`, `region` eller `okand`.
- `syssla`: för isländska orter sýslan, med nutida namn (t.ex. "Skagafjarðarsýsla", "Árnessýsla"), om du vet den.
- `wikidata`: Q-nummer bara om du är säker; annars tomt.
- Gissa inte. Ett namn som finns på många gårdar och inte avgörs av exemplen ska ha `typ: okand` och tomt `nutida`.
- `sakerhet`: `hog`, `medel` eller `lag`. `motivering`: högst 12 ord.

Exempel: "Hólum" i biskopsbrev → Hólar í Hjaltadal, is, biskopssate, Skagafjarðarsýsla. "Öxarárþingi" och
"alþingi" → Þingvellir, is, tingsplats, Árnessýsla. "Kaúpmannahöfn'" → Kaupmannahöfn, dk, stad.

Skriv JSON Lines, en rad per indatarad i samma ordning, med fälten `namn`, `nutida`, `land`, `typ`, `syssla`,
`wikidata`, `sakerhet`, `motivering`.

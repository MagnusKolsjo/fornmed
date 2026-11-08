# Extrahera ur fyra mindre lagtexter

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/gutalagens_additamenta.json`, `data/pastaenden/lagar/lydekini.json`, `data/pastaenden/lagar/smalandslagens_kyrkobalk.json`, `data/pastaenden/lagar/upplandslagen_tillagg.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt. Läs den först.

Uppdrag: fyra mindre verk, en fil per verk. Läs hela texten i varje. Hittar du inget om ämnena i ett verk skriver du en fil med tom lista och säger det.
1. Smålandslagens kyrkobalk, `verk:lag:smalandslagens_kyrkobalk` (ca 18 000 tecken; dråp i kyrka, kyrkofrid, jäv i kyrkliga mål). Plats: `plats:sdhk:smaland`. Fil: <projektmapp>/data/pastaenden/lagar/smalandslagens_kyrkobalk.json
2. Gutalagens additamenta, `verk:lag:gutalagens_additamenta_enligt_am_54` (ca 7 000 tecken). Plats: `plats:gotland`. Fil: .../data/pastaenden/lagar/gutalagens_additamenta.json
3. Yngre Västgötalagens äldsta fragment, Lydekini excerpter och anteckningar, `verk:lag:yngre_vastgotalagens_aldsta_fragment_lydekini_excerpter_och_` (ca 40 000 tecken). Plats: `plats:sdhk:vastergotland`. Fil: .../data/pastaenden/lagar/lydekini.json
4. Tillägg till Upplandslagen, hskr A (Ups B 12), `verk:lag:tillagg_till_upplandslagen_hskr_a_ups_b_12` (ca 4 000 tecken). Plats: `plats:sdhk:upland`. Fil: .../data/pastaenden/lagar/upplandslagen_tillagg.json

(... står för <projektmapp>.)

Kontrollera varje fil med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med en kort sammanfattning enligt specifikationen för varje verk.
````

## Delagentens slutrapport

Alla fyra filerna är skrivna och klarar `pastaenden_fil.py --kontrollera` utan fel. Inget är inläst i databasen och inga andra filer är ändrade. Jag läste hela texten i varje verk, utan mönster eller `--sok`. Inget verk blev tomt.

**1. Smålandslagens kyrkobalk** – <projektmapp>/data/pastaenden/lagar/smalandslagens_kyrkobalk.json, 11 påståenden.
- **Antal:** dråp och kyrkofrid 10, jäv 1 (prästen nämner biskopens tolvmannanämnd och både biskopen och sockenmännen ska godta den), edsöre 0.
- **Flockar:** Kkb 1–18. Allt som togs ut står i Kkb 13.
- **Osäkert:** Hugg på kyrktrappan, i dörren, i kyrkan och vid altaret ger biskopssak från 0 öre till högst 3 marker. Att den huggne faller på trappan har jag tolkat som dråp, men texten säger bara "hugger", så jag satte `begrepp:sar` där blod stänker. Vad "morth" betyder bland biskopens värjomål är oklart. Läsningen "till næs fællæ" (hänskjuta till edgång) är också osäker.
- **Anmärkningsvärt:** Edgärden för de tre värjomålen tas uttryckligen bland den anklagades släkt ("kyni oc kunnum mannum"), alltså motsatsen till en jävsregel.
- **Utelämnat:** Kkb 4 säger att en präst inte får vara "moorthare eller mandrapære". Det är ett behörighetskrav för präster, inte jäv, så jag tog inte med det.

**2. Gutalagens additamenta** – <projektmapp>/data/pastaenden/lagar/gutalagens_additamenta.json, 9 påståenden om dråp.
- **Flockar:** stycke 1–16. Allt som togs ut står i stycke 3 och 5.
- **Innehåll:** En olärd prästson som dräper får själv akta sig för hämnd. Om en präst är målsägande ska bot bjudas genast och vid behov bäras fram på tinget. Hämnddråp efter erbjuden bot kostar full mansbot och 40 marker till landet. För två bröder, en lärd och en olärd, gäller särskilda regler om huvudlotten.
- **Motivering:** En präst får inte hämnas "vtan kristindomber warder spiltir" (utan att kristendomen fördärvas).
- **Osäkert:** vem som lägger fram och tar emot huvudlotten.

**3. Lydekini** – <projektmapp>/data/pastaenden/lagar/lydekini.json, 45 påståenden.
- **Antal:** dråp och mord 23, jäv, nämnd och mutor 17, edsöre 5.
- **Flockar:** hela verket. Påståendena kommer från Kb 52, Tillägg 1 (under Forn 15), Ab 8, Rb 15, Gb 2, Gb 2 (andra delen), Dr 7 och Forn 36.
- **Mutor:** Lagman, häradshövding och länsman som tar muta mister sitt ämbete och mutan går till kungen. En nämndeman böter 40 marker, och den som bevisar mutan får 13 marker och 8 örtugar.
- **Nämnden:** En tjänsteman får vara nämndeman bara med både böndernas och häradshövdingens vilja. Häradshövding som tvingar nämnden att fria böter 12 marker. Omyndig, träl och fridlös får inte stå i ed.
- **Dråp:** Dråp i kyrka ger 9 marker till biskopen.
- **Osäkert:** "häräzmanna mal", om 40-markersboten för "þiänestomaþir oc bonþe" gäller den som tar eller den som ger muta, och fortsättningen av ättebotstabellen i Dr 7.

**4. Tillägg till Upplandslagen (Ups B 12)** – <projektmapp>/data/pastaenden/lagar/upplandslagen_tillagg.json, 6 påståenden.
- **Antal:** edsöre 2 (att hysa fredlösa ger en bot per gärning), dråp 4 (dolt dråp ska "þræskiptæs", vem som räknas som dråpare, hundaret saklöst, 40 marker för att röva en dråpare från en annan).
- **Flockar:** Add. 1–18.
- **Osäkert:** om det är boten eller ansvaret som tredelas.

**Begrepp som saknades:** präst, prost, skrift (botgöring), kyrkofrid, frist eller grid, köpstad och tjänsteman. Jag skrev dem som fria värden. Barnamord står som `begrepp:mord`.

**Inför jämförelsen:** Kyrkofridsboten går till biskopen i både SmL (högst 3 marker) och Lydekini (9 marker för dråp i kyrka). Jäv motiveras ingenstans uttryckligen. Lydekini är det enda av de fyra verken med utförliga regler om mutor och om nämndens oväld mot häradshövdingen.

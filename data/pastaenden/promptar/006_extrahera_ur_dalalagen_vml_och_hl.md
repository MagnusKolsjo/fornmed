# Extrahera ur Dalalagen, VmL och HL

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_1.md](specifikationer/SPEC_version_1.md)
- Utfiler: `data/pastaenden/lagar/dalalagen.json`, `data/pastaenden/lagar/halsingelagen.json`, `data/pastaenden/lagar/yngre_vastmannalagen.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_1.md exakt. Läs den först.

Uppdrag: tre lagar, en fil per lag.
1. Dalalagen (Äldre Västmannalagen), verk-id `verk:lag:dalalagen_aldre_vastmannalagen`, balkarna ' Eb ' (Kunungs ezöre), ' Mb ' (Manhælghis balkir) och ' Tb ' (Þingh balkir). Plats: `plats:sdhk:dalarna`. Fil: <projektmapp>/data/pastaenden/lagar/dalalagen.json
2. Yngre Västmannalagen, verk-id `verk:lag:yngre_vastmannalagen_enl_holm_b_57`, flockarna utan balk och balkarna ' Kgb ' och ' Tb '. (Utgåvan saknar manhelgdsbalken.) Plats: `plats:sdhk:vastmanland`. Fil: <projektmapp>/data/pastaenden/lagar/yngre_vastmannalagen.json
3. Hälsingelagen, verk-id `verk:lag:halsingelagen`, flockarna utan balk och balkarna ' Kgb ', ' Mb ' och ' Tb '. Plats: `plats:sdhk:halsingland`. Fil: <projektmapp>/data/pastaenden/lagar/halsingelagen.json

Kontrollera varje fil med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med en sammanfattning enligt specifikationen för varje lag (högst 200 ord per lag).
````

## Delagentens slutrapport

Alla tre filerna klarar `pastaenden_fil.py --kontrollera` utan fel. Inget är inläst i databasen och inga andra projektfiler är ändrade. Filerna byggdes med ett eget hjälpskript i scratchpad (`<arbetsmapp>/lagpilot/bygg/`).

En sak att känna till inför de andra filerna: `_kort` i pastaenden_fil.py delar på kolon, så ett kolon i objektets värdedel klipper id:t. Två påståenden kolliderade därför av det skälet. Jag använder inga kolon i värden.

**1. Dalalagen** – <projektmapp>/data/pastaenden/lagar/dalalagen.json (87 påståenden)
- **Per ämne:** dråp 46, edsöre 31, jäv 9, stiftare 1.
- **Lästa flockar:** Eb 1–9, Mb 1–27, Tb 1–19. Eb 8 och sårflockarna togs inte med.
- **Osäkert:** "alle men/alli men" har jag tolkat som `landskap`. Om målsäganden i Tb 15 väljer edgärdsmän är oklart.
- **Begrepp som saknades:** förverkat gods (skrivet som `boter` med anmärkning), dulgadråp, dylsbot, fall och manhelgd som bötesposter.
- **Att jämföra:** Mansboten tredelas mellan kungen, målsäganden och "alli men". Vid fränddråp går manhelgden i stället till kungen, biskopen och hundaret. Biskopen tar tre marker av varje dråp. Hemsökn utan skada kostar sex marker. Vittnesjävet gäller bror och hushåll, och fattiga vittnen godtas uttryckligen. Kung Birger nämns i Tb 11.

**2. Yngre Västmannalagen** – <projektmapp>/data/pastaenden/lagar/yngre_vastmannalagen.json (41 påståenden)
- **Per ämne:** edsöre 30, jäv 7, dråp 3, stiftare 1.
- **Lästa flockar:** innehållsförteckning, prologen (stycke 1–5), Kgb 1–7 och Tb 1–23. Prologen nämner ingen stiftare.
- **Osäkert:** Tb 15, där tjugo marker för att dräpa en förrymd brottsling är en osäker läsning.
- **Begrepp som saknades:** skeppslag, förgörning (skrivet som `trolldom`) och kön som jävsgrund.
- **Att jämföra:** Hemsökn utan skada kostar tre marker, mot sex i Dalalagen. Vittnen måste äga minst tre markers egendom, vilket går emot Dalalagen. Domarna utses så att tolv män ur hundaret nämner två och kungen sätter domen i deras händer. Kung Birger nämns i Tb 13. Utgåvan saknar manhelgdsbalk, så dråpsreglerna fattas nästan helt.

**3. Hälsingelagen** – <projektmapp>/data/pastaenden/lagar/halsingelagen.json (81 påståenden)
- **Per ämne:** dråp 40, edsöre 33, jäv 6, stiftare 2.
- **Lästa flockar:** prologen (stycke 1–17), Kgb 1–11, Mb 1–38 och Tb 1–15.
- **Osäkert:** orden "wæghnær" och "wærold" i Mb 38. Början av Tb 1 saknas, så det framgår inte vem som väljer lagmannen.
- **Begrepp som saknades:** skeppslag, kungens are, tockabot och den dräptes herre som mottagare.
- **Att jämföra:**
  - Prologen säger att lagen satts av Gud och sedan av kungen, med samtycke av välborna män och allmogen.
  - Fjortonmannaed i stället för tolvmannaed.
  - Böterna på 140 marker delas så att målsäganden får 65, kungen 45 och skeppslaget 30.
  - Hela vådaboten på sju marker går till målsäganden.
  - Målsäganden väljer mellan hämnd och bot.
  - Fader, son och bror är jäviga som vittnen och i ed, och så är den som står i skrift.

# Oberoende extraktion av normpåståenden ur medeltida nordiska lagar

Du ska ta ut påståenden om **dråp**, **edsöre**, **jäv** och **lagstiftning** ur 24 flockar (lagkapitel) ur KrL, Grágás. Det här är del 8 av 9 av en genomgång av de medeltida svenska landskapslagarna, stadslagarna, landslagarna och isländska Grágás. Resultatet blir en JSON-fil. Den ska jämföras med en annan extraktion som gjorts oberoende av din, så arbeta bara utifrån texten och reglerna nedan. Läs inga andra filer än de två som nämns här.

## Filer

- `indata_del_08.json` innehåller allt du behöver:
  - `passager` är flockarna. Varje flock har lagens namn, adress, plats, språk och text. Texten är fornsvensk, utom Grágás som finns i dansk översättning.
  - `kandidater` är de begrepp, personer och platser du får använda, med fasta id:n och korta beskrivningar.
  - `predikat` är de tillåtna predikaten.
- `kontrollera.py` kontrollerar din fil. Kör det och rätta tills det inte rapporterar några fel:
  ```
  python kontrollera.py indata_del_08.json utdata_del_08.json
  ```

Skriv resultatet till `utdata_del_08.json`.

## Ämnen

1. **Dråp:** dråp med uppsåt och av våda, och dödande som är ogilt (utan bot), till exempel vid tvekamp, hemsökn eller av tjuv på bar gärning. Ta ut:
   - påföljd och belopp,
   - hur boten delas (kungen, häradet eller hundaret, målsäganden, ätten, biskopen),
   - var målet handläggs,
   - vilka bevis eller vilken ed som krävs,
   - lagens egna definitioner (vad som räknas som dråp, våda, nidingsverk).
2. **Edsöre:** kungens edsvurna frid, alltså edsöresbrotten (hemsökn, våldtäkt, dråp på ting eller i kyrka med flera). Ta ut påföljderna (fredlöshet, böter, förverkat gods), bötesdelningen, vem som dömer och lagens motivering om den finns.
3. **Jäv och oväld:** regler om vem som inte får vara domare, nämndeman, edgärdsman eller vittne, och varför: frändskap, svågerskap, egen sak, mutor, fiendskap. Ta också ut regler om hur nämnden eller edgärden utses, och eder som binder domare eller nämnd att döma rätt.

4. **Lagstiftning och konungaval:** vem som stiftat, ändrat eller stadfäst lagen, om flocken säger det (predikatet `stiftar_lag`), och reglerna om hur kungen väljs, vem som väljer, eriksgatan och de eder kungen och folket svär varandra.

Ta inte ut annat: arv, jord, kyrka, köp, sår, stöld och så vidare. Undantaget är när en flock uttryckligen handlar om ett av ämnena. Alla flockar behöver inte innehålla något om ämnena. En flock utan sådant innehåll lämnar du utan påståenden.

## Utdatans form

```json
{
 "beskrivning": "En mening om hur extraktionen gjordes.",
 "extraherad_av": "språkmodell (ange modell) – oberoende kontrollextraktion av lagarna, del 8",
 "passager": {},
 "entiteter": [],
 "identifieringar": [],
 "pastaenden": [
  ["<passage-id>", "<subjekt>", "<predikat>", "<objekt>", "<plats>", "<ordagrant citat>", "<anmärkning, valfri>"]
 ]
}
```

- **passage-id** skrivs fullt ut, som nyckeln i `passager`, till exempel `lag:aldre_vastgotalagen:avgl_md_1`.
- **subjekt** är ett id ur `kandidater`.
- **objekt** har en av tre former:
  - ett id: `begrepp:fredloshet`,
  - ett fritt värde på modern svenska: `=nio marker`,
  - båda åtskilda av `|`: `begrepp:mansbot|nio marker till arvingarna`.
- **plats** är flockens `plats` i indata.
- **citat** är ett ordagrant utdrag ur flockens text. Det ska vara kort men täcka det påståendet bygger på. Kopiera tecken för tecken, med interpunktion och felstavningar som de står. Normalisera, översätt eller sätt ihop utdrag aldrig. För Grágás tas citatet ur den danska översättningen.
- **anmärkning** används för villkor ("om dråparen flyr"), för vem som för talan, för tolkningar och för osäkra läsningar.

Två påståenden får inte ha samma passage, predikat, subjekt och objekt. Skiljer sig bara beloppet, till exempel olika bot för fri man och träl, skrivs det i objektets värdedel så att påståendena blir olika.

## Predikat

| predikat | subjekt | objekt | exempel |
|---|---|---|---|
| `paforljd` | brottet | påföljden, med belopp eller villkor | `begrepp:drap` → `begrepp:mansbot\|nio marker` |
| `tillfaller` | boten eller det förverkade godset | mottagaren, med andelen | `begrepp:mansbot` → `begrepp:kung\|en tredjedel` |
| `handlaggs_vid` | brottet eller målet | tinget eller domaren | `begrepp:drap` → `begrepp:haradsting` |
| `kraver` | brottet eller avgörandet | bevismedlet eller förfarandet, med detaljer | `begrepp:drap` → `begrepp:tylftered\|för att fria sig` |
| `diskvalificerar` | jävsgrunden | rollen | `begrepp:frandskap` → `begrepp:namnd\|närmare än tremänning` |
| `utses_av` | uppdraget | den som utser | `begrepp:namnd` → `begrepp:haradshovding` |
| `definieras_som` | begreppet | `=` lagens definition | `begrepp:vadadrap` → `=dödande utan avsikt, t.ex. när ett träd faller` |
| `stiftar_lag` | personen eller ämbetet | `=` vad som gjordes med lagen | `person:...` → `=stadfäste lagen 1296` |

Håll dig till dessa predikat.

## Begrepp och entiteter

- Använd bara id:n ur `kandidater`. Lägg inte till nya entiteter; `entiteter` ska vara tom.
- Välj det mest precisa begreppet. Exempel: `begrepp:dulgadrap` när dråparen är okänd, `begrepp:radsbane` och `begrepp:hallbane` för den som rådde till eller höll vid dråpet, `begrepp:forverkat_gods` när den dömdes gods förverkas och delas, `begrepp:tvebot` och `begrepp:trebot` för dubbel och tredubbel bot, `begrepp:rafst` för kungens räfst och `begrepp:kungsnamnd` för kungens nämnd.
- I `diskvalificerar` är subjektet själva grunden när den finns som begrepp (`begrepp:frandskap`, `begrepp:svagerskap`, `begrepp:muta`, `begrepp:fiendskap`, `begrepp:losker_man`, `begrepp:fredloshet`, `begrepp:tral`). Annars är subjektet `begrepp:jav` och grunden skrivs i värdet.
- Den som stiftat eller stadfäst lagen är subjekt med sitt person-id om personen nämns och finns bland kandidaterna. Annars är subjektet ämbetet (`begrepp:kung`, `begrepp:lagman`, `begrepp:biskop`), och namn och handling skrivs i värdet.
- I stadslagarna och Bjärköarätten motsvaras häradet eller hundaret ofta av staden, rådet eller fogden. Använd då `begrepp:stad`, `begrepp:radman`, `begrepp:borgmastare` eller `begrepp:fogde`.
- Ett dödande som lagen förklarar ogilt (utan bot) skrivs med dråpet som subjekt: `begrepp:drap` `paforljd` `begrepp:ogild`, med villkoret i värdet. Hemsökn, tjuvnad eller annat brott som offret begick står i värdet, inte som subjekt.
- Att en gärning bryter kungens edsöre skrivs `begrepp:edsore` `definieras_som` `=…` med gärningen i värdet, inte som en påföljd.
- När en fredlös eller dömd mans gods delas upp är subjektet `begrepp:forverkat_gods`, inte en bot.
- Skriv bara den påföljd texten anger. Att den skyldige ska tas fram, gripas eller föras till tinget är inte ett dödsstraff.
- Saknas ett begrepp du behöver använder du ett fritt värde (`=…`) och nämner begreppet i sammanfattningen.

## Regler

- **Bara texten:** lägg aldrig till uppgifter som inte står i flocken. Kunskap om lagarna får bara användas för att förstå texten.
- **Ett påstående per regel:** dela upp en mening som ger både påföljd och bötesdelning i flera påståenden, ett per predikat och mottagare.
- **Var försiktig:** noggrannhet och ordagranna citat är viktigare än fullständighet. Är en läsning osäker, skriv det i anmärkningen.

## Arbetsordning

1. Läs flockarna en lag i taget. Granna flockar kan sakna innehåll om ämnena; de är med för att inget ska missas.
2. Ta ut påståendena flock för flock.
3. Kör `kontrollera.py` och rätta alla fel.
4. Lämna filen när kontrollen inte rapporterar några fel. Skriv sist en kort sammanfattning: antal påståenden per ämne, osäkra läsningar och begrepp som saknades.

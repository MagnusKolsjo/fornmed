# Extraktion av normpåståenden ur landskapslagarna (pilot)

Du tar ut påståenden ur en eller flera fornsvenska lagar om tre ämnen och skriver dem till en granskningsbar JSON-fil. Filen läses senare in i en forskningsdatabas och jämförs med en oberoende extraktion, så noggrannhet och ordagranna citat är viktigare än fullständighet.

## Ämnen

1. **Dråp:** dråp med uppsåt och av våda, och dödande som är ogilt (utan bot), t.ex. vid tvekamp, hemsökn eller tjuv på bar gärning. Ta ut:
   - påföljd och belopp,
   - hur boten delas (kungen, häradet eller hundaret, målsäganden, ätten, biskopen),
   - vem som för talan,
   - var målet handläggs,
   - vilka bevis eller vilken ed som krävs,
   - lagens egna definitioner (vad som räknas som dråp, våda, nidingsverk).
2. **Edsöre:** kungens edsvurna frid, alltså edsöresbrotten (hemsökn, våldtäkt, dråp på ting eller i kyrka med flera). Ta ut påföljderna (fredlöshet, böter, förverkat gods), bötesdelningen, vem som dömer och lagens motivering om den finns.
3. **Jäv och oväld:** regler om vem som inte får vara domare, nämndeman, edgärdsman eller vittne, och varför: frändskap, svågerskap, egen sak, mutor, fiendskap. Ta också ut regler om hur nämnden eller edgärden utses, och eder som binder domare eller nämnd att döma rätt.

Ta också ut uppgifter om vem som **stiftat eller stadfäst lagen**, om lagen själv nämner det i prolog eller stadfästelse (predikatet `stiftar_lag`).

Ta inte ut annat: arv, jord, kyrka, köp, sår, stöld och så vidare. Undantaget är när en flock uttryckligen handlar om ett av ämnena.

## Läsa texten

Kör hjälpskriptet från projektmappen:

```
cd <projektmapp>
python hjalpskript/lagtext.py VERK_ID ' Mb ' --sv
```

`--sv` visar en maskinöversättning som läshjälp. Den får **aldrig** citeras och kan vara fel. Läs alltid den fornsvenska texten själv. `--sok dråp edsöre nämnd` begränsar till flockar vars översättning innehåller något av orden.

## Filens form

Skriv till den fil uppdraget anger, i formen:

```json
{
 "beskrivning": "Normpåståenden om dråp, edsöre och jäv ur <lag>, extraherade av språkmodell ur den fornsvenska texten. Ogranskade.",
 "extraherad_av": "språkmodell (Claude Opus 5.5) via data/pastaenden/lagar/<fil>.json",
 "passager": {},
 "entiteter": [],
 "identifieringar": [],
 "pastaenden": [
  ["<passage-id>", "<subjekt>", "<predikat>", "<objekt>", "<plats>", "<ordagrant citat>", "<anmärkning, valfri>"]
 ]
}
```

- **passage-id** skrivs fullt ut, som det står efter `###` i hjälpskriptets utskrift, t.ex. `lag:aldre_vastgotalagen:md_1`.
- **subjekt** är ett begrepps- eller entitets-id ur listan nedan.
- **objekt** har en av tre former:
  - ett id: `begrepp:fredloshet`,
  - ett fritt värde på modern svenska: `=nio marker`,
  - båda åtskilda av `|`: `begrepp:mansbot|nio marker till arvingarna`.
- **plats** är lagens landskap (se uppdraget) och ska vara samma i varje påstående.
- **citat** är ett ordagrant utdrag ur flockens fornsvenska text. Det ska vara kort men täcka det påståendet bygger på. Kopiera tecken för tecken, med interpunktion och felstavningar som de står. Normalisera, översätt eller sätt ihop utdrag aldrig.
- **anmärkning** används för villkor ("om dråparen flyr"), tolkningar och osäkra läsningar.

Två påståenden får inte ha samma passage, predikat, subjekt och objekt. Skiljer sig bara beloppet, till exempel olika bot för fri man och träl, skrivs det i objektets värdedel så att de blir olika.

## Predikat

| predikat | subjekt | objekt | exempel |
|---|---|---|---|
| `paforljd` | brottet | påföljden, med belopp eller villkor | `begrepp:drap` → `begrepp:mansbot\|nio marker` |
| `tillfaller` | boten eller det förverkade godset | mottagaren, med andelen | `begrepp:mansbot` → `begrepp:kung\|en tredjedel` |
| `handlaggs_vid` | brottet eller målet | tinget eller domaren | `begrepp:drap` → `begrepp:haradsting` |
| `kraver` | brottet eller avgörandet | bevismedlet, med detaljer | `begrepp:drap` → `begrepp:tylftered\|för att fria sig` |
| `diskvalificerar` | jävsgrunden | rollen | `begrepp:frandskap` → `begrepp:namnd\|närmare än tremänning` |
| `utses_av` | uppdraget | den som utser | `begrepp:namnd` → `begrepp:haradshovding` |
| `definieras_som` | begreppet | `=` lagens definition | `begrepp:vadadrap` → `=dödande utan avsikt, t.ex. när ett träd faller` |
| `stiftar_lag` | personen | `=` vad den gjorde med lagen | `person:...` → `=stadfäste lagen 1296` |

Vem som för talan (målsäganden, arvingarna, kungens ombud) skrivs i anmärkningen. Håll dig till predikaten ovan.

## Begrepp och entiteter

Använd bara dessa id:n. Lägg inte till nya entiteter.

- **Brott:** `begrepp:drap`, `vadadrap`, `mord`, `hemsokn`, `valdtakt`, `ran`, `stold`, `mordbrand`, `sar`, `arekrankning`, `nidingsverk`, `trolldom`, `hor`, `edsore` (edsöresbrott)
- **Påföljder:** `begrepp:boter`, `mansbot`, `attebot`, `sakore`, `vite`, `fredloshet`, `dodsstraff`, `landsflykt`, `ogild`
- **Mottagare och aktörer:** `begrepp:kung`, `harad`, `hundare`, `landskap` (landet, "alla landsmän"), `malsagande`, `att`, `arv` (arvingarna), `biskop`, `bonde`, `allmoge`, `lagman`, `haradshovding`, `domare`, `lansman`, `fogde`
- **Ting och förfarande:** `begrepp:ting`, `haradsting`, `landsting`, `namnd`, `landssyn`, `rannsakan`, `ed`, `edgard`, `tylftered`, `vittne`, `syn`, `tvekamp`
- **Jäv och oväld:** `begrepp:jav`, `ovald`, `frandskap`, `svagerskap`, `muta`
- **Statsrätt:** `begrepp:konungaval`, `eriksgata`, `manhelgd`

Alla skrivs med prefixet `begrepp:`, t.ex. `begrepp:hundare`. Saknas ett begrepp du behöver, använder du ett fritt värde (`=…`) och nämner begreppet i sammanfattningen till sist.

Den som stiftat eller stadfäst lagen skrivs med ämbetet som subjekt (`begrepp:kung`, `begrepp:lagman`, `begrepp:allmoge`) och namn och handling som värde, t.ex. `=lagman Birger Persson och tolv män satte samman lagen`. Huvudsessionen kopplar namnen till personer.

## Kontroll

Kontrollera filen tills inga fel återstår:

```
python pastaenden_fil.py --kontrollera data/pastaenden/lagar/<fil>.json
```

Läs **inte** in filen i databasen; kör aldrig utan `--kontrollera`. Ändra inga andra filer.

## Sammanfattning

Svara till sist med högst 200 ord:
- antal påståenden per ämne,
- vilka flockar du läste,
- osäkra läsningar och tolkningar,
- begrepp som saknades,
- något anmärkningsvärt för jämförelsen mellan lagarna, t.ex. hur boten delas eller hur jäv motiveras.

## Särskilda regler för vissa verk

- **Grágás** finns i databasen bara i dansk översättning, inte på fornisländska. Läs den med `--oversattning`. Citaten tas ordagrant ur den danska översättningen. Skriv i varje anmärkning att citatet är ur översättningen, och skriv i filens beskrivning att Grágás citeras efter dansk översättning. Platsen är `plats:island`. Definiera den som entitet: `["plats:island", "plats", "Island", null, "Q189"]`. Det är det enda tillåtna undantaget från regeln om nya entiteter.
- **Kristoffers landslag:** läs huvudverket `verk:lag:kristoffers_landslag`. Delverken `verk:lag:kristoffers_landslag_innehallsligt_andrade_flockar_i_forhall` och `verk:lag:kristoffers_landslag_nyskrivna_flockar_i_forhallande_till_me` visar vilka flockar som ändrats eller skrivits nya i förhållande till Magnus Erikssons landslag. Skriv "ändrad i förhållande till MEL" eller "nyskriven i förhållande till MEL" i anmärkningen för påståenden ur sådana flockar. Ta inte ut påståenden ur delverken.
- **Stadslagen och Bjärköarätten** gäller städerna. Ett påstående om häradet eller hundaret motsvaras där ofta av staden, rådet eller fogden. Använd då `begrepp:stad`, `begrepp:radman`, `begrepp:borgmastare` eller `begrepp:fogde`.

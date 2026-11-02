# Hela lagmaterialet: bedömning av skillnaderna

A är vår extraktion (1 878 påståenden i nio delar, utöver stickprovet) och B är Codex oberoende extraktion (1 318 påståenden). Sju delagenter har prövat de 2 034 skillnaderna mot lagtexten, med maskinöversättningen som läshjälp. Varje skillnad finns med beslut och motivering i `bedomning_del_NN.json`, och det som har ändrats står i `genomforda_andringar.md`.

## Utfall

| beslut | antal | betydelse |
|---|---|---|
| samma_regel | 940 | samma regel modellerad eller formulerad olika |
| A_ratt | 694 | vårt påstående stämmer; Codex missade det |
| B_lagg_till | 189 | Codex hittade en regel som vi saknade; **tillagd** |
| A_utanfor | 65 | vårt påstående låg utanför ämnena; **borttaget** |
| A_fel | 61 | vi hade läst eller modellerat fel; **rättat** (58) eller **borttaget** (2); ett förslag avslaget, se nedan |
| B_fel | 40 | Codex hade läst fel |
| osaker | 45 | **ditt beslut**, se nedan |

Jag har själv granskat ett stickprov på 18 av agenternas förslag. Alla höll.

**Vad som ändrades:**
- **Rättelserna** är till största delen konventionsfel. Ogilda dödanden hade fel subjekt (`hemsokn`, `vadadrap` eller `ogild` i stället för `drap`), och `edsore` stod som subjekt där det ska vara förverkat gods eller fridsbön. Några är verkliga felläsningar:
  - "halfwre næmpd" är en halv nämnd som båda parter godtar,
  - ÖgL M 10: kungen *tar* lotten som sin ensak,
  - i SkL 118 är mottagaren ärkebiskopen,
  - i MESt KgB 1 utser fogden inte rådmännen.
- **Luckorna i A** gällde särskilt konungavalet och eriksgatan (ÄVgL, UL, SdmL och ÖgL), Västgötalagens lagmanslängd, dråpbalken i stadslagen (MESt EB 27), ogilda dödanden, edsöresdefinitioner och kvidjäven i Grágás.
- **`begrepp:arv`** betyder egendom, inte arvingarna. Det nya begreppet `begrepp:arvinge` har ersatt arv som mottagare i alla lagfiler.
- **Ett förslag är avslaget:** att byta Magnus Ladulås mot ämbetet kung i Alsnö stadga. Kopplingen till personen står kvar.

Dev har nu 2 236 lagpåståenden över 713 passager. Prod är inte uppdaterad.

## Principfrågor att avgöra

De 45 osäkra fallen samlar sig i sex principfrågor och fem enskilda läsningar. Mitt förslag står för varje fråga.

| | fråga | fall | förslag |
|---|---|---|---|
| P1 | **Rån i edsöresbalkarna.** Ska rån som står i edsöresbalken tas med när lagen inte kallar det edsöre? Agenten för MEL och KrL tog bort 12 sådana påståenden. Agenten för stadslagen markerade 7 som osäkra (MESt EB 23). | 7 + 12 redan borttagna | Ta inte med. Det håller ämnet edsöre rent. |
| P2 | **Att hysa en biltog eller fridlös** (MEL och KrL Dmv 17–18, Eb 25, 28 och 29). | 9 | Ta med. Det visar hur fredlösheten verkade. Subjektet `fredloshet` får stå kvar, och det som hyses står i värdet. |
| P3 | **Edsöre enligt balkens sammanhang.** I DL, VmL, HL och SdmL Kgb 6 nämner våldtäktsflocken inte edsöre, men balken säger "Thæssæ maal æru konungx eþzöræ". I SkL 90 är kungens frid den skånska motsvarigheten. | 4 + 3 | Ta med våldtäkten som `edsore definieras_som`. Ge SkL 90 subjektet `fridsbrott` i stället för edsöre. |
| P4 | **Domarens ansvar,** som domvilla (UL Kkb 19) och domare som vägrar döma (Grágás kap. 41). Agenterna tog redan bort sex liknande påståenden om domarböter som utanför ämnena. | 3 + 6 redan borttagna | Ta med och återställ de sex. Domarens ansvar för en riktig dom hör till frågan om saklighet och oväld. |
| P5 | **Text som Schlyter supplerat ur hskr C** i UL hskr B (Mb 6–15). | 10 | Ta inte med. Det är hskr C:s text, och den finns redan i hskr A. |
| P6 | **Allmänna regler och motiveringar.** GL 13:s "fianda raþi" är lagens motivering, inte en definition. DL Tb 12 är en allmän bevisregel för fyrtiomarkssaker. SdmL Add. 8 gäller våldsgärning mot bonde, som A har kallat hemsökn. | 4 | Behåll GL 13 och skriv i anmärkningen att det är lagens motivering. Ta bort DL Tb 12 och SdmL Add. 8 som dråp och hemsökn. |

## Enskilda läsningar

| fall | fråga | förslag |
|---|---|---|
| Lydek. Rb 15 | Gäller häradsnämnden en utlänning som angriper en inländsk man för en förlikt sak? | Lägg inte till; läsningen är oklar. |
| YVgL Ob 1 §5 | "Miþir maþer man saklösan for pæningæ skylþ": mörda eller lemlästa? | Byt subjekt till `orbotamal` och skriv båda läsningarna i anmärkningen. |
| UL Mb 3 | Gäller vådan också den som kommer emellan? | Behåll A:s läsning, som följer texten ordagrant. |
| ÖgL fragm. C stycke 6 | Edsöret att ta en tjuv från annan bygger på rekonstruktion. | Ta bort påståendet. |
| DL Tb 3 | "þe næmpd ma attir bryta" utan negation | Lägg inte till B:s "får inte". |

## Genomfört 2026-11-01

Användaren godkände förslagen till principfrågorna och de enskilda läsningarna. Ändringarna står i `principbeslut_logg.json`.

- **P1:** rånflockarna i MESt EB 23 är borttagna (7 påståenden).
- **P2:** påståendena om att hysa en biltog eller fridlös står kvar.
- **P3:** våldtäkt som edsöre är tillagt i SdmL Kgb 6, DL Eb 3, VmL Kgb 3 och HL Kgb 3. SkL 90 har fått subjektet `fridsbrott`.
- **P4:** domvilla och domare som vägrar döma står kvar, och de sex domarböterna är återställda.
- **P5:** ingen text ur hskr C är tillagd.
- **P6:** GL 13 står kvar, med en anmärkning om att det är lagens motivering. DL Tb 12 och SdmL Add. 8 är borttagna.
- **Läsningarna:** YVgL Ob 1 har fått subjektet `orbotamal`, med anmärkning om de två läsningarna. ÖgL fragm. C stycke 6 är borttaget. Övriga står som förut.

Dev har 2 235 lagpåståenden över 709 passager.

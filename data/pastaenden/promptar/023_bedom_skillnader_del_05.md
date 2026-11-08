# Bedöm skillnader del 05

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: –
- Utfiler: `oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_05.json`

## Uppdraget till delagenten

````text
Läs och följ <projektmapp>/oberoende_extraktion/jamforelse_lagar_hela/BEDOMNING.md. Din del: del_05 (NN = 05). Bedöm varje skillnad i jamforelse_del_05.json och skriv bedomning_del_05.json. Svara på svenska.
````

## Delagentens slutrapport

Bedömningen av alla 276 skillnader i del_05 finns i `<projektmapp>/oberoende_extraktion/jamforelse_lagar_hela/bedomning_del_05.json`. Ett skript har bekräftat att varje id har ett beslut och att alla ny_rad har ordagranna citat, giltiga id:n och inga dubbletter.

**Beslut:** A_ratt 123, samma_regel 108, B_lagg_till 17, A_utanfor 9, B_fel 8, osaker 7, A_fel 4.

**Viktigaste felen i A:**
- "ingen förverkar annans gods" är felaktigt modellerat som edsore definieras_som (Hl Kgb 6, VmL Kgb 6). Rättat till forverkat_gods.
- "halfwre næmpd" är läst som att parterna nämner var sin hälft. Det betyder en halv nämnd som båda parter godtar.
- A saknar SdmL:s regler om konungaval och eriksgata (5 tillägg) och edsore definieras_som för hemsökn (3 tillägg).
- A_utanfor gäller torvogäld, mened, falskt vittne och böter för nämnd och domare.

**Osäkra fall:**
- Våldtäkt som edsöre när flocken själv inte nämner ezöre (#4, #101, #121).
- "þe næmpd ma attir bryta" utan negation (#29).
- En allmän bevisregel för fyrtiomarkssaker som A knyter till dråp (#264).
- Additamentet om "ualzgerninga til bonda", som A modellerar som hemsökn (#266, #267).

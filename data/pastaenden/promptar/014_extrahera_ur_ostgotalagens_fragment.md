# Extrahera ur Östgötalagens fragment

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Specifikation som delagenten läste: [specifikationer/SPEC_version_2.md](specifikationer/SPEC_version_2.md)
- Utfiler: `data/pastaenden/lagar/ostgotalagen_fragment.json`

## Uppdraget till delagenten

````text
Följ specifikationen i specifikationer/SPEC_version_2.md exakt. Läs den först.

Uppdrag: Östgötalagens sex fragment, alla i samma fil. Läs hela texten i varje fragment (C är störst, ca 72 000 tecken; använd gärna `--sok` för att hitta flockarna om ämnena i C och H).
- `verk:lag:ostgotalagen_fragment_c_ur_holm_b_1709`
- `verk:lag:ostgotalagen_fragment_d_ur_holm_b_24`
- `verk:lag:ostgotalagen_fragment_e_ur_ups_b_22`
- `verk:lag:ostgotalagen_fragment_h_ur_kyrkobalken_ur_skokloster_avdl_i_`
- `verk:lag:ostgotalagen_fragment_m_ur_holm_b_196`
- `verk:lag:ostgotalagen_fragment_n_ur_kopenhamn_am_1056`
Fragmenten är andra handskrifter av samma lag som Östgötalagen A. Ta ut påståendena som de står i fragmentet; där fragmentet tydligt avviker från huvudtexten i sak (annat belopp, annan mottagare) får du gärna skriva det i anmärkningen om du har sett huvudtexten med `lagtext.py verk:lag:ostgotalagen_a_ur_holm_b_50`.
- Plats: `plats:sdhk:ostergotland`.
- Fil: <projektmapp>/data/pastaenden/lagar/ostgotalagen_fragment.json

Kontrollera med `pastaenden_fil.py --kontrollera` tills inga fel återstår. Läs inte in i databasen och ändra inga andra filer. Svara med sammanfattningen enligt specifikationen.
````

## Delagentens slutrapport

Klart. Filen <projektmapp>/data/pastaenden/lagar/ostgotalagen_fragment.json har 58 påståenden. `pastaenden_fil.py --kontrollera` ger inga fel. Ingenting är inläst i databasen och inga andra filer är ändrade.

**Per ämne:** dråp 17 (därav 7 om "hedit mord", H Kkb 46), edsöre/räfst 13, jäv och nämnd/edgärd 28. Inga påståenden om vem som stiftat lagen.

**Lästa flockar:** jag läste hela texten i alla sex fragmenten. Påståendena kommer ur:
- H Kkb 25, 27, 28, 33, 35, 42, 44, 46
- M 7, 8, 10, 11
- C 4, 5, 6, 22, 23
- E innehållsförteckningen (kap. XII)
- N stycke 2

D ger ingenting om ämnena.

**Osäkert:**
- C är mycket fragmentariskt. C 6 ("[ez] øre kununx", att ta en tjuv från någon annan) har jag tolkat med stöd av A, där det i stället gäller en dråpare.
- "valincunna" i C 5 är en osäker läsning.
- I M 10 är det oklart vem som väljer edtagaren.
- "vilda mæn" har jag tolkat som parternas vänner.

**Begrepp som saknades:** biskopsnämnd och fjärdingsnämnd (skrivna som `namnd|…`), jarl (Birger jarls stadga i M 9 är därför inte uttagen), kvinna/omyndig/träl som jävsgrund, egen sak och kolsvarf.

**Inför jämförelsen:**
- H har två regler som jag inte har hittat i A: dråp vid helgerna i Linköping, Skänninge och Söderköping höjer saken med 40 marker (20 till kungen, 20 till biskopen), och dråp i kyrkan gör att den måste vigas om.
- Räfstböterna delas olika: i Götaland en tredjedel till kungen, en till biskopen och 1/9 var till målsäganden, lagmannen och häradshövdingen. I Småland en tredjedel var till målsäganden, kungen och häradet.
- Jäv motiveras med egen sak, vänskap och frändskap, men ingen gradgräns anges.
- I övrigt stämmer belopp och delning med A där jag har jämfört.

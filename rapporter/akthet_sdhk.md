# Äkthetsbedömningar ur SDHK

Granskning av de äkthetsbedömningar som härleds ur Svenskt Diplomatariums
huvudkartotek (SDHK). Listan finns i `data/sdhk/akthet_granskning.tsv` och läses
in med `sdhk_akthet.py`, som också används av `importera_sdhk.py`.

## Utgångsläget

SDHK-importen gav 84 brev bedömningen *misstänkt förfalskning*. Regeln tog varje
mening i regest, kommentar och vittnesuppgifter som innehöll ordet "förfalsk", och
meningarna delades vid punkt. Det gav tre slags fel:

- **Brev som inte är misstänkta.** Anmärkningen handlade om ett annat brev
  (SDHK 10800 nämner det förfalskade SDHK 3902), om förfalskning som ämne
  (SDHK 10206: påven bemyndigar någon att ogiltigförklara förfalskade påvebrev)
  eller hänvisade bara till litteratur om förfalskaren Nils Rabenius.
- **Missade brev.** Regeln läste inte datumfältet, där SDHK ofta skriver sin egen
  bedömning ("förfalskning från omkr. 1158", "misstänkt förfalskning"), och sökte
  inte efter "falskt" eller "interpolation".
- **Avkapade motiveringar.** Förkortningar som "enl." och "s." räknades som
  meningsslut, så att motiveringen slutade mitt i en hänvisning.

## Hur listan är gjord

Alla brev där SDHK:s datumfält, regest, kommentar eller vittnesuppgifter nämner
förfalskning, falskhet, fingering eller interpolation har lästs, 186 brev i allt.
Värdet bestäms så här:

1. SDHK:s egen klassificering i datumfältet gäller först.
2. Annars avgör SDHK:s ordval: ett fast konstaterande ("Falskt", "är en
   förfalskning", "anses vara en förfalskning") ger *förfalskning*; frågor,
   "möjligen", "sannolikt" och en enskild forskares åsikt ger *misstänkt
   förfalskning*.
3. Att Rabenius har ändrat namn eller datum ger *interpolerad*.
4. När SDHK redovisar att forskare är oense registreras båda bedömningarna med
   var sin bedömare (SDHK 413, 2177 och 33188).
5. När orden gäller något annat än brevets äkthet står brevet i listan med värdet
   *ingen* och en motivering, så att det inte läggs till igen.

En förfalskad avskrift av ett i övrigt oifrågasatt brev bedöms som vittne, inte
som verk (SDHK 6165).

Listan är tolkad av en språkmodell ur SDHK:s formuleringar och har inte granskats
av en människa. Bedömningarna har därför `granskad = false`, och motiveringen
säger att de är tolkade.

## Resultat

| | Före | Efter |
|---|---:|---:|
| Förfalskning | – | 25 |
| Misstänkt förfalskning | 84 | 55 |
| Interpolerad | – | 29 |
| Äkta (motbedömning) | – | 3 |
| Bedömningar i allt | 84 | 112 |

- **20 brev har inte längre någon bedömning:** SDHK 277, 549, 5087, 5706, 6165
  (bedömningen gäller nu avskriften), 9759, 10206, 10800, 10835, 10879, 12693,
  24556, 27425, 31525, 33295, 35705, 39328, 43809, 44695 och 45032.
- **44 brev har fått en bedömning de saknade**, bland dem påvebreven till
  Hamburg-Bremen som förfalskades omkring 1158 (SDHK 152–168), de fingerade
  breven SDHK 24440 och 33566 och ett tjugotal brev med Rabenius interpolationer.
- **Tre brev är omstridda:** SDHK 413 (Toll: förfalskning, SDHK: påståendet
  ogrundat), SDHK 2177 (Toll: bland Nydala-förfalskningarna, SDHK: oberättigat)
  och SDHK 33188 (utplockat som förfalskning, Liedgren: äkta).

## Wiktorssons prövning

Per-Axel Wiktorsson, *Falskt eller äkta: i brev från Sveriges medeltid* (Skara: Skara stiftshistoriska
sällskap, 2026; ISBN 978-91-86681-78-4), prövar
183 brev som har misstänkts för förfalskning, varav 162 finns i SDHK. Varje brev har
ett utslag: förfalskning, partiell förfalskning eller äkta. Utslagen ligger i
`data/sdhk/akthet_wiktorsson.tsv` med brevets nummer och sida i boken och läses in som
en egen bedömare bredvid SDHK. 93 av breven saknade tidigare all äkthetsbedömning.
Förteckningen anger brev 160 som SDHK 2686; genomgången visar att det är SDHK 32686.
Sidnumren är tagna ur förhandsversionen på academia.edu och kan skilja sig från den
tryckta bokens; brevens nummer är desamma.

I 31 brev skiljer sig Wiktorssons utslag från SDHK:s. Oftast är det en skillnad i grad
(SDHK: misstänkt, Wiktorsson: förfalskning), men i tolv fall bedömer han brev som SDHK
refererar som falska eller interpolerade som äkta, bland dem SDHK 317, 621, 2529,
19491, 22385, 25905, 34717, 38114 och 38313. Båda ståndpunkterna visas.

## Avgjorda efter genomgång

- **SDHK 9759** (kung Albrekt för Hinze Pape 1370): partiell förfalskning enligt
  Wiktorsson (nr 86, s. 261 f.). Rabenius har på originalet ändrat ”Hincerum Pape” till
  ”Lancerum Rabbe” och ”familijs premissis” till ”familijs rabbenianis”; Peringskiölds
  avskrift har den ursprungliga texten. SDHK uttalar sig inte själv.
- **SDHK 10835 och 10879** (Kristian i Svinn 1376): bara kända genom Rabenius
  avskrifter, i en svit som Liedgren behandlar (Donum Boëthianum, 1950, s. 246 f.). SDHK
  ifrågasätter inte breven och Wiktorsson tar inte upp dem. Bedömningen *misstänkt*,
  låg säkerhet, sitter på avskriften. Liedgrens studie finns inte elektroniskt.
- **SDHK 659**: SDHK:s tre markeringar är odaterade, och SDHK:s bedömning är därför
  *misstänkt* enligt försiktighetsprincipen. Wiktorsson (nr 34, s. 138) bedömer
  originalet som ett skenoriginal och brevet som *förfalskning*; det är den senaste
  bedömningen.
- **SDHK 39886** är den förfalskade versionen av freden i Nöteborg (DS 2419, 2419 bb,
  2419 bc), känd genom Hans Brasks kopiebok: *förfalskning* enligt både SDHK och
  Wiktorsson (nr 58, s. 201). Den äkta versionen är SDHK 3228 (DS 2418), som inte har
  någon bedömning.

Bedömningar av vittnen (SDHK 6165, 10835, 10879) visas på brevsidan och i
träffkortets källkritiska hjälp med vilket vittne de gäller.

## Nya brev

För brev som inte finns i listan använder `sdhk_akthet.py` bara SDHK:s
klassificering i datumfältet och uttrycket "med Rabenius interpol.".
`python sdhk_akthet.py --kandidater` skriver ut brev som nämner förfalskning men
saknas i listan; efter granskningen är den tom.

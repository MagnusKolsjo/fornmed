# Fornmed – grafisk manual

Version 1.0 · 1 november 2026

## Idé och användning

Fornmed är namnet i den här profilen för tjänsten som beskrivs i den bifogade README:n: en sökbar databas över källor till Sveriges och Nordens forntid och medeltid. Användaren ska kunna följa en uppgift tillbaka till en citerbar passage och se när forskare bedömer den olika. Identiteten förenar därför **ristad sten** och **illuminerat manuskript**, medan gränssnittet hålls lugnt och läsbart.

De bifogade runstensbilderna gav den kantiga formen och den röda järnoxidkänslan. Manuskriptbilderna gav blått bläck, varmt pergament, dämpat guld och gröna ornament. Färgerna är digitalt bearbetade profilfärger, inte uppmätta originalpigment.

## Logotyp

Primärfil: [`fornmed-logo.svg`](fornmed-logo.svg). Ordet läses **Fornmed**. `Forn` är specialritat med få raka streck efter de bifogade runraderna: `o` tecknas som en fyrsidig romb, `r` med stam och gren och `n` med tre streck. Bokstäverna står tätare än i första versionen. `med` bygger på den mjukare, blackletterinspirerade Texturina och är omvandlat till vektorkurvor. De båda leden har samma baslinje och samma visuella över- och underkant. Logotypen kräver inget installerat typsnitt och gör ingen nätverksbegäran.

| Variant | Fil | Bakgrund |
|---|---|---|
| Primär | [`fornmed-logo.svg`](fornmed-logo.svg) | Pergament, vit eller annan mycket ljus yta |
| Mörk | [`fornmed-logo-mork.svg`](fornmed-logo-mork.svg) | Mörkt bläckblå eller mörkt fotografi med säker kontrast |
| Enfärg | [`fornmed-logo-enfarg.svg`](fornmed-logo-enfarg.svg) | När färg inte kan användas |

Använd hela ordmärket. Håll fri yta runt det motsvarande minst höjden på ett litet `o` i märket. Rekommenderad minsta visningsbredd är **220 CSS-pixlar**; under detta används namnet som vanlig text i gränssnittstypsnittet. Ändra inte bokstavsavstånd, proportioner eller de två delarnas färger. SVG-filerna har transparent bakgrund och beskrivande `<title>`/`<desc>`.

I HTML: `<img src="/grafisk_profil/fornmed-logo.svg" alt="Fornmed" width="360" height="105">`. När logotypen är den enda texten i en länk ska länkens tillgängliga namn vara “Fornmed”.

## Färger

Samtliga värden är vanliga sRGB-hexvärden och kan användas direkt i CSS. Textkontrast är beräknad mot `Pergament` enligt WCAG:s kontrastformel.

| Namn | Hex | Roll | Kontrast mot pergament |
|---|---|---|---:|
| Pergament | `#F7F2E6` | Sidbakgrund | – |
| Vit yta | `#FFFDFC` | Kort, läsytor | – |
| Bläck | `#1E2C30` | Brödtext | 12,89:1 |
| Dämpat bläck | `#536166` | Metadata, hjälpttext | 5,75:1 |
| Runröd | `#93483E` | `Forn`, avgränsade accenter | 5,81:1 |
| Manuskriptblå | `#244A63` | `med`, rubriker, länkar, primära knappar | 8,41:1 |
| Bladgrön | `#426C62` | Sekundär accent | 5,29:1 |
| Mörk guldockra | `#8B641E` | Små betoningar och dekor | 4,77:1 |
| Sten | `#D9D1C4` | Linjer och avskiljare, inte text | – |

Vit text på manuskriptblå har kontrasten **9,27:1** och på runröd **6,40:1**. Använd inte färg ensam för att förklara källstatus: skriv alltid ut exempelvis *belagd*, *legendarisk*, *omstridd* eller *ogranskad*. Profilfärgerna betecknar epoker och funktioner, inte sanningsgrad.

## Typografi

| Funktion | Typsnitt | Användning |
|---|---|---|
| Gränssnitt | **Source Sans 3** | Sökfält, navigation, filter, metadata, knappar och korta förklaringar |
| Läsning | **EB Garamond** | Källpassager, längre redaktionell text och större rubriker |
| Historiskt uttryck | **Texturina** | Endast kurvorna i logotypens `med`; använd inte som löptext |

Source Sans 3 och EB Garamond är fria under SIL Open Font License 1.1. De fyra medföljande WOFF2-filerna i `fonts/` kan hostas på samma domän som webbplatsen. Licenstexterna ligger i `licenser/`. Texturina behöver inte laddas på webbplatsen eftersom logotypens bokstäver redan är kurvor. Typsnittsfilerna kommer från [Google Fonts öppna källkod för Source Sans 3](https://github.com/google/fonts/tree/main/ofl/sourcesans3), [EB Garamond](https://github.com/google/fonts/tree/main/ofl/ebgaramond) och [Texturina](https://github.com/google/fonts/tree/main/ofl/texturina); licensens användningsvillkor finns hos [SIL Open Font License](https://openfontlicense.org/open-font-license-official-text/).

Rekommenderade startvärden på webben: gränssnittstext **16–18 px**, radavstånd **1,5**; källtext i EB Garamond **20–22 px**, radavstånd **1,5–1,6**, maximal radlängd cirka **68 tecken**. Huvudrubriker i EB Garamond **36–56 px** beroende på skärm. Använd riktiga viktgrader från de variabla filerna, inte syntetisk fetning. Respektera användarens zoom och textstorlek.

## Webbimplementation

[`profil.css`](profil.css) innehåller lokala `@font-face`-regler, CSS-variabler och enkla typografiklasser. Anpassa sökvägen till `fonts/` om filerna flyttas. Använd gärna WOFF2-filerna direkt på den egna domänen; inkludera inte Google Fonts CSS, Adobe Fonts-kit eller externa bildlänkar. Detta upplägg sätter inga kakor och skapar inga typsnittsrelaterade tredjepartsanrop.

```html
<link rel="stylesheet" href="/grafisk_profil/profil.css">
```

```css
body { background: var(--fm-paper); color: var(--fm-ink); font-family: var(--fm-font-ui); }
.source-passage { font-family: var(--fm-font-reading); font-size: 1.3rem; line-height: 1.55; }
a { color: var(--fm-manuscript); text-underline-offset: .17em; }
```

Låt citerbara passageadresser och källhänvisningar vara synliga i gränssnittet. Rubriker och ornament kan bära det historiska uttrycket; sökresultat, årtal, signum och bedömningar behöver enkel läsbarhet. Lägg alltid en tydlig tangentbordsfokusmarkering på länkar och kontroller.

## Levererade filer

`manual.html` är en visuell, responsiv version av denna manual med exempel på logotyp, färger, text och komponenter. Den använder endast lokala filer. `fornmed-forhandsvisning.png` är en enkel rasterförhandsvisning; SVG-filen är originalet. Inga av de bifogade fotografierna är inbakade i logotypen eller manualen.

# Fornmed som länkade data

Fornmeds källor, register, påståenden och bedömningar beskrivs här som RDF:

- **URI:er.** Varje post har en beständig URI och kan hämtas som webbsida eller som RDF.
- **Dumpfiler.** Hela datamängden kan laddas ner som filer.
- **SPARQL.** En SPARQL-ändpunkt besvarar frågor över alltihop.

Dokumentet beskriver hur URI:erna är byggda, vilka modeller som används och hur varje
slags post ser ut. Kodexemplen är skrivna i Turtle och använder riktiga poster ur
Fornmed.

Filer i den här katalogen:

| Fil | Innehåll |
|---|---|
| `fornmed.ttl` | Fornmeds egna klasser och egenskaper, `https://w3id.org/fornmed/def/` |
| `vokabular_mappning.ttl` | Egenskaper i Wikidata, CIDOC CRM och Schema.org som motsvarar Fornmeds predikat |

Vokabuläret (genre, predikat, historicitet och de andra klassificeringsaxlarna) skrivs ut
som SKOS av `vokabular_rdf.py` i projektets rotkatalog.

## Grundtanke

Fornmed skiljer på vad en källa *säger* och vad forskningen *drar för slutsatser*. Det
gäller också i RDF:

- **Ett påstående är aldrig en direkt tripel.** Att ett brev kallar Knut Eskilsson lagman
  i Uppland skrivs som en post med passagen som belägg, inte som
  `person fm:innehar_ambete lagman`. En direkt tripel skulle säga att det *är* så, och den
  tappar källan när den kopieras vidare.
- **Två entiteter slås aldrig ihop med `owl:sameAs`.** Att kung Knut i ett brev är Knut
  Eriksson är en identifiering som kan bedömas och ifrågasättas. En SPARQL-motor med
  inferens skulle annars slå ihop entiteterna och dölja frågan.
- **Allt som inte är källans egen uppgift bär sin proveniens.** Det anges hur uppgiften
  togs fram (manuellt, med regel eller av språkmodell) och om en människa har granskat den.
- **Oeniga bedömningar redovisas var för sig.** Ingenting vägs samman.

## URI:er

### Mönster

| Post | URI | Exempel på id |
|---|---|---|
| Källsamling | `https://w3id.org/fornmed/id/kallsamling/{id}` | `sdhk`, `rundata` |
| Verk | `https://w3id.org/fornmed/id/verk/{id}` | `sdhk:34486`, `dn:6:516`, `verk:runa:vg_52` |
| Vittne | `https://w3id.org/fornmed/id/vittne/{id}` | `sdhk:34486:eftermedeltida_avskrift:1` |
| Utgåva | `https://w3id.org/fornmed/id/utgava/{id}` | `utgava:runa:vg_52` |
| Passage | `https://w3id.org/fornmed/id/passage/{id}` | `sdhk:34486:regest`, `runa:vg_52:translitt` |
| Entitet | `https://w3id.org/fornmed/id/entitet/{id}` | `person:sdhk:knut_eskilson:33355`, `plats:socken:449` |
| Påstående | `https://w3id.org/fornmed/id/pastaende/{id}` | |
| Identifiering | `https://w3id.org/fornmed/id/identifiering/{id}` | |
| Bedömning | `https://w3id.org/fornmed/id/bedomning/{id}` | |
| Term | `https://w3id.org/fornmed/id/term/{id}` | `begrepp:lagman:fsv:laghman` |
| Ordboksartikel | `https://w3id.org/fornmed/id/ordboksartikel/{id}` | |
| Längd | `https://w3id.org/fornmed/id/langd/{id}` | regent-, biskops- och påvelängderna |
| Omnämnande | `https://w3id.org/fornmed/id/omnamnande/{id}` | entiteter som hittats i passagernas text |
| Datering | `https://w3id.org/fornmed/id/datering/{id}` | tider knutna till passager |
| Koppling | `https://w3id.org/fornmed/id/koppling/{id}` | kopplingar till kulturarvsobjekt |
| Vokabulär | `https://w3id.org/fornmed/id/vokabular/{axel}` | `predikat`, `genre` |
| Värde i vokabulär | `https://w3id.org/fornmed/id/vokabular/{axel}/{kod}` | `predikat/innehar_ambete` |
| Graf | `https://w3id.org/fornmed/graf/{namn}` | `kallsamling/sdhk`, `register` |
| Klasser och egenskaper | `https://w3id.org/fornmed/def/{namn}` | `Pastaende`, `granskad` |

### Regler

- **Id:t är detsamma som i databasen, API:et och MCP-servern.** Kolon är tillåtet i en
  URI-sökväg och skrivs som det är.
- **Typen i sökvägen är generaliserad.** Personer, platser, ämbeten och begrepp är alla
  `entitet`, eftersom en entitets typ kan ändras när forskningen ändras. URI:n får aldrig
  ändras.
- **URI:erna skrivs i ASCII.** Tecken som inte får stå i en URI-sökväg, och tecken utanför
  ASCII, procentkodas med UTF-8. Termen `begrepp:harad:fsv:hæraþ` får URI:n
  `https://w3id.org/fornmed/id/term/begrepp:harad:fsv:h%C3%A6ra%C3%BE`. Snedstreck i ett id
  kodas som `%2F`. Regeln finns i `rdf_uri.py`.
- **En URI tas aldrig bort och återanvänds aldrig.** En entitet som slås ihop med en annan
  behåller sin URI, som då pekar vidare med `dcterms:isReplacedBy`.

### Uppslag

`https://w3id.org/fornmed/` vidarebefordrar med 303 till samma sökväg under
`https://fornmed.se/`. Där väljs svaret efter `Accept`-huvudet:

| `Accept` | Svar |
|---|---|
| `text/html` | Postens webbsida |
| `text/turtle` | Turtle |
| `application/ld+json` | JSON-LD |
| `application/n-triples` | N-Triples |
| `application/rdf+xml` | RDF/XML |

Det är w3id-adressen som står i RDF:en och som andra ska länka till. Om Fornmed flyttar
till en annan domän ändras bara vidarebefordringen i w3id.org.

## Modeller

| Prefix | Namnrum | Används för |
|---|---|---|
| `crm:` | `http://www.cidoc-crm.org/cidoc-crm/` | CIDOC CRM: personer, platser, tider, påståenden |
| `lrmoo:` | `http://iflastandards.info/ns/lrm/lrmoo/` | LRMoo: verk och utgåvor |
| `crminf:` | `http://www.cidoc-crm.org/extensions/crminf/` | CRMinf: bedömningar och identifieringar |
| `oa:` | `http://www.w3.org/ns/oa#` | W3C Web Annotation: omnämnanden i text |
| `skos:`, `skosxl:` | `http://www.w3.org/2004/02/skos/core#`, `http://www.w3.org/2008/05/skos-xl#` | Vokabulär, begrepp och termer |
| `geo:` | `http://www.opengis.net/ont/geosparql#` | Geometrier |
| `wgs84:` | `http://www.w3.org/2003/01/geo/wgs84_pos#` | Latitud och longitud |
| `dcterms:`, `rdfs:`, `foaf:` | | Titlar, etiketter, licenser, länkar till webbsidor |
| `fm:` | `https://w3id.org/fornmed/def/` | Fornmeds egna klasser och egenskaper |

CIDOC CRM är stommen: det som Fornmed vet uttrycks där. Varje `fm:`-klass och
`fm:`-egenskap är kopplad till CRM med `rdfs:subClassOf` eller `rdfs:subPropertyOf`, så
att data kan läsas både med Fornmeds termer och med CRM:s. Därtill har varje post enkla
egenskaper som `rdfs:label`, `skos:prefLabel` och `wgs84:lat`, så att det går att fråga
utan att kunna CRM.

Exemplen nedan använder de här prefixen för Fornmeds poster:

```turtle
@prefix fm:            <https://w3id.org/fornmed/def/> .
@prefix kallsamling:   <https://w3id.org/fornmed/id/kallsamling/> .
@prefix verk:          <https://w3id.org/fornmed/id/verk/> .
@prefix vittne:        <https://w3id.org/fornmed/id/vittne/> .
@prefix utgava:        <https://w3id.org/fornmed/id/utgava/> .
@prefix passage:       <https://w3id.org/fornmed/id/passage/> .
@prefix entitet:       <https://w3id.org/fornmed/id/entitet/> .
@prefix pastaende:     <https://w3id.org/fornmed/id/pastaende/> .
@prefix identifiering: <https://w3id.org/fornmed/id/identifiering/> .
@prefix bedomning:     <https://w3id.org/fornmed/id/bedomning/> .
@prefix term:          <https://w3id.org/fornmed/id/term/> .
```

## Källor

En källa beskrivs i fyra nivåer: verket (texten), vittnena (bevarade exemplar),
utgåvorna (utgivna texter och översättningar) och passagerna (citerbara textenheter).

| Fornmed | Klass |
|---|---|
| Verk | `fm:Verk` ⊂ `lrmoo:F2_Expression` |
| Vittne | `fm:Vittne` ⊂ `crm:E22_Human-Made_Object` |
| Utgåva | `fm:Utgava` ⊂ `lrmoo:F3_Manifestation` |
| Passage | `fm:Passage` ⊂ `crm:E33_Linguistic_Object` |

```turtle
verk:sdhk:34486 a fm:Verk ;
    rdfs:label "SDHK nr 34486" ;
    dcterms:title "SDHK nr 34486" ;
    fm:kallsamling kallsamling:sdhk ;
    fm:genre <https://w3id.org/fornmed/id/vokabular/genre/diplom> ;
    fm:upphov "Riddaren Knut Eskilsson till Venngarn, lagman i Uppland" ;
    crm:P72_has_language <http://lexvo.org/id/iso639-3/swe> ;
    dcterms:date "1502-01-06?" ;
    lrmoo:R17i_was_created_by [
        a lrmoo:F28_Expression_Creation ;
        crm:P4_has_time-span [ a crm:E52_Time-Span ;
            fm:edtf "1502-01-06?" ; fm:fran 15020106 ; fm:till 15020106 ;
            crm:P82a_begin_of_the_begin "1502-01-06T00:00:00"^^xsd:dateTime ;
            crm:P82b_end_of_the_end "1502-01-06T23:59:59"^^xsd:dateTime ] ;
        crm:P7_took_place_at entitet:plats:sdhk:stockholm ] ;
    fm:utfardandeort entitet:plats:sdhk:stockholm ;
    fm:plats [ a fm:Platsangivelse ;
        fm:roll <https://w3id.org/fornmed/id/vokabular/platsroll/utfardandeort> ;
        fm:avser entitet:plats:sdhk:stockholm ;
        fm:namnform "Stockholm" ; fm:osaker false ; fm:harledd false ] ;
    foaf:page <https://sok.riksarkivet.se/sdhk?SDHK=34486> .

vittne:sdhk:34486:eftermedeltida_avskrift:1 a fm:Vittne ;
    fm:vittnestyp <https://w3id.org/fornmed/id/vokabular/vittnestyp/eftermedeltida_avskrift> ;
    rdfs:label "Westin 1038, fol. 10v, UUB (dep. Stockholms SA)" ;
    crm:P128_carries verk:sdhk:34486 .

passage:sdhk:34486:regest a fm:Passage ;
    crm:P106i_forms_part_of verk:sdhk:34486 ;
    fm:passagetyp <https://w3id.org/fornmed/id/vokabular/passagetyp/regest> ;
    fm:adress "SDHK 34486" ;
    crm:P72_has_language <http://lexvo.org/id/iso639-3/swe> ;
    crm:P190_has_symbolic_content "Riddaren Knut Eskilsson till Venngarn, lagman i Uppland (1496-1516), utfärdar dombrev …"@sv .
```

Vokabulärvärden innehåller ett snedstreck mellan axel och kod och kan därför inte skrivas
som prefixnamn i Turtle. De står som fulla URI:er.

### Tid

Källornas datum är julianska och ofta ogiltiga som gregorianska datum, till exempel
29 februari 1300. En tid är därför alltid en `crm:E52_Time-Span` med tre uppgifter:

| Egenskap | Innehåll |
|---|---|
| `fm:edtf` | EDTF-uttrycket i källans kalender. Det är den auktoritativa formen. |
| `fm:fran`, `fm:till` | Samma intervall som heltal ÅÅÅÅMMDD, för jämförelser utan kalenderomräkning |
| `crm:P82a_begin_of_the_begin`, `crm:P82b_end_of_the_end` | Intervallet som `xsd:dateTime`, för verktyg som förväntar sig CRM:s egenskaper. Datumen räknas inte om till den gregorianska kalendern. En dag som inte finns i den gregorianska kalendern flyttas utåt, så att intervallet blir bredare och aldrig smalare: 29 februari 1300 blir 28 februari som början och 1 mars som slut. |

### Språk

`crm:P72_has_language` pekar på språkets ISO 639-3-kod hos Lexvo
(`http://lexvo.org/id/iso639-3/swe`). Texternas språktaggar följer BCP 47, alltså den
kortaste koden: `@sv`, `@la`, `@en`, `@is`, `@non` (fornvästnordiska). Fornsvenska saknar
egen kod och skrivs `@sv-x-fsv`, i `crm:P72_has_language` som
`<https://w3id.org/fornmed/id/vokabular/sprak/fsv>`.

### Maskinöversättningar

Passager i utgåvor som en språkmodell har översatt har `fm:maskinoversatt true`.
Översättningarna är ogranskade. Citera originalet.

## Entiteter

| Entitetstyp | Klass |
|---|---|
| Person | `fm:Person` ⊂ `crm:E21_Person` |
| Grupp, släkt, folk | `fm:Grupp` ⊂ `crm:E74_Group` |
| Plats | `fm:Plats` ⊂ `crm:E53_Place` |
| Administrativ indelning | `fm:Indelning` ⊂ `fm:Plats` |
| Institution | `fm:Institution` ⊂ `crm:E74_Group` |
| Ämbete, roll | `fm:Ambete` ⊂ `crm:E55_Type`, `skos:Concept` |
| Händelse | `fm:Handelse` ⊂ `crm:E5_Event` |
| Begrepp | `fm:Begrepp` ⊂ `crm:E55_Type`, `skos:Concept` |
| Gud, väsen | `fm:Vasen` ⊂ `crm:E28_Conceptual_Object` |
| Fast kulturarvsobjekt | `fm:FastKulturarvsobjekt` ⊂ `crm:E18_Physical_Thing` |
| Löst kulturarvsobjekt | `fm:LostKulturarvsobjekt` ⊂ `crm:E22_Human-Made_Object` |

En entitet har namnet som `rdfs:label` och `skos:prefLabel`. Källornas namnformer står
som `crm:P1_is_identified_by` med passagen där formen förekommer:

```turtle
entitet:person:sdhk:knut_eskilson:33355 a fm:Person ;
    rdfs:label "Knut Eskilsson" ;
    skos:prefLabel "Knut Eskilsson"@sv .
```

### Platser

En plats har sitt läge och sin nutida tillhörighet som enkla egenskaper. Uppgifterna är en
bedömning och inte källans egen uppgift. Därför anges varifrån de kommer, hur kopplingen
gjordes och om den är granskad.

```turtle
entitet:plats:socken:449 a fm:Indelning ;
    rdfs:label "Krokeks socken" ;
    skos:prefLabel "Krokeks socken"@sv ;
    fm:platsslag <https://w3id.org/fornmed/id/vokabular/platsslag/socken> ;
    fm:nutidaNamn "Krokek" ;
    fm:landskap entitet:plats:sdhk:ostergotland ;
    fm:lan entitet:plats:lan:05 ;
    fm:kommun entitet:plats:kommun:0581 ;
    wgs84:lat 58.66306 ; wgs84:long 16.39083 ;
    geo:hasGeometry [ geo:asWKT "POINT(16.39083 58.66306)"^^geo:wktLiteral ] ;
    fm:lageKalla "Riksantikvarieämbetet, K-samsök; Wikidata" ;
    fm:lageMetod "auktoritet" ;
    fm:lageGranskat false ;
    skos:exactMatch <http://www.wikidata.org/entity/Q10549369> ,
        <http://kulturarvsdata.se/resurser/aukt/geo/parish#449> .
```

Socknarna har samma nummer som Riksantikvarieämbetets sockenauktoritet, så länken dit
följer direkt av sockenkoden. Kommuner och län länkas på samma sätt till RAÄ:s
auktoriteter för kommun och län.

### Länkar till andra datamängder

| Egenskap | Används när |
|---|---|
| `skos:exactMatch` | Det är samma sak, och kopplingen kommer från en auktoritet, ett register eller en granskad avstämning |
| `skos:closeMatch` | Det är sannolikt samma sak, men kopplingen är inte granskad |
| `owl:sameAs` | Används inte mellan Fornmeds egna entiteter. Mot andra datamängder bara för granskade kopplingar som gäller en verklig identitet. |
| `foaf:page` | Postens sida hos källan: SDHK, Diplomatarium Norvegicum, Rundata |

Fornmed länkar direkt till den som äger uppgiften: Riksantikvarieämbetet för socknar och
lämningar, Riksarkivet för TORA, Kartverket för norska ortnamn. Wikidata är navet för
resten. Länkar som Wikidata redan har till VIAF, GND och GeoNames upprepas inte.

### Begrepp

Begreppsregistret är ett `skos:ConceptScheme`. Termerna, med historiska former och
motsvarigheter på andra språk, är `skosxl:Label`. Relationerna mellan begreppen är
`skos:broader` och `skos:related`.

```turtle
entitet:begrepp:lagman a fm:Begrepp ;
    skos:inScheme <https://w3id.org/fornmed/id/begreppsregister> ;
    skos:prefLabel "lagman"@sv ;
    skosxl:prefLabel term:begrepp:lagman:swe:lagman ;
    skosxl:altLabel term:begrepp:lagman:lat:legifer , term:begrepp:lagman:fsv:laghman ;
    skos:related entitet:begrepp:lagsaga .

term:begrepp:lagman:fsv:laghman a skosxl:Label ;
    skosxl:literalForm "laghman"@sv-x-fsv ;
    fm:termtyp <https://w3id.org/fornmed/id/vokabular/termtyp/historisk_form> .
```

## Påståenden

Ett påstående är vad en passage hävdar. Det blir en `fm:Pastaende`, som är en
`crm:E13_Attribute_Assignment`:

| CRM-egenskap | Innehåll |
|---|---|
| `crm:P140_assigned_attribute_to` | Subjektet |
| `crm:P177_assigned_property_of_type` | Predikatet, ett värde i vokabuläret `predikat` |
| `crm:P141_assigned` | Objektet, när det är en entitet |
| `fm:objektvarde` | Objektet, när det är ett värde |
| `crm:P7_took_place_at` | Platsen |
| `crm:P4_has_time-span` | Tiden |
| `crm:P70i_is_documented_in` | Passagen som påståendet bygger på |

```turtle
pastaende:sdhk:34486:utfardare:sdhk_knut_eskilson_33355:innehar_ambete:lagman:upland
    a fm:Pastaende ;
    crm:P140_assigned_attribute_to entitet:person:sdhk:knut_eskilson:33355 ;
    crm:P177_assigned_property_of_type <https://w3id.org/fornmed/id/vokabular/predikat/innehar_ambete> ;
    crm:P141_assigned entitet:begrepp:lagman ;
    crm:P7_took_place_at entitet:plats:sdhk:upland ;
    crm:P4_has_time-span [ a crm:E52_Time-Span ;
        fm:edtf "1502-01-06?" ; fm:fran 15020106 ; fm:till 15020106 ] ;
    crm:P70i_is_documented_in passage:sdhk:34486:regest ;
    fm:extraktion <https://w3id.org/fornmed/id/vokabular/extraktion/regel> ;
    fm:extraheradAv "pastaenden_sdhk.py" ;
    fm:granskad false .
```

Relationer mellan påståenden skrivs direkt mellan dem: `fm:stoder`, `fm:motsager`,
`fm:sammaSom` och `fm:beroendeAv`. Den sista betyder att påståendet återger samma
tradition som det andra och alltså inte ger oberoende stöd.

### Att få direkta tripler

Den som vill ha direkta tripler, till exempel för att jämföra med Wikidata, kan bilda dem
med en SPARQL-fråga. `vokabular_mappning.ttl` anger med `fm:motsvarandeEgenskap` vilka
predikat som har en motsvarighet i samma riktning:

```sparql
PREFIX fm:  <https://w3id.org/fornmed/def/>
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>

CONSTRUCT { ?subjekt ?egenskap ?objekt }
WHERE {
  ?p a fm:Pastaende ;
     crm:P140_assigned_attribute_to ?subjekt ;
     crm:P177_assigned_property_of_type ?predikat ;
     crm:P141_assigned ?objekt .
  ?predikat fm:motsvarandeEgenskap ?egenskap .
  FILTER(STRSTARTS(STR(?egenskap), "http://www.wikidata.org/prop/direct/"))
}
```

Resultatet saknar källa och bedömningar. Det ska inte publiceras som om det vore fakta.

## Identifieringar

En identifiering är förslaget att två entiteter avser samma sak. Identifieringar med samma
`fm:alternativgrupp` utesluter varandra: kung Knut i SDHK 214 är antingen Knut Eriksson
eller Knut Långe.

```turtle
identifiering:sdhk:sdhk_kung_knut_214:knut_eriksson a fm:Identifiering ;
    fm:entitet entitet:person:sdhk:kung_knut:214 ;
    fm:identifieradMed entitet:person:knut_eriksson ;
    fm:alternativgrupp "sdhk:214:person:sdhk:kung_knut:214" .

identifiering:sdhk:sdhk_kung_knut_214:knut_6 a fm:Identifiering ;
    fm:entitet entitet:person:sdhk:kung_knut:214 ;
    fm:identifieradMed entitet:person:knut_6 ;
    fm:alternativgrupp "sdhk:214:person:sdhk:kung_knut:214" .
```

## Bedömningar

En bedömning är en forskares eller ett registers omdöme om ett påstående, ett verk, ett
vittne eller en identifiering. Den blir en `fm:Bedomning`, som är en CRMinf
`crminf:I2_Belief`. `crminf:J4_that` pekar på det som bedöms och `crminf:J5_holds_to_be`
på omdömet.

```turtle
bedomning:sdhk:2177:akthet:h_toll a fm:Bedomning ;
    crminf:J4_that verk:sdhk:2177 ;
    fm:aspekt <https://w3id.org/fornmed/id/vokabular/bedomningsaspekt/akthet> ;
    crminf:J5_holds_to_be <https://w3id.org/fornmed/id/vokabular/akthet/misstankt> ;
    fm:sakerhet <https://w3id.org/fornmed/id/vokabular/sakerhet/lag> ;
    fm:bedomare "H. Toll" ;
    fm:publikation "Historisk tidskrift för Finland 1926, s. 81 not 1" ;
    fm:granskad false .

bedomning:sdhk:sdhk_kung_knut_214:knut_eriksson:bedomning a fm:Bedomning ;
    crminf:J4_that identifiering:sdhk:sdhk_kung_knut_214:knut_eriksson ;
    fm:aspekt <https://w3id.org/fornmed/id/vokabular/bedomningsaspekt/identifiering> ;
    crminf:J5_holds_to_be <https://w3id.org/fornmed/id/vokabular/identifiering/mojlig> ;
    fm:bedomare "pastaenden_sdhk.py" ;
    fm:granskad false .
```

När publikationen har en DOI eller en Libris-post pekar `crm:P70i_is_documented_in` på
den. En bedömning av datering har ett EDTF-uttryck i stället för ett vokabulärvärde, som
en `crm:E52_Time-Span`.

## Längder

Regent-, biskops- och påvelängderna har var sin URI under `langd/` och egen licens. Varje
titel en person har i en längd blir ett påstående med predikatet
`innehar_ambete` och längden som belägg.

## Omnämnanden i passagerna

Entiteter som nämns i passagernas text, oavsett om de har hittats med NER eller
registrerats manuellt, beskrivs som omnämnanden. Tre saker hålls isär:

1. **Omnämnandet:** textspannet i passagen.
2. **Identifieringen:** vilken entitet spannet avser. Det kan saknas, och det kan finnas
   flera kandidater med samma `fm:alternativgrupp`.
3. **Påståendet:** vad passagen hävdar om entiteten. Ett omnämnande är inget påstående.

Ett omnämnande är en W3C Web Annotation, så att det kan läsas av verktyg för
textannotering. Exemplets id är påhittat:

```turtle
<https://w3id.org/fornmed/id/omnamnande/exempel> a fm:Omnamnande ;
    oa:motivatedBy oa:identifying ;
    oa:hasTarget [
        oa:hasSource passage:sdhk:34486:regest ;
        oa:hasSelector [ a oa:TextPositionSelector ; oa:start 9 ; oa:end 23 ] ,
                       [ a oa:TextQuoteSelector ; oa:exact "Knut Eskilsson" ]
    ] ;
    oa:hasBody entitet:person:sdhk:knut_eskilson:33355 ;
    fm:sannolikhet 0.97 ;
    fm:extraktion <https://w3id.org/fornmed/id/vokabular/extraktion/modell> ;
    fm:extraheradAv "<NER_MODELL>" ;
    fm:granskad false .
```

Positionerna räknas i tecken i passagens text. `oa:TextQuoteSelector` gör att det går att
upptäcka om texten ändrats så att positionerna inte längre stämmer.

Omnämnanden med en identifierad entitet som är granskade eller har hög sannolikhet ger
dessutom den enkla tripeln `passage crm:P67_refers_to entitet`. Den ligger i en egen graf,
`https://w3id.org/fornmed/graf/omnamnanden`, så att den kan väljas bort.

## Datering av passager

En passage kan ha två slags tid:

- **Tillkomst** (`fm:tillkomst`): när texten skrevs. För de flesta passager är det
  verkets datering, men delar av sammansatta verk kan ha egen.
- **Omtalad tid** (`fm:omtaladTid`): den tid texten handlar om. Ett kapitel i
  Heimskringla skrevs omkring 1230 men kan handla om 995–1000.

En datering är en `fm:Datering`, som anger vad den grundas på: ett årtal i texten,
påståenden i passagen, en regent med känd regeringstid eller en språkmodells bedömning.
Grunderna blir ett eget vokabulär, `dateringsgrund`. Exemplets id:n är påhittade:

```turtle
<https://w3id.org/fornmed/id/datering/exempel> a fm:Datering ;
    crm:P140_assigned_attribute_to <https://w3id.org/fornmed/id/passage/exempel> ;
    crm:P177_assigned_property_of_type fm:omtaladTid ;
    crm:P141_assigned [ a crm:E52_Time-Span ;
        fm:edtf "0995/1000" ; fm:fran 9950101 ; fm:till 10001231 ] ;
    fm:grund <https://w3id.org/fornmed/id/vokabular/dateringsgrund/pastaenden> ;
    fm:sakerhet <https://w3id.org/fornmed/id/vokabular/sakerhet/medel> ;
    fm:extraktion <https://w3id.org/fornmed/id/vokabular/extraktion/regel> ;
    fm:granskad false .
```

En tid som anges som en period, till exempel vikingatid eller unionstid, länkas till
periodens URI i PeriodO med `crm:P10_falls_within` på tidsintervallet.

## Kulturarvsobjekt

Lämningar, spår i kulturlandskapet, byggnader och föremål beskrivs som två entitetstyper:

- **Fasta kulturarvsobjekt** (`fm:FastKulturarvsobjekt`) är bundna till en plats:
  gravfält, runstenar, borgar, kyrkor, slott, galgbackar, offerlundar och tingsplatser.
- **Lösa kulturarvsobjekt** (`fm:LostKulturarvsobjekt`) är föremål: museiföremål, fynd och
  sigillstampar.

Fyra uppgifter hålls isär:

| Uppgift | Egenskap | Exempel |
|---|---|---|
| Typ | `fm:kulturarvstyp` | galgbacke, offerlund, borg, kyrka |
| Status i register | `fm:registerstatus` | fornlämning, övrig kulturhistorisk lämning, byggnadsminne |
| Skick | `fm:skick` | bevarad, i bruk, ruin, försvunnen, känd bara ur källor |
| Plats | `crm:P53_has_former_or_current_location` | |

"Fornlämning" är en rättslig status som kan ändras. Den är därför en uppgift om objektet,
med register och datum, och inte en klass.

Byggnad, plats och institution är olika entiteter. "Kalmar slott" i ett medeltidsbrev
kan avse anläggningen, platsen eller slottslänet. Anläggningen är ett fast
kulturarvsobjekt, platsen en `fm:Plats` och länet en `fm:Institution` med
`fm:harSateI` till anläggningen.

### Kopplingar

När ett verk och ett objekt i ett register är samma föremål, som en runinskrift och
runstenen i Kulturmiljöregistret, uttrycks det med `skos:exactMatch`:

```turtle
verk:runa:vg_52 skos:exactMatch
    <http://www.wikidata.org/entity/Q29577829> ,
    <http://kulturarvsdata.se/raa/lamning/b80bc1d6-bba5-4b4e-95d3-5596e3ec7922> .
```

Övriga kopplingar är `fm:Koppling` med slag, säkerhet och proveniens: att en passage
omnämner en lämning, att ett sigill hör till ett brev, eller att ett föremål är av samma
slag som ett som källan beskriver. Att brev och lämningar finns i samma socken behöver
ingen koppling. Det följer av att båda pekar på samma sockenauktoritet.

## Grafer och licenser

Varje källsamling har en egen namngiven graf, med licensen angiven på grafen:

| Graf | Innehåll | Licens |
|---|---|---|
| `graf/kallsamling/{id}` | Källsamlingens verk, vittnen, utgåvor, passager och påståenden | Källsamlingens licens |
| `graf/register` | Entiteter, namnformer, platsuppgifter, termer | CC0 |
| `graf/bedomningar` | Bedömningar och identifieringar | CC0 |
| `graf/vokabular` | Vokabulär och `fm:`-definitionerna | CC0 |
| `graf/lankar` | Länkar till andra datamängder | CC0 |
| `graf/omnamnanden` | Omnämnanden i passagerna | CC0 |

Påståendena ligger i källsamlingens graf eftersom de citerar källans text. Källsamlingarna
har allt från CC0 och public domain till CC BY 4.0, CC BY-SA 4.0, CC BY-NC-SA 4.0 och
ODbL, så den som återanvänder data bör välja grafer efter licens. Fornmeds egna
uppgifter är CC0. Ange gärna Fornmed som källa.

I SPARQL-ändpunkten är standardgrafen unionen av alla grafer. En fråga utan `GRAPH` ser
alltså allt, och med `GRAPH` eller `FROM` går det att avgränsa till vissa licenser.

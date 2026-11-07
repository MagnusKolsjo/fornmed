# Bedömning av brevspråk

Du bedömer vilket språk ett medeltida brev ur Diplomatarium Islandicum (800–1500-tal; texten är OCR med läsfel, þ kan stå som p och ð som ö eller d) är skrivet på.
Varje rad i indatafilen är JSON med `id`, `datum`, `ort` och `utdrag`: två eller tre stycken ur samma brev
med läge ("början", "mitten", "slutet") och styckenummer.

Bedöm brevets huvudspråk utifrån styckena. Ort och datum är sammanhang, inte bevis: ett brev från Oslo kan
vara danskt och ett från Stockholm danskt eller latinskt. Ett enstaka latinskt stycke i ett folkspråkligt brev
är troligen ett citat eller en formel och avgör inte brevet.

## Kännetecken

- **Fornisländska:** som fornnorskan men med kvarstående h- framför l, r och n ("hlutr", "hringr", "hnefi"), "ek"/"eg",
  "þetta", "vær"; brev från Island (alþingi, Skálholt, Hólar) är i regel isländska.
- **Fornnorska:** þ och ð; "ek", "sem", "ollum monnum", "þetta bref", ändelser på -um/-om och -a.
- **Fornsvenska:** "iak", "thetta", "dandemen"/"dannemen" ("Alle dandemen som thetta breff see"), "ok"/"oc",
  "haffwer", "bekennis", "jempska" (Jämtland); mer -a och -o i ändelserna än danskan.
- **Forndanska:** "jeg"/"jegh", "thette", "wij"/"wii", "oc", "gøre"/"giøre", "haffue", "kennes", "vdi";
  försvagade ändelser på -e. Kanslistilen efter 1450 är ofta dansk även i Norge och Sverige.
- **Jämtland och Härjedalen** hörde till Norge men till Uppsala stift; skriftspråket är ofta svenskt med norska
  drag. Det är inte danska.

## Svar

Välj exakt ett av: `lat` (latin), `swe` (fornsvenska), `dan` (forndanska), `nor` (fornnorska), `isl` (fornisländska), `eng` (engelska), `deu` (tyska,
även lågtyska), `nld` (mellannederländska), `dan-nor` (verkligt blandat danskt-norskt), `swe-nor` (verkligt
blandat svenskt-norskt), `dan-swe` (verkligt blandat danskt-svenskt), `annat`.

Använd blandkategorierna bara när texten själv blandar dragen, inte när du är osäker; ange då låg säkerhet.
Säkerhet: `hog`, `medel` eller `lag`. Motivering: högst 15 ord, med konkreta språkdrag ur texten.

Skriv JSON Lines, en rad per brev i samma ordning, med fälten `id`, `sprak`, `sakerhet`, `motivering`.

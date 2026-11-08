# Samordna namn i Gregorius

- Modell: Claude Opus 5.5 (`claude-opus-5-5`)
- Utfiler: –

## Uppdraget till delagenten

````text
Du ska samordna egennamnen i de svenska maskinöversättningarna av Gregorius av Tours, Historia Francorum, så att samma regel gäller i alla 15 filer. Flera agenter har översatt och sedan rättat namnen, men de har dragit gränserna olika.

Regeln (se också punkten om egennamn i <projektmapp>/data/oversattningar/RIKTLINJER.md):
1. Städer (civitates, i praktiken biskopsstäder och de romerska städer som texten kallar civitas/urbs), länder och större floder står i nutida namn, vid behov med textens latinska namn inom parentes första gången i en passage: "Köln (Colonia Agrippina)", "Zaragoza (Caesaraugusta)", "Trier", "Dax", "Bazas", "Comminges", "Javols", "Clermont", "Saintes". Samma stad ska heta likadant i alla filer.
2. Byar (vicus), gods (villa), borgar (castrum), kloster, skogar, berg, områden (pagus), mindre floder och folk står i textens form, gärna med typen och det latinska ordet: "byn Brivatensis (vicus)", "godset Brannacum (villa)", "borgen Divionensis (castrum)" (Dijon är hos Gregorius ett castrum), "arvernerna". Ingen modern identifiering av sådana orter, inte heller med [osäker tolkning].
3. Vedertagna svenska folk- och landnamn får stå: franker, goter, bretoner, burgunder, langobarder, Spanien, Italien, Gallien, Thüringen.
4. Inga egna förklaringar eller identifieringar inom parentes, utom textens latinska namn eller term enligt punkt 1–2.

Filer (relativt <projektmapp>): data/oversattningar/openmgh/historia_francorum__*.json (15 filer). Latinet hämtar du med
  python hjalpskript/kalltext.py verk:historia_francorum --fran 0 --till 445 --typer originaltext
från projektkatalogen (bara läsning).

Arbetssätt: hitta kandidater maskinellt (versalord i översättningarna, ord efter typord som by/gods/borg/stad/kloster/skog/flod/berg/trakt, och samma latinska namn som återgetts olika i olika filer), granska varje kandidat mot latinet och gör exakta strängbyten. Kontrollera före varje byte att strängen finns exakt en gång i passagen, och efteråt att varje fil har samma id-mängd. Ändra inget annat än namn och otillåtna parenteser. Arbeta i en egen katalog: <arbetsmapp>/namn_samordning/ (skapa den; importera inget från scratchpadens rot). Spara säkerhetskopior av filerna där innan du ändrar.

Rapportera: antal ändringar per fil, en lista över hur varje stad som förekom i flera former nu skrivs, och eventuella fall du inte kunde avgöra.
````

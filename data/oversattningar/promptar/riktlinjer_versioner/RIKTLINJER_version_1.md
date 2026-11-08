# Riktlinjer för maskinöversättningarna

Översättningarna i den här katalogen är gjorda av en språkmodell (Claude)
direkt från originalspråket. De är ogranskade och laddas i egna utgåvor
märkta som maskinöversättning; de får inte citeras som översättning.
Syftet är att göra texterna sökbara på modern svenska.

Modellen har fått följande instruktioner:

- Översätt till modern, saklig svenska, troget och fullständigt: varje
  mening och sats, utan sammanfattning, utelämningar eller tillägg.
- Behåll styckeindelning, numrering och rubriker (översatta).
- Centrala fackord (rättstermer, ämbeten, mynt- och måttenheter, juridiska
  förfaranden) översätts till sin moderna betydelse; vid första förekomsten
  i en passage står originalordet inom parentes efter, t.ex. "ledungen
  (leþunger)". Mynt- och måttenheter som mark, öre och örtug behålls.
- Egennamn återges i den form originalet har, eller i vedertagen svensk form
  när en sådan finns (Uppsala, Olof).
- Där tolkningen är osäker står den troligaste tolkningen följd av
  "[osäker tolkning]". Där texten är skadad eller obegriplig står
  "[oläslig]" eller "[oklart]".
- Inga kommentarer, förklaringar eller noter.

Filerna är JSON-objekt där nyckeln är originalpassagens id och värdet
översättningen.

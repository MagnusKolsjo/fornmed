# Oberoende extraktion ur de medeltida lagarna, alla delar

Den här mappen innehåller 9 delar, `del_01` till `del_09`. Varje del är en fristående uppgift med samma regler. Din uppgift är att arbeta dig igenom alla delarna i nummerordning utan att fråga användaren mellan delarna.

## Arbetsgång

För varje mapp `del_NN`, i nummerordning:

1. Hoppa över delen om `del_NN/utdata_del_NN.json` redan finns och `kontrollera.py` godkänner den. En tidigare körning kan ha avbrutits.
2. Läs `del_NN/PROMPT.md` och gör uppgiften som den beskriver. Indata är `del_NN/indata_del_NN.json` och resultatet skrivs till `del_NN/utdata_del_NN.json`.
3. Kör kontrollen från delens mapp och rätta tills den inte rapporterar några fel:
   ```
   cd del_NN && python kontrollera.py indata_del_NN.json utdata_del_NN.json
   ```
4. Skriv delens sammanfattning (antal påståenden per ämne, osäkra läsningar och saknade begrepp) till `del_NN/sammanfattning.md`.
5. Lägg till en rad i `STATUS.md` här: delens nummer, antal påståenden och om kontrollen gick igenom.

Fortsätt sedan med nästa del. När alla delar är klara skriver du en kort slutrad i `STATUS.md`.

## Regler

- **Varje del för sig.** Använd bara delens egen indata och `PROMPT.md`. Det du kom fram till i en tidigare del får inte styra tolkningen av texten i en senare. Reglerna i `PROMPT.md` gäller lika i alla delar.
- **Läs inga andra filer** än de som nämns här och i delarnas `PROMPT.md`. Gå inte upp i mappar ovanför den här, och sök inte efter andra extraktioner.
- **Ändra inte** indatafilerna, `PROMPT.md` eller `kontrollera.py`.
- **Stora delar:** arbeta lag för lag och flock för flock, och spara utdatafilen efter hand så att inget går förlorat om körningen avbryts.
- **Skriv inte ett skript** som tar ut påståenden automatiskt, till exempel med sökord eller reguljära uttryck. Varje påstående ska bygga på din egen läsning av flocken. Hjälpskript för att läsa indata, skriva JSON och kontrollera citat går bra.

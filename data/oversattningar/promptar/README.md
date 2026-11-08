# Uppdragen bakom maskinöversättningarna

Maskinöversättningarna i `data/oversattningar/` gjordes av delagenter. Alla delagenter körde på samma modell, Claude Opus 5.5 (`claude-opus-5-5`), enligt loggarna. Varje uppdragsfil anger modellen, och i databasen står den som översättare för maskinöversättningarnas utgåvor. Varje delagent fick ett eget uppdrag för en del av en text. Uppdragen är här återskapade ordagrant ur sessionsloggarna, så att det går att se exakt vilka instruktioner varje översättning bygger på. Uppdragen kan också användas igen för att göra om eller utöka en översättning.

## Innehåll

- **`NNN_….md`** innehåller ett uppdrag per delagent, i tidsordning: 209 stycken. Där finns de egentliga översättningsjobben för lagarna, MGH-krönikorna, Adams skolier, sagorna, kungakrönikorna, rimkrönikorna och Ottar och Wulfstan. Där finns också de senare uppdragen som granskade eller reviderade översättningar och samordnade egennamnen, till exempel i Gregorius och Adam av Bremen. Varje fil anger modell, utfiler och delagentens uppdrag.
- **Uppdrag som bara sa åt delagenten att köra ett skript** är sagorna, kungakrönikorna och de latinska texterna. För dem finns också skriptets utskrift ordagrant, alltså den instruktion delagenten faktiskt arbetade efter.
- **`INDEX.md`** visar för varje översättningsfil vilket eller vilka uppdrag som skapade eller ändrade den. Alla 262 översättningsfiler har minst ett uppdrag.
- **`hjalpskript/`** innehåller de hjälpskript uppdragen hänvisar till, återskapade i sin sista version:
  - `sagaprompt.py` och `latinprompt.py` byggde uppdragen,
  - `kalltext.py` och `kalltext_ids.py` hämtade originaltexten ur databasen,
  - `kontrollera_oversattning.py` och `kontroll_ids.py` kontrollerade att varje passage fått en översättning,
  - `granskpar.py` användes vid granskningen.

  Skripten låg i en tillfällig arbetsmapp. Uppdragen hänvisar nu till dem som `hjalpskript/…`. Listorna med jobb som `sagaprompt.py` och `latinprompt.py` läste (`sagauppdrag.json` med flera) finns inte kvar, men varje jobbs färdiga instruktion står i uppdragsfilen.
- **`riktlinjer_versioner/`** innehåller riktlinjernas versioner. `RIKTLINJER_version_1.md` gällde när de första lagjobben gjordes. `RIKTLINJER_version_2.md` är den nuvarande, med reglerna om ortnamn och om att inga egna tillägg får göras. Ändringarna däremellan gjordes på ett sätt som inte går att följa i loggarna. En ny version läggs till varje gång riktlinjerna ändras.

## Att tänka på

- Riktlinjerna ändrades medan arbetet pågick. Ett uppdrag hänvisar till `RIKTLINJER.md` som den såg ut när delagenten läste den, inte nödvändigtvis som den ser ut nu. De regler som ändrades, framför allt namnformerna, står oftast också ordagrant i uppdraget.
- Lokala sökvägar är ersatta med platshållare. Uppdragen är i övrigt ordagranna.
  - `<projektmapp>` är projektets rotmapp.
  - `<arbetsmapp>` är den tillfälliga arbetsmapp där delagenterna lade sina hjälpfiler.
  - `<produktionsmapp>` är mappen med den driftsatta servern.
  - `python` står för projektets Python-miljö.

## Nya översättningar

Nya översättningar redovisas här på samma sätt. Reglerna står under "Nya översättningar" i `../RIKTLINJER.md`.

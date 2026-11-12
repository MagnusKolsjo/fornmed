"""Skriver ut uppdraget för jobb N (från 147) ur uppdrag_kronikor_1500.json: python uppdragsprompt4.py N [fil]"""
import json, sys
S = "<arbetsmapp>"
uppdrag = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "uppdrag_kronikor_1500.json"))
GEMENSAMT = """- Texten är svensk prosa från 1500-talet (Olaus Petris krönika, 1530-talet, och Peder Swarts krönika om Gustav Vasa, omkring 1560) efter Fornsvenska textbankens utgåva. Översätt till modern svensk prosa: troget och fullständigt, varje sats, men med nutida stavning, ordföljd, böjning och interpunktion. Ändra inte innehållet, förkorta inte de långa meningarna till sammanfattningar och modernisera inte resonemangen.
- Ord som har bytt betydelse sedan 1500-talet översätts efter sin dåtida betydelse (t.ex. "fast" = mycket, "redo" = redogörelse, "lagha" = ordna); ålderdomliga ord som inte längre förstås får modern motsvarighet med originalordet inom parentes vid första förekomsten i passagen.
- Textbankens tecken: {…} är felaktig läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Utgivarens upplysningar (luckor, sidhänvisningar) återges inom hakparentes på svenska.
- Latinska och tyska inslag översätts till svenska.
- Personer: kungar och furstar i vedertagen svensk form (Gustav Eriksson/konung Gustav, Kristian, Sten Sture, Erik av Pommern, Magnus Ladulås, Birger jarl); övriga i textens form med modern stavning. Orter i nutida form när identifieringen är entydig (Stockholm, Uppsala, Västerås, Kalmar, Lübeck, Dalarna, Mora), annars textens form.
- Årtal, belopp och mått behålls som i texten.
- Om det finns översättningsfiler för samma verk i data/oversattningar/fornsvenska/ (samma filnamnsbörjan), läs dem och använd samma namnformer.
- Kontrollera ord med fornmed_ordbok (Söderwall) när du är osäker; SAOB (saob.se) om du kan nå den."""
SARSKILT = {"prosa": """- Behåll styckeindelningen; texten har inga versrader."""}
def typ(verk):
    return "prosa"
def prompt(nr):
    u = uppdrag[nr - 147]
    jobbrader = "\n".join(
        f"- {j['verk']}, passagerna {j['fran']}–{j['till']-1} i ordning ({j['tecken']} tecken) → {j['fil']}\n"
        f"  hämta: python {S}/kalltext.py {j['verk']} --fran {j['fran']} --till {j['till']} --typer originaltext\n"
        f"  kontrollera: python {S}/kontrollera_oversattning.py {j['fil']} {j['verk']} {j['fran']} {j['till']}"
        for j in u)
    sarskilt = "\n".join(dict.fromkeys(SARSKILT[typ(j["verk"])] for j in u))
    return f"""Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: 1500-talets svenska):
{jobbrader}

{GEMENSAMT}
{sarskilt}

ARBETSSÄTT:
- Kör python-kommandona med ~/MCP-Servers/.venv-v2/bin/python (det finns inget python i projektmappen).
- Använd ENDAST arbetskatalogen {S}/jobb_{nr}/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {{id: {{adress, sprak, text}}}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {{originalpassagens id: svensk översättning}} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Andra delar av samma krönika översätts parallellt av andra; följ namnformerna ovan.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser."""
if __name__ == "__main__":
    print(prompt(int(sys.argv[1])))

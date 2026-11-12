"""Skriver ut uppdraget för jobb N (75–132) ur uppdrag_fornsvenska_2.json: python uppdragsprompt2.py N [fil]"""
import json, sys
S = "<arbetsmapp>"
uppdrag = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "uppdrag_fornsvenska_2.json"))
GEMENSAMT = """SÄRSKILT FÖR FORNSVENSKA:
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion. Utgivarens upplysningar om handskriften (luckor, utplånad text) återges inom hakparentes på svenska.
- Upprepningar och uppenbara skrivfel i originalet översätts som de står; textens läsning byts aldrig ut.
- Latinska inslag (rubriker, bibelcitat, böner, recept) översätts också till svenska.
- Kristus, jungfru Maria, apostlarna och helgonen i vedertagen svensk form; påven, kejsaren. Orter i nutida form när identifieringen är entydig (Rom, Jerusalem, Vadstena, Uppsala, Linköping), annars textens form.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker."""
SARSKILT = {
    "vers": """- Texten är vers med en versrad per rad. Översätt rad för rad till modern svensk prosa i versradens form: samma antal rader, samma radbrytningar, inget rim, inga sammanslagna rader.
- Personer i textens form (Ivan, Gawian, Lunet, Fredrik, Flores, Blanzeflor); kung Artur och drottning Eufemia i vedertagen form.""",
    "ordsprak": """- Varje ordspråk står på egen rad med sitt nummer; behåll numret och radindelningen. Översätt ordagrant utan att förklara eller modernisera bilden.""",
    "facktext": """- Det är fackprosa (läkekonst, jordbruk). Växter, sjukdomar, kroppsdelar, mått och redskap får modern svensk benämning när identifieringen är säker, med originalordet inom parentes vid första förekomsten i passagen; annars textens ord följt av [osäker tolkning]. Mängder och enheter i recepten behålls (skålpund, lod, kvintin).
- Behåll receptens och kapitlens numrering och rubriker.""",
    "didrik": """- Det är prosa; behåll styckeindelningen. Personerna i den form fornsvenska Didrikssagan har dem, enhetligt: Didrik av Bern, Hildebrand, Vidrik Verlandsson, Sigurd, Gunnar, Högne, Grimhild, Brynhild, Attila, Ermenrik, Sifka; andra i textens form.
- Andra delar av verket översätts parallellt av andra; håll dig därför till formerna ovan och till textens form.""",
    "birgitta": """- Det är prosa; behåll styckeindelning, böckernas och kapitlens numrering och rubriker. Birgitta kallas i texten ofta "bruden" (brudhin); översätt ordet, byt inte ut det mot namnet. Guds Son, Kristus, jungfru Maria, påven, kejsaren, konung Magnus.
- Andra delar av verket översätts parallellt av andra; håll dig till formerna ovan.""",
    "prosa": """- Texten är prosa; behåll styckeindelningen.""",
}
def typ(verk):
    if any(v in verk for v in ("herr_ivan", "hertig_fredrik", "flores")): return "vers"
    if "ordsprak" in verk: return "ordsprak"
    if any(v in verk for v in ("lakebok", "bondakonst")): return "facktext"
    if "didrik" in verk: return "didrik"
    if "birgitta" in verk or "regula" in verk: return "birgitta"
    return "prosa"
def prompt(nr):
    u = uppdrag[nr - 75]
    jobbrader = "\n".join(
        f"- {j['verk']}, passagerna {j['fran']}–{j['till']-1} i ordning ({j['tecken']} tecken) → {j['fil']}\n"
        f"  hämta: python {S}/kalltext.py {j['verk']} --fran {j['fran']} --till {j['till']} --typer originaltext\n"
        f"  kontrollera: python {S}/kontrollera_oversattning.py {j['fil']} {j['verk']} {j['fran']} {j['till']}"
        for j in u)
    sarskilt = "\n".join(dict.fromkeys(SARSKILT[typ(j["verk"])] for j in u))
    return f"""Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: fornsvenska):
{jobbrader}

{GEMENSAMT}
{sarskilt}

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen {S}/jobb_{nr}/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {{id: {{adress, sprak, text}}}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {{originalpassagens id: svensk översättning}} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser."""
if __name__ == "__main__":
    print(prompt(int(sys.argv[1])))

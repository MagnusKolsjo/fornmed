"""Skriver ut uppdraget för jobb N (60–74): python uppdragsprompt.py N"""
import json, sys
S = "<arbetsmapp>"
uppdrag = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "uppdrag_fornaldarsagor_legender.json"))
FORNSVENSKA = """SÄRSKILT FÖR FORNSVENSKA:
- Texterna är prosa (legender och uppenbarelser); behåll styckeindelningen.
- Helgon, kungar och kyrkans män i vedertagen svensk form: Erik den helige, Olav den helige, Sigfrid, Ansgar, Rimbert, Birgitta, Katarina, Magnus jarl, biskop Henrik, Kristus, jungfru Maria, påven. Orter i nutida form när identifieringen är entydig (Uppsala, Birka, Sigtuna, Växjö, Vadstena, Rom, Orkneyöarna, Nidaros), annars textens form.
- Textbankens tecken: {…} är handskriftens felaktiga läsning och [ ] utgivarens rättelse eller tillägg. Översätt rättelsen och bortse från det som står inom {…}; hakparenteserna själva skrivs inte ut. Snedstrecket / är handskriftens skiljetecken; ersätt det med vanlig interpunktion.
- Latinska inslag (rubriker, bibelcitat, böner) översätts också till svenska.
- Kontrollera centrala ord med fornmed_ordbok (Söderwall) när du är osäker."""
FORNVASTNORDISKA = """SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde; sagokungarna likaså där en svensk form är vedertagen: Ragnar lodbrok, Ivar vidfamne, Harald hildetand, Sigurd ring, Gautrek, Adils, Rolf krake, Starkad.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Svitjod, Götaland, Uppsala, Nidaros, Konstantinopel, Gårdarike); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker."""
def prompt(nr):
    u = uppdrag[nr - 60]
    sprak = u[0]["sprak"]
    jobbrader = "\n".join(
        f"- {j['verk']}, passagerna {j['fran']}–{j['till']-1} i ordning ({j['tecken']} tecken) → {j['fil']}\n"
        f"  hämta: python {S}/kalltext.py {j['verk']} --fran {j['fran']} --till {j['till']} --typer originaltext\n"
        f"  kontrollera: python {S}/kontrollera_oversattning.py {j['fil']} {j['verk']} {j['fran']} {j['till']}"
        for j in u)
    return f"""Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: {sprak}):
{jobbrader}

{FORNSVENSKA if sprak == "fornsvenska" else FORNVASTNORDISKA}

ARBETSSÄTT:
- Kör python-kommandona med python = python från projektmappen.
- Använd ENDAST arbetskatalogen {S}/jobb_{nr}/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {{id: {{adress, sprak, text}}}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {{originalpassagens id: svensk översättning}} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Om det redan finns översättningsfiler för samma verk (samma filnamnsbörjan i data/oversattningar/sagor/ eller fornsvenska/), läs dem och använd samma namnformer för återkommande personer och platser.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser."""
if __name__ == "__main__":
    print(prompt(int(sys.argv[1])))

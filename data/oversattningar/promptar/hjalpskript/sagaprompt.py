import json, sys
S = "<arbetsmapp>"
uppdrag = json.load(open(f"{S}/sagauppdrag.json"))
def prompt(nr):
    u = uppdrag[nr - 1]
    sprak = u[0]["sprak"]
    jobbrader = "\n".join(
        f"- {j['verk']}, passagerna {j['fran']}–{j['till']-1} i ordning ({j['tecken']} tecken) → {j['fil']}\n"
        f"  hämta: python {S}/kalltext.py {j['verk']} --fran {j['fran']} --till {j['till']} --typer originaltext\n"
        f"  kontrollera: python {S}/kontrollera_oversattning.py {j['fil']} {j['verk']} {j['fran']} {j['till']}"
        for j in u)
    if "idfil" in u[0]:
        j = u[0]
        jobbrader = (f"- {j['verk']}, de passager vars id står i {j['idfil']} → {j['fil']}\n"
                     f"  hämta: python {S}/kalltext_ids.py {j['idfil']} [--fran N --till M]\n"
                     f"  kontrollera: python {S}/kontroll_ids.py {j['fil']} {j['idfil']}\n"
                     f"  Namnformer: följ de redan översatta Fagrskinna-filerna data/oversattningar/sagor/fagrskinna__*.json "
                     f"(läs dem för samma personer och platser). Harald Sigurðarson heter Harald hårdråde.")
    special = ("""SÄRSKILT FÖR FORNSVENSKA:
- Rimkrönikorna (Erikskrönikan, Karlskrönikan) har en versrad per rad. Översätt rad för rad till modern svenska prosa i versradens form: samma antal rader, samma radbrytningar, inget rim, inga sammanslagna rader.
- Konungastyrelsen och Prosaiska krönikan är prosa; behåll styckeindelningen.
- Kungar och kända personer i vedertagen svensk form (Magnus Ladulås, Birger Magnusson, hertig Erik, Karl Knutsson, Engelbrekt, drottning Margareta); orter i nutida form när identifieringen är entydig (Nyköping, Stockholm, Kalmar), annars textens form.""" if sprak == "fornsvenska" else
    """SÄRSKILT FÖR FORNVÄSTNORDISKA:
- Islänningar och andra personer i textens fornvästnordiska grundform (nominativ, utan böjning): Þorsteinn, Guðrún, Gunnarr kan skrivas Gunnar om texten själv växlar — välj en form per person och håll den. Tillnamn översätts när de är begripliga ord ("Ketill flatnefr" → "Ketill flatnos"), annars behålls de.
- Norska, danska och svenska kungar och jarlar i vedertagen svensk form: Harald hårfagre, Olav Tryggvason, Olav den helige, Håkon jarl, Erik segersäll, Olof skötkonung, Knut den store, Sven tveskägg, Magnus den gode, Harald hårdråde.
- Länder och kända orter i svensk form (Norge, Island, Danmark, Sverige, Uppsala, Nidaros, Konstantinopel); isländska gårdar, fjordar och mindre orter i textens form (Hlíðarendi, Borg).
- Skaldestrofer: översätt rad för rad med strofens radbrytningar. Kenningar översätts ordagrant, utan upplösning eller förklaring; sätt [osäker tolkning] där strofens innebörd är osäker.""")
    return f"""Du maskinöversätter medeltida texter till modern svenska i projektet <projektmapp> (fornmed). Läs data/oversattningar/RIKTLINJER.md först och följ den exakt: troget och fullständigt, varje sats, inga sammanfattningar, inga egna tillägg eller förklaringar i parentes, fackord med originalordet inom parentes vid första förekomst i passagen, [osäker tolkning] efter osäkra tolkningar, [oklart]/[oläslig] för skadad text.

DINA JOBB (källspråk: {sprak}):
{jobbrader}

{special}

ARBETSSÄTT:
- Använd ENDAST arbetskatalogen {S}/saga_{nr:02d}/ (skapa den) för egna hjälpfiler och skript; ge dem unika namn. Skriv inga andra filer än dina utfiler ovan.
- Hämta originalen med hämta-kommandot (JSON {{id: {{adress, sprak, text}}}}), gärna i mindre delar via --fran/--till inom ditt intervall.
- Utfilen är ett JSON-objekt {{originalpassagens id: svensk översättning}} med exakt de id som ingår i ditt intervall. Skriv inkrementellt med json.dump (ensure_ascii=False) efter varje passage eller några passager, så att inget går förlorat om du avbryts; läs in befintlig fil först och översätt bara id som saknas.
- Du kan slå upp ord med verktyget fornmed_ordbok (Schlyter, Söderwall) om du har det.
- Kör kontrollera-kommandot för varje utfil när du är klar; det ska ge OK utan saknade, extra eller tomma id. Längdkvoter utanför 0,6–2,2 ska ha en förklaring.

Avsluta med en kort rapport per utfil: antal passager, kontrollens resultat, antal [osäker tolkning], och namnformer du valt för återkommande personer och platser."""
if __name__ == "__main__":
    print(prompt(int(sys.argv[1])))

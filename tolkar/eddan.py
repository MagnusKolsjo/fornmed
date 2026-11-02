"""
Tolk för den poetiska Eddan ur heimskringla.no: Finnur Jónssons
fornisländska text (De gamle Eddadigte, 1932) och Erik Brates svenska
översättning (Eddan, 1913), båda fria från upphovsrätt.

Varje kväde blir ett verk med en passage för originalet och en för
översättningen; stroferna står kvar numrerade i texten. Finnur Jónssons
danska kommentar mellan stroferna tas bort. Kväden som bara finns i den
ena utgåvan (Brates Solsången och prosastyckena, Finnur Jónssons Vǫluspǫ́
hin skamma) får bara den passagen.

Användning:
    python -m tolkar.eddan
    python -m tolkar.eddan --torr
"""

import argparse
import html
import logging
import re
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda
from tolkar.heimskringla_no import hamta_wikitext, rensa_wiki, sidlank

log = logging.getLogger("tolkar.eddan")

UTG_FJ = "utgava:eddan:finnur_jonsson1932"
UTG_BRATE = "utgava:eddan:brate1913"

# (verkets id-del, namn, sida hos Finnur Jónsson, sida hos Brate), i Codex Regius ordning
KVADEN = [
    ("voluspa", "Vǫluspá", "Vǫluspǫ́", "Valans spådom"),
    ("havamal", "Hávamál", "Hávamǫ́l", "Den Höges sång"),
    ("vafthrudnismal", "Vafþrúðnismál", "Vafþrúðnismǫ́l", "Sången om Vavtrudner"),
    ("grimnismal", "Grímnismál", "Grímnismǫ́l", "Sången om Grimner"),
    ("skirnismal", "Skírnismál", "Skírnismǫ́l", "Sången om Skirner"),
    ("harbardsljod", "Hárbarðsljóð", "Hárbarðsljóð (FJ)", "Sången om Harbard"),
    ("hymiskvida", "Hymiskviða", "Hymiskviða (FJ)", "Kvädet om Hymer"),
    ("lokasenna", "Lokasenna", "Lokasenna (FJ)", "Loketrätan"),
    ("thrymskvida", "Þrymskviða", "Þrymskviða (FJ)", "Kvädet om Trym"),
    ("volundarkvida", "Vǫlundarkviða", "Vǫlundarkviða", "Kvädet om Volund"),
    ("alvissmal", "Alvíssmál", "Alvíssmǫ́l", "Sången om Allvis"),
    ("baldrs_draumar", "Baldrs draumar", "Baldrs draumar (FJ)", "Balders drömmar"),
    ("rigsthula", "Rígsþula", "Rígsþula (FJ)", "Rigstula (Erik Brate)"),
    ("hyndluljod", "Hyndluljóð", "Hyndluljóð (FJ)", "Hyndlas sång"),
    ("voluspa_hin_skamma", "Vǫluspá hin skamma", "Vǫluspǫ́ hin skamma", None),
    ("grogaldr", "Grógaldr", "Grógaldr (FJ)", "Groas trollsång"),
    ("fjolsvinnsmal", "Fjǫlsvinnsmál", "Fjǫlsvinnsmǫ́l", "Sången om Fjolsvinn"),
    ("helgakvida_hjorvardssonar", "Helgakviða Hjǫrvarðssonar", "Helgakviða Hjǫrvarðssonar",
     "Kvädet om Helge Hjorvardsson"),
    ("helgakvida_hundingsbana_i", "Helgakviða Hundingsbana I", "Vǫlsungakviða",
     "Första kvädet om Helge Hundingsbane"),
    ("helgakvida_hundingsbana_ii", "Helgakviða Hundingsbana II", "Vǫlsungakviða hin forna (Helg. hund. II)",
     "Andra kvädet om Helge Hundingsbane"),
    ("fra_dauda_sinfjotla", "Frá dauða Sinfjǫtla", None, "Om Sinfjotles död"),
    ("gripisspa", "Grípisspá", "Grípisspǫ́", "Gripers spådom"),
    ("reginsmal", "Reginsmál", "Reginsmǫ́l", "Sången om Regin"),
    ("fafnismal", "Fáfnismál", "Fáfnismǫ́l", "Sången om Favner"),
    ("sigrdrifumal", "Sigrdrífumál", "Sigrdrífumǫ́l", "Sången om Sigrdriva"),
    ("brot_af_sigurdarkvidu", "Brot af Sigurðarkviðu", "Sigurðarkviða hin meiri (Brot)",
     "Brottstycke av det större kvädet om Sigurd"),
    ("gudrunarkvida_i", "Guðrúnarkviða I", "Goðrúnarkviða (I)", "Första kvädet om Gudrun"),
    ("sigurdarkvida_hin_skamma", "Sigurðarkviða hin skamma", "Sigurðarkviða hin skamma",
     "Det korta kvädet om Sigurd"),
    ("helreid_brynhildar", "Helreið Brynhildar", "Helreið", "Brynhilds färd till Hel"),
    ("drap_niflunga", "Dráp Niflunga", None, "Nivlungarnes dråp"),
    ("gudrunarkvida_ii", "Guðrúnarkviða II", "Goðrúnarkviða hin forna (II)", "Andra kvädet om Gudrun"),
    ("gudrunarkvida_iii", "Guðrúnarkviða III", "Goðrúnarkviða (III)", "Tredje kvädet om Gudrun"),
    ("oddrunargratr", "Oddrúnargrátr", "Oddrúnargrátr", "Oddruns gråt"),
    ("atlakvida", "Atlakviða", "Atlakviða (FJ)", "Kvädet om Atle"),
    ("atlamal", "Atlamál", "Atlamǫ́l", "Den grönländska sången om Atle"),
    ("gudrunarhvot", "Guðrúnarhvǫt", "Goðrúnarhvǫt", "Gudruns eggelse"),
    ("hamdismal", "Hamðismál", "Hamðismǫ́l", "Sången om Hamder"),
    ("grottasongr", "Grottasǫngr", "Gróttasǫngr", "Grottesången"),
    ("solarljod", "Sólarljóð", None, "Solsången"),
]


def _brodtext(wikitext: str) -> str:
    """Sidans text efter språktabellen och utgåvans titelblock."""
    if "Velg språk" in wikitext:
        wikitext = wikitext[wikitext.find("|}", wikitext.find("Velg språk")) + 2:]
    wikitext = re.sub(r"\[\[Kategori:[^\]]*\]\]", "", wikitext)
    return re.sub(r"\[\[(?:Fil|Bilde|File):[^\]]*\]\]", "", wikitext)


def _slutrensa(text: str) -> str:
    text = html.unescape(rensa_wiki(text)).replace("]]", "")
    text = re.sub(r"(?m)^\s*-{4,}\s*$", "", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def finnur_jonsson(sida: str) -> str:
    """
    Kvädets text utan Finnur Jónssons kommentarer, titelblock och danska
    inledning. Kommentarerna står i blockquote; inledningen om handskrifterna
    står före en skiljelinje (----) och den första strofen.
    """
    text = _brodtext(hamta_wikitext(sida)[0])
    text = re.sub(r"<blockquote>.*?</blockquote>", "", text, flags=re.S)
    text = re.sub(r"<center>.*?</center>", "", text, flags=re.S)
    # Titelblocket står inte alltid inom center; det slutar med förlagsorten och året
    text = re.sub(r"^.*?K[øo]benhavn,?\s*1932", "", text, count=1, flags=re.S)
    forsta = re.search(r"(?m)^[:\s]*(?:'{3}\s*)?1\.", text)
    linjer = [m for m in re.finditer(r"(?m)^\s*-{4,}\s*$", text) if not forsta or m.start() < forsta.start()]
    if linjer:
        text = text[linjer[-1].end():]
    text = _slutrensa(text)
    # Kvar blir ibland en dansk inledningsmening utan skiljelinje ("Dette digt, der kun
    # findes i R …"); orden nedan förekommer inte i fornisländskan
    dansk = re.compile(r"\b(?:digt|digtet|findes|henvises|hds|behandling|overleveret|tolke|egenligste)\b")
    return "\n".join(r for r in text.split("\n") if not dansk.search(r) and not re.fullmatch(r"\s*_{5,}\s*", r))


def brate(sida: str) -> str:
    """Kvädets text i Brates översättning; texten står i blockquote."""
    text = _brodtext(hamta_wikitext(sida)[0])
    delar = re.findall(r"<blockquote>(.*?)</blockquote>", text, flags=re.S)
    text = "\n".join(delar) if delar else re.sub(r"<center>.*?</center>", "", text, flags=re.S)
    return _slutrensa(re.sub(r"<br\s*/?>", "\n", text))


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="eddan", namn="Den poetiska Eddan (Finnur Jónsson 1932; Brate 1913)",
            utgivare="heimskringla.no", url="https://heimskringla.no/wiki/Eddan",
            licens="Public domain (enligt heimskringla.no; sajten anges som källa)", version="2026-10"),
        verk=[])
    for ordning, (nyckel, namn, fj, br) in enumerate(KVADEN, start=1):
        verk_id = f"verk:edda:{nyckel}"
        paket.verk.append(Verk(
            id=verk_id, titel=namn, genre="eddadikt", sprak=["non"],
            beskrivning=("Eddakväde. Bevarat i Codex Regius (GKS 2365 4to, omkring 1270) eller i andra "
                         "handskrifter; kvädenas tillkomsttid är omstridd och varierar mellan kvädena."),
            extern_url=f"https://heimskringla.no/wiki/{(fj or br).replace(' ', '_')}"))
        if fj:
            paket.utgavor.append((verk_id, Utgava(
                f"{UTG_FJ}:{nyckel}", f"Finnur Jónsson (utg.), De gamle Eddadigte, København 1932: {fj}. "
                                      "heimskringla.no.", "Public domain")))
            paket.passager.append((verk_id, Passage(
                id=f"edda:{nyckel}:non", typ="originaltext", adress=f"{namn} (Finnur Jónsson 1932)",
                sprak="non", text=finnur_jonsson(fj), ordning=ordning, utgava_id=f"{UTG_FJ}:{nyckel}",
                url=sidlank(fj))))
        if br:
            paket.utgavor.append((verk_id, Utgava(
                f"{UTG_BRATE}:{nyckel}", f"Erik Brate (övers.), Eddan: de nordiska guda- och hjältesångerna, "
                                         f"Stockholm 1913: {br}. heimskringla.no.", "Public domain")))
            paket.passager.append((verk_id, Passage(
                id=f"edda:{nyckel}:swe", typ="oversattning", adress=f"{namn}: {br} (Brate 1913)",
                sprak="swe", text=brate(br), ordning=1000 + ordning, utgava_id=f"{UTG_BRATE}:{nyckel}",
                url=sidlank(br))))
    paket.lagg_till_maskinoversattningar(Path(__file__).parent.parent / "data" / "oversattningar" / "eddan_sv.json", "fornvästnordiskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa passagerna utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    for _, p in paket.passager:
        log.info("%-60s %6d tecken | %s", p.adress[:60], len(p.text), p.text[:60].replace("\n", " / "))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

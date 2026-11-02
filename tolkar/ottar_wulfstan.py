"""
Tolk för Ottars (Ohthere) och Wulfstans reseberättelser och den fornengelska
Orosius beskrivning av Europas folk, efter Henry Sweets utgåva Extracts from
Alfred's Orosius (Oxford 1885), public domain.

Avsnitten är de tillägg som gjordes i den fornengelska översättningen av
Orosius under Alfreds tid: beskrivningen av Europa norr om Donau (med
Cwenland, Sweon, Scridefinnas och Osti), Ottars berättelse för kung Alfred
och Wulfstans färd från Hedeby till Truso.

Internet Archives OCR av utgåvan (extractsfromalfr00alfruoft) förvanskar þ, æ
och ⁊ och blandar in Sweets noter, radnummer och den latinska parallelltexten.
Därför laddas texten inte direkt ur OCR:en utan ur en rensad transkription i
data/transkriptioner/ottar_wulfstan.json, gjord av språkmodell och ogranskad.
OCR:en hämtas ändå och används för att kontrollera att varje rensat stycke
fortfarande motsvarar utgåvans text, så att ett stycke som rensats fel eller
hamnat under fel id upptäcks.

Passagerna följer Sweets stycken; adressen anger avsnitt, sida och rader i
utgåvan. En engelsk översättning (Hakluyt/Goldsmid 1889, The Discovery of
Muscovy) prövades men saknas i Internet Archives skanning (sidorna 165–188
fattas), och är därför inte med.

Svensk översättning av språkmodell ligger i
data/oversattningar/ottar_wulfstan_sv.json.

Användning:
    python -m tolkar.ottar_wulfstan
    python -m tolkar.ottar_wulfstan --torr
"""

import argparse
import difflib
import json
import logging
import re
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

log = logging.getLogger("tolkar.ottar_wulfstan")

ROT = Path(__file__).parent.parent
OCR_FIL = ROT / "data" / "raw" / "ottar_wulfstan" / "extractsfromalfr00alfruoft_djvu.txt"
OCR_URL = "https://archive.org/download/extractsfromalfr00alfruoft/extractsfromalfr00alfruoft_djvu.txt"
TRANSKRIPTIONER = ROT / "data" / "transkriptioner" / "ottar_wulfstan.json"
OVERSATTNINGAR = ROT / "data" / "oversattningar" / "ottar_wulfstan_sv.json"
VERK_ID = "verk:ottar_wulfstan"
UTG = "utgava:ottar_wulfstan:sweet1885"

# Sweets indelning: passage-id -> (avsnitt, sidor, rader). Raderna räknas om
# från 1 i varje avsnitt i utgåvan, så adressen måste ange avsnittet.
STYCKEN = {
    "ottar_wulfstan:europa:1": ("III Europe", "10–12", "1–10"),
    "ottar_wulfstan:europa:2": ("III Europe", "12–13", "11–50"),
    "ottar_wulfstan:ottar:1": ("IV Ohthere's Voyage", "13", "1–6"),
    "ottar_wulfstan:ottar:2": ("IV Ohthere's Voyage", "13–14", "7–31"),
    "ottar_wulfstan:ottar:3": ("IV Ohthere's Voyage", "14–15", "32–45"),
    "ottar_wulfstan:ottar:4": ("IV Ohthere's Voyage", "15", "46–61"),
    "ottar_wulfstan:ottar:5": ("IV Ohthere's Voyage", "15", "62–74"),
    "ottar_wulfstan:ottar:6": ("IV Ohthere's Voyage", "15–16", "75–82"),
    "ottar_wulfstan:ottar:7": ("IV Ohthere's Voyage", "16", "83–95"),
    "ottar_wulfstan:ottar:8": ("IV Ohthere's Voyage", "16", "96–105"),
    "ottar_wulfstan:wulfstan:1": ("V Wulfstan's Voyage", "17", "1–19"),
    "ottar_wulfstan:wulfstan:2": ("V Wulfstan's Voyage", "17–19", "20–60"),
}

# Under denna andel av stycket som återfinns i OCR:en har stycket troligen
# rensats fel eller fått fel id; värdet ligger klart under vad korrekt rensade
# stycken ger, eftersom OCR:en också har egna fel.
MINSTA_LIKHET = 0.8


def hamta_ocr() -> str:
    if not OCR_FIL.exists():
        OCR_FIL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(OCR_URL, OCR_FIL)
    return OCR_FIL.read_text(encoding="utf-8")


def _skelett(text: str) -> str:
    """
    Konsonantskelett för jämförelse mellan rensad text och OCR. OCR:en läser
    þ som f>, ]?, J> m.fl. och æ som ae, se eller a3, så vokaler och de tecken
    som þ förväxlas med (f, p, j) tas bort; kvar blir det som OCR:en läser säkert.
    """
    return re.sub(r"[^bcdghklmnqrstvwxz]", "", text.lower())


def kontrollera_mot_ocr(texter: dict[str, str]) -> None:
    """Varnar för stycken vars skelett inte återfinns i OCR:ens fornengelska avsnitt."""
    ocr = hamta_ocr()
    # Avsnitt III börjar med Europa-styckets första ord; VI (Europe continued) avslutar
    start = ocr.find("Nu  haebbe  we  scortlice")
    slut = ocr.find("EUROPE  (continued", start)
    if start < 0 or slut < 0:
        log.warning("Hittade inte avsnitten III–V i OCR:en; kontrollen hoppas över")
        return
    skelett_ocr = _skelett(ocr[start:slut])
    for pid, text in texter.items():
        s = _skelett(text)
        # Jämförelsen görs mot ett fönster kring styckets längsta gemensamma bit:
        # mot hela avsnittet går nästan vad som helst att matcha som delföljd.
        # Fönstret har marginal för den latinska parallelltext som kan ligga mitt i
        # ett stycke, och bara gemensamma bitar om minst fyra tecken räknas, så
        # att spridda enstaka konsonanter inte ger skenbar likhet.
        m = difflib.SequenceMatcher(None, s, skelett_ocr, autojunk=False).find_longest_match(
            0, len(s), 0, len(skelett_ocr))
        fonster = skelett_ocr[max(0, m.b - m.a - 1500):m.b - m.a + len(s) + 1500]
        block = difflib.SequenceMatcher(None, s, fonster, autojunk=False).get_matching_blocks()
        likhet = sum(b.size for b in block if b.size >= 4) / max(len(s), 1)
        if likhet < MINSTA_LIKHET:
            log.warning("%s: bara %.0f %% av stycket återfinns i OCR:en", pid, 100 * likhet)
        else:
            log.debug("%s: %.0f %% i OCR:en", pid, 100 * likhet)


def las_transkriptioner() -> dict[str, str]:
    # Nycklar som börjar med '_' är beskrivningar av filen, inte passager
    texter = {k: v for k, v in json.loads(TRANSKRIPTIONER.read_text(encoding="utf-8")).items()
              if not k.startswith("_")}
    if set(texter) != set(STYCKEN):
        raise ValueError(f"Transkriptionerna stämmer inte med Sweets stycken: "
                         f"saknas {sorted(set(STYCKEN) - set(texter))}, okända {sorted(set(texter) - set(STYCKEN))}")
    return texter


def bygg_paket(kontrollera_ocr: bool = True) -> Kallpaket:
    texter = las_transkriptioner()
    if kontrollera_ocr:
        kontrollera_mot_ocr(texter)
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="ottar_wulfstan",
            namn="Ottar och Wulfstan ur den fornengelska Orosius (Sweet 1885, rensad OCR ur Internet Archive)",
            utgivare="Internet Archive (skanning: University of Toronto)",
            url="https://archive.org/details/extractsfromalfr00alfruoft",
            licens="Public domain", version="djvu.txt; transkription rensad av språkmodell"),
        verk=[Verk(
            id=VERK_ID, titel="Ottars och Wulfstans berättelser (ur den fornengelska Orosius)",
            genre="geografi", sprak=["ang"],
            datering_edtf="0890/0899", datering_fran=8900101, datering_till=8991231,
            beskrivning="Tillägg i den fornengelska översättningen av Orosius Historiae adversus paganos, "
                        "gjord under kung Alfreds tid: en beskrivning av folken i Europa norr om Donau "
                        "(bl.a. Sweon, Osti, Cwenland och Scridefinnas), den norske Ottars (Ohthere) berättelse "
                        "för kung Alfred om färden runt Nordkalotten till Beormas land och söderut till Sciringes "
                        "heal och Hedeby, samt Wulfstans berättelse om seglatsen från Hedeby till Truso och om "
                        "Estas seder.",
            extern_url="https://archive.org/details/extractsfromalfr00alfruoft")],
        utgavor=[(VERK_ID, Utgava(
            UTG, "Henry Sweet (utg.), Extracts from Alfred's Orosius, Oxford 1885, avsnitt III–V (s. 10–19). "
                 "Text rensad av språkmodell (Claude) ur Internet Archives OCR (extractsfromalfr00alfruoft), "
                 "jämförd med Sweets EETS-utgåva 1883 (kingalfredsorosi79oros); noter och latinsk "
                 "parallelltext borttagna. Ogranskad mot sidbild.", "Public domain"))],
    )
    for ordning, (pid, (avsnitt, sidor, rader)) in enumerate(STYCKEN.items(), start=1):
        paket.passager.append((VERK_ID, Passage(
            id=pid, typ="originaltext", adress=f"Sweet 1885, {avsnitt}, s. {sidor}, r. {rader}",
            sprak="ang", text=texter[pid], ordning=ordning, utgava_id=UTG,
            url="https://archive.org/details/extractsfromalfr00alfruoft")))
    antal = paket.lagg_till_maskinoversattningar(OVERSATTNINGAR, "fornengelskan")
    log.info("%d originalstycken, %d maskinöversättningar", len(STYCKEN), antal)
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och kontrollera utan att ladda")
    tolk.add_argument("--utan-ocr", action="store_true", help="hoppa över kontrollen mot OCR:en")
    arg = tolk.parse_args()
    paket = bygg_paket(kontrollera_ocr=not arg.utan_ocr)
    paket.kontrollera()
    log.info("%d passager", len(paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

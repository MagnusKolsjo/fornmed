"""
Parallella passager för skolier till Adam av Bremen ur Lappenbergs och
Waitz utgåva (MGH SS rer. Germ. 2, 2 uppl., Hannover 1876).

Lappenberg och Schmeidler numrerar skolierna olika och har olika läsarter,
så Lappenbergs text läggs som egna passager vid sidan av Schmeidlers, inte
som komplettering av dem. Bara skolier som är ofullständiga i OCR:en av
Schmeidlers utgåva tas med; numren mappas via de Lappenbergnummer
Schmeidler själv anger ('Schol. 138 (134).'). OCR:en av 1876 års tryck är
betydligt sämre än av Schmeidlers.

Ett skolion inleds 'Schol. 134.' och slutar med handskriftsnumren inom
parentes ('(5. 6. 8b. 10.)').

Användning:
    python -m tolkar.adam_skolier_lappenberg
"""

import argparse
import logging
import re
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, ladda
from tolkar import adam_skolier

log = logging.getLogger("tolkar.adam_skolier_lappenberg")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "adam_skolier"
OCR_URL = "https://archive.org/download/gestahammaburgen00adamuoft/gestahammaburgen00adamuoft_djvu.txt"
VERK_ID = adam_skolier.VERK_ID
UTGAVA_ID = "utgava:adam_av_bremen:lappenberg1876_skolier"

START = r"(?m)^\s*(?:\d{{1,2}}\s+)?S\s?[cr]?h[o0][lI1L]\s?[.,]?\s+{nr}\s*[.,]\s+"
# Handskriftsnumren som avslutar skoliet: '(2. 3. 4.)', '(8b. 9.)', '|2. 6. 6. 8*».)'
SLUT = re.compile(r"[(|]\s*(?:\d{1,2}[a-z]?[*»^'\"]*\.?\s*){1,6}[)|]")


def hamta() -> Path:
    fil = KATALOG / "lappenberg1876_djvu.txt"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        log.info("Hämtar %s", OCR_URL)
        urllib.request.urlretrieve(OCR_URL, fil)
    return fil


def skolion(text: str, lappenberg_nr: int) -> str | None:
    """Skoliets text till och med handskriftsparentesen, eller None om det inte hittas."""
    m = re.search(START.format(nr=lappenberg_nr), text)
    if not m:
        return None
    rest = text[m.end():m.end() + 3000]
    slut = SLUT.search(rest)
    stycke = rest[:slut.end()] if slut else rest.split("\n\n")[0]
    return adam_skolier.rensa(stycke.split("\n"))


def bygg_paket() -> Kallpaket:
    schmeidler = adam_skolier.tolka(adam_skolier.hamta().read_text(encoding="utf-8"))
    text = hamta().read_text(encoding="utf-8")
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="adam_skolier_lappenberg", namn="Adam av Bremen, skolierna (Lappenberg & Waitz 1876, OCR)",
            utgivare="Internet Archive (skanning: University of Toronto)",
            url="https://archive.org/details/gestahammaburgen00adamuoft", licens="Public domain",
            version="djvu.txt"),
        verk=[], befintliga_verk=[VERK_ID],
        utgavor=[(VERK_ID, Utgava(
            UTGAVA_ID, "J. M. Lappenberg & G. Waitz (utg.), Magistri Adam Bremensis Gesta Hammaburgensis "
                       "ecclesiae pontificum, 2 uppl., Hannover 1876 (MGH SS rer. Germ. 2): skolierna. "
                       "OCR ur Internet Archive (gestahammaburgen00adamuoft).", "Public domain"))])
    for s in schmeidler:
        if not (s.avbrutet and s.lappenberg):
            continue
        t = skolion(text, s.lappenberg)
        if not t:
            log.warning("Lappenbergs skolion %d (Schmeidler %d) hittades inte", s.lappenberg, s.nr)
            continue
        paket.passager.append((VERK_ID, Passage(
            id=f"adam_av_bremen:skolion_lappenberg:{s.lappenberg}", typ="skolion",
            adress=f"skolion {s.lappenberg} hos Lappenberg (= Schmeidler {s.nr}; Lappenberg & Waitz 1876; "
                   f"OCR av låg kvalitet)",
            sprak="lat", text=t, ordning=20000 + s.nr, utgava_id=UTGAVA_ID)))
    log.info("%d skolier ur Lappenbergs utgåva", len(paket.passager))
    paket.lagg_till_maskinoversattningar(
        Path(__file__).parent.parent / "data" / "oversattningar" / "adam_skolier_lappenberg_sv.json", "latinet")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    for _, p in paket.passager:
        log.info("%s | %s", p.adress, p.text[:90])
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

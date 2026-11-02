"""
Tolk för Snorres Edda ur heimskringla.no: den fornisländska texten i Guðni
Jónssons normaliserade utgåva och Anders Jacob D. Cnattingius svenska
översättning (1819).

Guðni Jónssons utgåva (1935, omtryckt 1954) är inte fri från upphovsrätt för
normaliseringen; den används här som på heimskringla.no, i en icke-
kommersiell forskningsdatabas, och utgåvan anges med licens därefter.
Cnattingius översättning är fri. Texterna delas per kapitel i respektive
utgåvas numrering; de två utgåvorna paras inte ihop.

Användning:
    python -m tolkar.snorres_edda
"""

import argparse
import html
import logging
import re

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda
from tolkar.heimskringla_no import hamta_wikitext, kapitel, rensa_wiki, sidlank

log = logging.getLogger("tolkar.snorres_edda")

VERK_ID = "verk:snorres_edda"
UTG_ON = "utgava:snorres_edda:gudni_jonsson"
UTG_SV = "utgava:snorres_edda:cnattingius1819"

# (del, sida med fornisländsk text, sida med svensk översättning)
DELAR = [
    ("Prologus", "Prologus", "Snorre Sturlesons Edda samt Skalda Förespråk"),
    ("Gylfaginning", "Gylfaginning", "Snorre Sturlesons Edda samt Skalda Gylfaginning"),
    ("Skáldskaparmál", "Skáldskaparmál", "Snorre Sturlesons Edda samt Skalda Brages Samtal"),
    ("Skáldskaparmál, omskrivningar", None, "Snorre Sturlesons Edda samt Skalda Omskrifningar"),
    ("Skáldskaparmál, okenningar", None, "Snorre Sturlesons Edda samt Skalda Oomskrifna namn"),
    ("Skáldatal", "Skáldatal", None),
]


def _slug(text: str) -> str:
    t = text.lower()
    for a, b in (("á", "a"), ("ð", "d"), ("þ", "th"), ("æ", "ae"), ("ó", "o"), ("í", "i"), ("é", "e")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _delar(sida: str) -> list[tuple[int | None, str]]:
    """(kapitelnummer, text); en sida utan numrerade kapitel blir en enda del."""
    text = hamta_wikitext(sida)[0]
    kap = kapitel(text)
    if kap:
        return [(nr, html.unescape((f"{nr}. {rubrik}\n" if rubrik else "") + t)) for nr, rubrik, t in kap]
    if "Velg språk" in text:
        text = text[text.find("|}", text.find("Velg språk")) + 2:]
    text = re.sub(r"<center>.*?</center>", "", text, flags=re.S)
    text = re.sub(r"\[\[(?:Fil|Bilde|File|Kategori):[^\]]*\]\]", "", text)
    return [(None, html.unescape(rensa_wiki(re.sub(r"<br\s*/?>", "\n", text))))]


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="snorres_edda", namn="Snorres Edda (Guðni Jónsson; Cnattingius 1819)",
            utgivare="heimskringla.no", url="https://heimskringla.no/wiki/Edda_Snorra_Sturlusonar",
            licens="Cnattingius: public domain; Guðni Jónsson: upphovsrätt för normaliseringen", version="2026-10"),
        verk=[Verk(id=VERK_ID, titel="Snorres Edda", upphov="Snorri Sturluson", genre="undersamling",
                   sprak=["non"], datering_edtf="1220/1241", datering_fran=12200101, datering_till=12411231,
                   beskrivning="Lärobok i skaldekonst med Gylfaginning, berättelsen om den nordiska "
                               "mytologin, Skáldskaparmál om skaldespråkets omskrivningar och Háttatal. "
                               "Skáldatal förtecknar skalder vid kungarnas hov.",
                   extern_url="https://heimskringla.no/wiki/Edda_Snorra_Sturlusonar")],
        utgavor=[(VERK_ID, Utgava(UTG_ON, "Guðni Jónsson (utg.), Edda Snorra Sturlusonar, Reykjavík 1954, "
                                          "heimskringla.no.",
                                  "Upphovsrätt för normaliseringen; används icke-kommersiellt")),
                 (VERK_ID, Utgava(UTG_SV, "A. J. D. Cnattingius (övers.), Snorre Sturlesons Edda samt Skalda, "
                                          "Stockholm 1819, heimskringla.no.", "Public domain"))])
    ordning = 0
    for namn, on_sida, sv_sida in DELAR:
        for sida, sprak, typ, utg in ((on_sida, "non", "originaltext", UTG_ON),
                                      (sv_sida, "swe", "oversattning", UTG_SV)):
            if not sida:
                continue
            for nr, text in _delar(sida):
                if len(text) < 40:
                    continue
                ordning += 1
                adress = f"{namn}" + (f", kap. {nr}" if nr is not None else "") + \
                         (" (Guðni Jónsson)" if sprak == "non" else " (Cnattingius 1819)")
                pid = f"snorres_edda:{_slug(namn)}:{nr if nr is not None else 'hela'}:{sprak}"
                paket.passager.append((VERK_ID, Passage(id=pid, typ=typ, adress=adress, sprak=sprak, text=text,
                                                        ordning=ordning, utgava_id=utg, url=sidlank(sida))))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    from collections import Counter
    log.info("%d passager: %s", len(paket.passager),
             Counter(p.adress.split(",")[0].split(" (")[0] + " " + p.sprak for _, p in paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

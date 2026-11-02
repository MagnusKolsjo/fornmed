"""
Ynglingatal ur Ynglinga saga.

Dikten är bevarad som citat i Snorres Ynglinga saga, där strofer om varje
kung anförs efter berättelsen om honom ('Svá segir Þjóðólfr:'). Citaten tas
ut ur Linder & Haggsons fornvästnordiska text och Emil Olsons svenska
översättning på heimskringla.no och paras i den ordning de står; de två
utgåvorna numrerar sagans kapitel olika, så adressen anger båda.

Ett citat kan omfatta mer än en strof; indelningen i strofer följer citaten
i sagan, inte någon utgåva av skaldediktningen. Strofer som Snorre anför av
andra skalder (Bragi, Eyvindr) tas inte med.

Användning:
    python -m tolkar.ynglingatal
"""

import argparse
import logging
import re

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda
from tolkar import heimskringla_no
from tolkar.heimskringla_no import sidlank

log = logging.getLogger("tolkar.ynglingatal")

VERK_ID = "verk:ynglingatal"
UTG_ON = "utgava:ynglingatal:linder-haggson"
UTG_SV = "utgava:ynglingatal:olson"

# Inledningen till ett citat namnger skalden och slutar med kolon
SKALD = re.compile(r"Þjóðólf|Thjodolv|Tjodolv")


def citat(kapitel: list[tuple[int, str, str]]) -> list[tuple[int, str]]:
    """
    (kapitelnummer, citatets rader) för varje citat ur Ynglingatal. Versraderna
    är indragna med ett blanksteg; i Linder & Haggsons text är den första
    raden inte indragen.
    """
    ut = []
    for nr, _, text in kapitel:
        rader = text.split("\n")
        for i, rad in enumerate(rader[:-1]):
            if not (rad.rstrip().endswith(":") and SKALD.search(rad)):
                continue
            vers = [rader[i + 1].strip()]
            for foljande in rader[i + 2:]:
                if not foljande.startswith(" "):
                    break
                vers.append(foljande.strip())
            if len(vers) > 1:
                ut.append((nr, "\n".join(vers)))
    return ut


def bygg_paket() -> Kallpaket:
    on_text, _ = heimskringla_no.hamta_wikitext("Ynglinga saga")
    sv_sida = heimskringla_no.svensk_sida(on_text)
    on = citat(heimskringla_no.kapitel(on_text))
    sv = citat(heimskringla_no.kapitel(heimskringla_no.hamta_wikitext(sv_sida)[0]))
    if len(on) != len(sv):
        raise ValueError(f"{len(on)} citat i originalet men {len(sv)} i översättningen; "
                         "citaten kan inte paras ihop")

    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="ynglingatal", namn="Ynglingatal ur Ynglinga saga (heimskringla.no)",
            utgivare="heimskringla.no", url="https://heimskringla.no/wiki/Ynglinga_saga",
            licens="Public domain (enligt heimskringla.no; sajten anges som källa)", version="2026-10"),
        verk=[Verk(
            id=VERK_ID, titel="Ynglingatal", upphov="Tillskrivs Þjóðólfr ór Hvini",
            genre="skaldedikt", sprak=["non"], datering_edtf="0850/1199",
            datering_fran=8500101, datering_till=11991231,
            beskrivning="Skaldedikt om ynglingaättens kungar, bevarat genom citat i Ynglinga saga. "
                        "Dateringen är omstridd; intervallet täcker både den traditionella och den "
                        "sena dateringen.",
            extern_url=sidlank("Ynglinga saga"))],
        utgavor=[
            (VERK_ID, Utgava(UTG_ON, "Citaten i Ynglinga saga efter N. Linder & H. A. Haggson (utg.), "
                                     "Heimskringla. Snorra Sturlusonar, Uppsala 1869–72. heimskringla.no.",
                             "Public domain")),
            (VERK_ID, Utgava(UTG_SV, f"Citaten i Ynglinga saga efter Emil Olson (övers.), Snorre "
                                     f"Sturlasson: Norges konungasagor, Lund 1919–26: {sv_sida}. "
                                     f"heimskringla.no.", "Public domain")),
        ],
    )
    for lopnr, ((on_kap, on_vers), (sv_kap, sv_vers)) in enumerate(zip(on, sv), start=1):
        adress = (f"citat {lopnr} av {len(on)} (Ynglinga saga kap. {on_kap} hos Linder & Haggson "
                  f"= kap. {sv_kap} hos Olson)")
        paket.passager.append((VERK_ID, Passage(
            id=f"ynglingatal:non:{lopnr}", typ="originaltext", adress=adress, sprak="non",
            text=on_vers, ordning=lopnr, utgava_id=UTG_ON, url=sidlank("Ynglinga saga"))))
        paket.passager.append((VERK_ID, Passage(
            id=f"ynglingatal:swe:{lopnr}", typ="oversattning", adress=adress, sprak="swe",
            text=sv_vers, ordning=1000 + lopnr, utgava_id=UTG_SV, url=sidlank(sv_sida))))
    log.info("%d citat ur Ynglingatal", len(on))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa citaten utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    if arg.torr:
        for _, p in paket.passager:
            if p.sprak == "non":
                log.info("%s | %s", p.adress, p.text.split("\n")[0])
        return
    db.initiera_schema()
    ladda(paket)


if __name__ == "__main__":
    main()

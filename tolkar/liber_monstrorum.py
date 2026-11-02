"""
Tolk för Liber monstrorum de diversis generibus efter Moriz Haupts utgåva
(Index lectionum, Berlin 1863), OCR ur Internet Archive (public domain).

OCR:en har den textkritiska apparaten längst ned på varje sida; den känns
igen på handskriftssiglerna (A, B) och avgränsarna (II) och tas bort.
Radnummer i marginalen tas också bort. Texten delas i Haupts tre böcker
(människor, vilddjur, ormar) och hans kapitel; kapitelnumren avviker från
Orchards utgåva (Haupt I.3 = Orchard I.2, kung Huiglaucus).

Svensk översättning av språkmodell ligger i
data/oversattningar/liber_monstrorum_sv.json.

Användning:
    python -m tolkar.liber_monstrorum
    python -m tolkar.liber_monstrorum --dumpa FIL
"""

import argparse
import json
import logging
import re
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

log = logging.getLogger("tolkar.liber_monstrorum")

ROT = Path(__file__).parent.parent
FIL = ROT / "data" / "raw" / "liber_monstrorum" / "Haupt_Liber_monstrorum_djvu.txt"
URL = "https://archive.org/download/HauptLiberMonstrorum/Haupt_Liber_monstrorum_djvu.txt"
OVERSATTNINGAR = ROT / "data" / "oversattningar" / "liber_monstrorum_sv.json"
VERK_ID = "verk:liber_monstrorum"
UTG = "utgava:liber_monstrorum:haupt1863"
UTG_SV = "utgava:liber_monstrorum:sv_modell"
MASKIN = ("Svensk översättning gjord av språkmodell (Claude) från latinet i Haupts utgåva. Ogranskad; "
          "citera originalet eller en tryckt översättning.")
BOCKER = {"I.": 1, "II.": 2, "III.": 3}


def _apparat(rad: str) -> bool:
    """En apparatrad har flera handskriftssigler eller avgränsare (II, i OCR:en ofta U eller H)."""
    sigler = len(re.findall(r"\s[AB](?:\s?\d)?[.,:;]?(?:\s|$)", rad))
    sigler += len(re.findall(r"(?:^|\s)(?:II|U|H|ll|il|0)(?:\s|$)", rad))
    return sigler >= 2


def brodtext() -> str:
    if not FIL.exists():
        FIL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, FIL)
    text = FIL.read_text(encoding="utf-8")
    text = text[text.find("LIBER MONSTRORVM DE DIVERSIS GENERIBVS"):]
    ut = []
    for sida in re.split(r"Digitized by[^\n]*", text):
        rader = [r.strip() for r in sida.split("\n") if r.strip() and "oogle" not in r and "ooQle" not in r]
        # Apparaten börjar vid den första apparatraden som följs av fler
        for i, rad in enumerate(rader):
            if _apparat(rad) and sum(_apparat(x) for x in rader[i:i + 4]) >= 2:
                rader = rader[:i]
                break
        for rad in rader:
            if re.fullmatch(r"\d{1,3}", rad):
                continue
            ut.append(re.sub(r"^\d{1,2}\s+(?=[a-zA-Z]|\d{1,2}\.\s)", "", rad))
    return "\n".join(ut)


def kapitel() -> list[tuple[int, int, str]]:
    """(bok, kapitel, text)."""
    ut, bok = [], 0
    delar = re.split(r"(?m)^(I{1,3}\.)\s*$", brodtext())
    for markering, stycke in zip(delar[1::2], delar[2::2]):
        bok = BOCKER[markering]
        bitar = re.split(r"(?m)^(\d{1,2})\.\s+(?=[A-Z])", stycke)
        for nr, text in zip(bitar[1::2], bitar[2::2]):
            text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
            ut.append((bok, int(nr), re.sub(r"\s+", " ", text).strip()))
    return ut


def bygg_paket() -> Kallpaket:
    oversattning = json.loads(OVERSATTNINGAR.read_text(encoding="utf-8")) if OVERSATTNINGAR.exists() else {}
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="liber_monstrorum", namn="Liber monstrorum (Haupt 1863, OCR ur Internet Archive)",
            utgivare="Internet Archive", url="https://archive.org/details/HauptLiberMonstrorum",
            licens="Public domain", version="djvu.txt"),
        verk=[Verk(id=VERK_ID, titel="Liber monstrorum de diversis generibus", genre="undersamling", sprak=["lat"],
                   datering_edtf="0650/0750", datering_fran=6500101, datering_till=7501231,
                   beskrivning="Anglosaxisk latinsk katalog över monster, vilddjur och ormar i tre böcker. "
                               "I.3 (Haupt) om geternas kung Huiglaucus, som dödades av frankerna, är ett av "
                               "de få oberoende beläggen för Beowulfs Hygelac.",
                   extern_url="https://archive.org/details/HauptLiberMonstrorum")],
        utgavor=[(VERK_ID, Utgava(UTG, "M. Haupt (utg.), Liber monstrorum de diversis generibus, i Index "
                                       "lectionum … Universitate Friderica Guilelma, Berlin 1863. OCR ur Internet "
                                       "Archive; den textkritiska apparaten borttagen.", "Public domain")),
                 (VERK_ID, Utgava(UTG_SV, MASKIN, "CC BY-SA 4.0"))])
    for ordning, (bok, nr, text) in enumerate(kapitel(), start=1):
        pid = f"liber_monstrorum:{bok}.{nr}"
        adress = f"bok {bok}, kap. {nr} (Haupt 1863)"
        paket.passager.append((VERK_ID, Passage(id=pid, typ="originaltext", adress=adress, sprak="lat", text=text,
                                                ordning=ordning, utgava_id=UTG)))
        if f"{pid}:sv" in oversattning:
            paket.passager.append((VERK_ID, Passage(id=f"{pid}:sv", typ="oversattning",
                                                    adress=adress + " (maskinöversättning)", sprak="swe",
                                                    text=oversattning[f"{pid}:sv"], ordning=1000 + ordning,
                                                    utgava_id=UTG_SV)))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--dumpa", type=Path, help="skriv kapitlen som JSON och avsluta")
    tolk.add_argument("--torr", action="store_true", help="tolka utan att ladda")
    arg = tolk.parse_args()
    if arg.dumpa:
        texter = [dict(id=f"liber_monstrorum:{b}.{n}:sv", bok=b, kapitel=n, text=t) for b, n, t in kapitel()]
        arg.dumpa.write_text(json.dumps(texter, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("%d kapitel, %d tecken", len(texter), sum(len(t["text"]) for t in texter))
        return
    paket = bygg_paket()
    paket.kontrollera()
    log.info("%d passager", len(paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

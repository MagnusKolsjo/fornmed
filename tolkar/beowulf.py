"""
Tolk för Beowulf och Finnsburgfragmentet.

- Fornengelsk text: Harrison & Sharp, 4 uppl. 1894, ur Project Gutenberg
  (#9701, UTF-8 med längdtecken). Dikten är indelad i 43 avsnitt (fitter)
  och har radnummer var femte rad.
- Svensk översättning: Rudolf Wickberg, 2 uppl. 1914, ur svenska Wikisource.
  Översättningen följer originalet rad för rad med samma radnumrering, så
  den delas i samma fitter med samma radintervall som originalet.

Varje fitt blir två passager, original och översättning, med adressen
'fitt N, rad a–b'. Radnumren kontrolleras mot utgåvornas tryckta nummer.

Användning:
    python -m tolkar.beowulf          # hämtar, tolkar och laddar
    python -m tolkar.beowulf --torr   # tolkar och skriver statistik, laddar inte
"""

import argparse
import html
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, Vittne, ladda

log = logging.getLogger("tolkar.beowulf")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "beowulf"
GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/9701/pg9701.txt"
WIKISOURCE_API = "https://sv.wikisource.org/w/api.php"
WICKBERG_SIDA = "Beowulf: en fornengelsk hjältedikt (1914)"
USER_AGENT = "fornmed-forskningsdatabas/0.1 (öppen forskningsdatabas över medeltida källor)"

UTG_HS = "utgava:beowulf:harrison-sharp-1894"
UTG_WICKBERG = "utgava:beowulf:wickberg-1914"
UTG_FINNSBURG = "utgava:finnsburg:harrison-sharp-1894"

ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50}


def romersk(tal: str) -> int:
    varden = [ROMERSKA[t] for t in tal]
    return sum(-v if i + 1 < len(varden) and v < varden[i + 1] else v for i, v in enumerate(varden))


def _hamta(url: str, mal: Path) -> Path:
    if not mal.exists():
        log.info("Hämtar %s", url)
        mal.parent.mkdir(parents=True, exist_ok=True)
        forfragan = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(forfragan, timeout=60) as svar:
            mal.write_bytes(svar.read())
        # Wikimedia begränsar täta anrop från samma klient
        time.sleep(2)
    return mal


def _versrad(rad: str) -> str:
    """Halvverserna står åtskilda av flera blanksteg; de behålls åtskilda av tre."""
    return re.sub(r"\s{2,}", "   ", rad.strip())


def tolka_harrison_sharp(text: str) -> tuple[list[dict], list[dict]]:
    """
    Fitterna i Beowulf och raderna i Finnsburgfragmentet ur Gutenbergtexten.

    Varje versrad räknas; där utgåvan trycker ett radnummer kontrolleras
    räkningen mot det, och vid avvikelse följs utgåvans nummer.
    """
    rader = text.splitlines()
    start = next(i for i, r in enumerate(rader) if r.strip() == "BĒOWULF.")
    appendix = next(i for i, r in enumerate(rader) if r.strip() == "APPENDIX")
    slut = next(i for i, r in enumerate(rader) if i > appendix and "LIST OF NAMES; NOTES" in r)

    def versrader(fran: int, till: int, rubrik_monster: str | None):
        avsnitt, aktuellt, nr, avvikelser = [], None, 0, 0
        for r in rader[fran:till]:
            if rubrik_monster and (m := re.match(rubrik_monster, r)):
                aktuellt = {"nr": romersk(m.group(1)), "rubrik": m.group(2).strip(), "rader": []}
                avsnitt.append(aktuellt)
                continue
            # Versraderna är indragna; en rad med tryckt radnummer börjar med
            # numret, och fyrsiffriga nummer följs av bara ett blanksteg
            m = re.match(r"^(?:(\d+)\s+|\s{2,})(\S.*)$", r)
            if not m:
                continue
            nr += 1
            if m.group(1) and int(m.group(1)) != nr:
                avvikelser += 1
                nr = int(m.group(1))
            if aktuellt is None:
                aktuellt = {"nr": 1, "rubrik": "", "rader": []}
                avsnitt.append(aktuellt)
            aktuellt["rader"].append((nr, _versrad(m.group(2))))
        if avvikelser:
            log.warning("%d avvikelser mellan räknade och tryckta radnummer", avvikelser)
        return avsnitt

    fitter = versrader(start + 1, appendix, r"^([IVXL]+)\. (.+)$")
    finnsburg = versrader(appendix + 1, slut, None)
    return fitter, finnsburg


def hamta_wickberg() -> list[tuple[int, str]]:
    """Wickbergs översättning som (radnummer, text), i ordning, ur Wikisources fyra delar."""
    rader: list[tuple[int, str]] = []
    nr = 0
    for del_ in (1, 2, 3, 4):
        sida = f"{WICKBERG_SIDA}/{del_}"
        url = WIKISOURCE_API + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": sida, "prop": "text", "format": "json", "formatversion": 2})
        h = json.loads(_hamta(url, KATALOG / f"wickberg_{del_}.json").read_text(encoding="utf-8"))["parse"]["text"]
        h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
        # Fotnotsreferenserna står inne i raderna och tas bort
        h = re.sub(r'<sup[^>]*class="reference".*?</sup>', "", h, flags=re.S)
        for m in re.finditer(r'ws-poem-versenum">(\d+)\s*</span>|class="ws-poem-line">(.*?)<span class="ws-poem-break">',
                             h, flags=re.S):
            if m.group(1):
                # Versnumret står före den rad det gäller
                nr = int(m.group(1)) - 1
                continue
            text = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            if text:
                nr += 1
                rader.append((nr, text))
    return rader


def bygg_paket() -> Kallpaket:
    text = _hamta(GUTENBERG_URL, KATALOG / "pg9701.txt").read_text(encoding="utf-8")
    fitter, finnsburg = tolka_harrison_sharp(text)
    wickberg = dict(hamta_wickberg())

    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="beowulf", namn="Beowulf och Finnsburgfragmentet (Harrison & Sharp 1894; Wickberg 1914)",
            utgivare="Project Gutenberg; svenska Wikisource",
            url="https://www.gutenberg.org/ebooks/9701", licens="Public domain; transkription CC BY-SA 4.0",
            version="1"),
        verk=[
            # Påståendena och bedömningarna i pastaenden_hygelac.py pekar på
            # detta verk och dess fitter
            Verk(id="verk:beowulf", titel="Beowulf", genre="hjaltedikt", sprak=["ang"],
                 datering_edtf="0700/1025", datering_fran=7000101, datering_till=10251231,
                 beskrivning="Fornengelskt hjältedikt om geaten Beowulf. Tillkomsttiden är omstridd; "
                             "intervallet täcker de vanligaste förslagen.",
                 extern_url="https://www.gutenberg.org/ebooks/9701"),
            Verk(id="verk:finnsburg", titel="Finnsburgfragmentet", genre="hjaltedikt", sprak=["ang"],
                 beskrivning="Fragment av ett fornengelskt hjältedikt om striden i Finnsburg; samma "
                             "berättelse återges i Beowulf rad 1068–1159. Handskriften är förlorad; "
                             "texten är känd genom George Hickes tryck 1705.",
                 extern_url="https://www.gutenberg.org/ebooks/9701"),
        ],
        utgavor=[
            ("verk:beowulf", Utgava(UTG_HS, "James A. Harrison & Robert Sharp (utg.), Bēowulf: an "
                                    "Anglo-Saxon poem, 4 uppl., Boston 1894. Project Gutenberg #9701.",
                                    "Public domain")),
            ("verk:beowulf", Utgava(UTG_WICKBERG, "Rudolf Wickberg (övers.), Beowulf: en fornengelsk "
                                    "hjältedikt, 2 uppl. 1914. Svenska Wikisource.",
                                    "Public domain; transkription CC BY-SA 4.0")),
            ("verk:finnsburg", Utgava(UTG_FINNSBURG, "James A. Harrison & Robert Sharp (utg.), Bēowulf: "
                                      "an Anglo-Saxon poem, 4 uppl., Boston 1894, appendix. "
                                      "Project Gutenberg #9701.", "Public domain")),
        ],
        vittnen=[
            ("verk:beowulf", Vittne("vittne:beowulf:cotton_vitellius", "handskrift",
                                    "London, British Library, Cotton Vitellius A.xv (Nowell-kodexen)",
                                    "Cotton Vitellius A.xv", "0975/1025", 9750101, 10251231)),
        ],
    )

    saknas_sv = 0
    for fitt in fitter:
        a, b = fitt["rader"][0][0], fitt["rader"][-1][0]
        adress = f"fitt {fitt['nr']}, rad {a}–{b}"
        paket.passager.append(("verk:beowulf", Passage(
            id=f"beowulf:fitt:{fitt['nr']:02d}", typ="originaltext", adress=adress, sprak="ang",
            text=f"{fitt['nr']}. {fitt['rubrik']}\n" + "\n".join(t for _, t in fitt["rader"]),
            ordning=fitt["nr"], utgava_id=UTG_HS)))
        svenska = [wickberg[n] for n in range(a, b + 1) if n in wickberg]
        saknas_sv += (b - a + 1) - len(svenska)
        paket.passager.append(("verk:beowulf", Passage(
            id=f"beowulf:wickberg:fitt:{fitt['nr']:02d}", typ="oversattning", adress=adress, sprak="swe",
            text="\n".join(svenska), ordning=100 + fitt["nr"], utgava_id=UTG_WICKBERG)))
    if saknas_sv:
        log.warning("%d rader i originalet saknar motsvarighet i Wickbergs radnumrering", saknas_sv)

    rader = [r for avsnitt in finnsburg for r in avsnitt["rader"]]
    paket.passager.append(("verk:finnsburg", Passage(
        id="finnsburg:rad:1-", typ="originaltext", adress=f"rad 1–{rader[-1][0]}", sprak="ang",
        text="\n".join(t for _, t in rader), ordning=1, utgava_id=UTG_FINNSBURG)))
    paket.lagg_till_maskinoversattningar(Path(__file__).parent.parent / "data" / "oversattningar" / "beowulf_sv.json", "fornengelskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    fitter = [p for _, p in paket.passager if p.typ == "originaltext" and p.id.startswith("beowulf:")]
    log.info("Beowulf: %d fitter, sista adress %s; Finnsburg: %s", len(fitter), fitter[-1].adress,
             paket.passager[-1][1].adress)
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

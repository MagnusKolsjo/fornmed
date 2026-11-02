"""
Tolk för de fornsvenska krönikorna och Konungastyrelsen ur Språkbankens
"Fornsvenska textbankens material" (Korp, CC BY 4.0).

- Erikskrönikan (rimkrönika, skriven omkring 1320–35) efter Spegelbergs bok,
  Codex Holm D 2 (1470-talet).
- Karlskrönikan (rimkrönika om tiden 1389–1452).
- Konungastyrelsen (Um styrilsi konunga ok höfþinga, 1300-talets mitt) efter
  Johannes Bureus tryck 1634.
- Prosaiska krönikan (Sverige krönika, 1450-talet) efter Holm D 26; korpusen
  har bara början av texten.

Svenska översättningar gjorda av språkmodell ligger i
data/oversattningar/kronikor/ (se RIKTLINJER.md där) och laddas som egna
utgåvor märkta som maskinöversättning.

Korpusen markerar utgåvans sidor med "# N" och i rimkrönikorna en versrad
per stycke. Passagerna följer utgåvans sidor; adressen anger sidan.

Användning:
    python -m tolkar.fornsvenska_kronikor
    python -m tolkar.fornsvenska_kronikor --torr
"""

import argparse
import bz2
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, Vittne, ladda
from tolkar.fornsvenska_lagar import stycketext

log = logging.getLogger("tolkar.fornsvenska_kronikor")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "sprakbanken"
OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "kronikor"
KORPUSAR = {
    "fsv-verser": "https://spraakbanken.gu.se/resurser/meningsmangder/fsv-verser.xml.bz2",
    "fsv-profanprosa": "https://spraakbanken.gu.se/resurser/meningsmangder/fsv-profanprosa.xml.bz2",
}

# (titelns början i korpusen, verk-id, titel, genre, tillkomst, beskrivning, versform)
TEXTER = [
    ("Erikskrönikan", "verk:erikskronikan", "Erikskrönikan", "kronika", ("1320/1335", 13200101, 13351231),
     "Rimkrönika om Sveriges historia från mitten av 1200-talet till 1319, med tyngdpunkt på "
     "hertigarna Erik och Valdemar. Skriven omkring 1320–35; texten här efter en handskrift från "
     "1470-talet.", True),
    ("Karlskrönikan", "verk:karlskronikan", "Karlskrönikan", "kronika", ("1452", 14520101, 14521231),
     "Rimkrönika om tiden från Margaretas unionsdrottningskap till Karl Knutssons kungatid "
     "(1389–1452), skriven i Karl Knutssons krets.", True),
    ("Konungastyrelsen", "verk:konungastyrelsen", "Konungastyrelsen (Um styrilsi konunga ok höfþinga)",
     "furstespegel", ("1330/1350", 13300101, 13501231),
     "Furstespegel om hur kungar och hövdingar ska styra sig själva, sitt hov och sitt rike. "
     "Handskriften är förlorad; texten finns bara i Johannes Bureus tryck 1634.", False),
    ("Sverige krönika", "verk:prosaiska_kronikan", "Prosaiska krönikan (Sverige krönika)", "kronika",
     ("1448/1457", 14480101, 14571231),
     "Svensk krönika på prosa från goternas ursprung till 1400-talet. Korpusen har bara textens början.",
     False),
]


def hamta(korpus: str) -> Path:
    fil = KATALOG / f"{korpus}.xml.bz2"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        log.info("Hämtar %s", KORPUSAR[korpus])
        urllib.request.urlretrieve(KORPUSAR[korpus], fil)
    return fil


def _datering(text: str | None) -> tuple[str | None, int | None, int | None]:
    m = re.findall(r"\d{4}", text or "")
    if not m:
        return None, None, None
    return "/".join(dict.fromkeys([m[0], m[-1]])), int(m[0] + "0101"), int(m[-1] + "1231")


def sidor(stycken: list[str], vers: bool) -> list[tuple[str, str]]:
    """(sida, text) per sida i utgåvan; sidmarkören "# N" kan stå ensam eller inleda ett stycke."""
    ut: list[tuple[str, list[str]]] = []
    for stycke in stycken:
        m = re.match(r"#\s*(\d+)\s*", stycke)
        if m:
            ut.append((m.group(1), []))
            stycke = stycke[m.end():]
        # Korpusens titelrad ("[Konungastyrelsen, Bureus utgåva]") hör inte till texten
        if not stycke or (not ut and stycke.startswith("[")):
            continue
        if not ut:
            ut.append(("", []))
        ut[-1][1].append(stycke)
    return [(s, ("\n" if vers else "\n").join(rader)) for s, rader in ut if rader]


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="fornsvenska_kronikor", namn="Fornsvenska textbankens material: krönikor och Konungastyrelsen",
            utgivare="Språkbanken Text, Göteborgs universitet (efter Fornsvenska textbanken, Lunds universitet)",
            url="https://spraakbanken.gu.se/resurser/fsv-verser", licens="CC BY 4.0"),
        verk=[])
    for korpus in KORPUSAR:
        with bz2.open(hamta(korpus)) as fh:
            for _, el in ET.iterparse(fh, events=("end",)):
                if el.tag != "text":
                    continue
                titel_korpus, datum = el.get("title", "").strip(), el.get("date")
                konf = next((t for t in TEXTER if titel_korpus.startswith(t[0])), None)
                if konf is None:
                    el.clear()
                    continue
                stycken = [stycketext(p) for p in el.findall("paragraph")]
                el.clear()
                _, verk_id, titel, genre, (edtf, fran, till), beskrivning, vers = konf
                slug = verk_id.split(":", 1)[1]
                paket.verk.append(Verk(
                    id=verk_id, titel=titel, genre=genre, sprak=["fsv"], datering_edtf=edtf,
                    datering_fran=fran, datering_till=till, beskrivning=beskrivning,
                    extern_url=f"https://spraakbanken.gu.se/korp/?mode=old_swedish#?corpus={korpus}"))
                utgava_id = f"utgava:{slug}:fsv"
                paket.utgavor.append((verk_id, Utgava(
                    utgava_id, f"Fornsvenska textbanken (Lunds universitet), i Språkbankens korpus "
                               f"{korpus}: {titel_korpus}.", "CC BY 4.0")))
                h_edtf, h_fran, h_till = _datering(datum)
                if h_edtf:
                    paket.vittnen.append((verk_id, Vittne(
                        f"vittne:{slug}", "handskrift" if "Bureus" not in titel_korpus else "tryck",
                        titel_korpus, datering_edtf=h_edtf, datering_fran=h_fran, datering_till=h_till)))
                n = 0
                for ordning, (sida, text) in enumerate(sidor(stycken, vers), 1):
                    pid = f"{slug}:s{sida}" if sida else f"{slug}:inledning"
                    paket.passager.append((verk_id, Passage(
                        id=pid, typ="originaltext", adress=f"s. {sida}" if sida else "inledning",
                        sprak="fsv", text=text, ordning=ordning, utgava_id=utgava_id)))
                    n += 1
                log.info("%-50s %4d sidor, %7d tecken", titel, n, sum(map(len, stycken)))
    for fil in sorted(OVERSATTNINGAR.glob("*.json")):
        paket.lagg_till_maskinoversattningar(fil, "fornsvenskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

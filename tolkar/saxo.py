"""
Tolk för Saxo Grammaticus, Gesta Danorum: den latinska texten ur latinska
Wikisource (efter Det Kongelige Biblioteks e-text) och Frederik Winkel Horns
danska översättning (Danmarks Krønike, 1898) ur heimskringla.no.

Den latinska texten delas per bok och kapitel; paragrafnumren står kvar i
hakparentes ("9.4 [12]"). Winkel Horns översättning delas i hans avsnitt
("Ragnar Lodbrog"), som inte sammanfaller med kapitlen. Någon fri svensk
översättning finns inte.

Användning:
    python -m tolkar.saxo
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
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda
from tolkar.heimskringla_no import hamta_wikitext, rensa_wiki, sidlank

log = logging.getLogger("tolkar.saxo")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "saxo"
LA_API = "https://la.wikisource.org/w/api.php"
USER_AGENT = "fornmed-forskningsdatabas/0.1 (öppen forskningsdatabas över medeltida källor)"
VERK_ID = "verk:saxo_gesta_danorum"
UTG_LAT = "utgava:saxo:kb_latin"
UTG_DAN = "utgava:saxo:winkel_horn1898"
BOCKER = ["Praefatio"] + [f"Liber {r}" for r in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI",
                                                  "XII", "XIII", "XIV", "XV", "XVI")]
DANSKA_BOCKER = ["Første", "Anden", "Tredie", "Fjerde", "Femte", "Sjette", "Syvende", "Ottende", "Niende",
                 "Tiende", "Ellevte", "Tolvte", "Trettende", "Fjortende", "Femtende", "Sekstende"]


def _latin(sida: str) -> str:
    fil = KATALOG / f"{re.sub(r'[^A-Za-z]+', '_', sida)}.json"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        url = LA_API + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": f"Gesta Danorum/{sida}", "prop": "wikitext", "format": "json",
             "formatversion": 2})
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
                                    timeout=60) as svar:
            fil.write_bytes(svar.read())
        time.sleep(1.5)
    return json.loads(fil.read_text(encoding="utf-8"))["parse"]["wikitext"]


def latinska_kapitel() -> list[tuple[int, int | None, str]]:
    """(bok, kapitel, text); förordet är bok 0 utan kapitel."""
    ut = []
    for bok, sida in enumerate(BOCKER):
        text = _latin(sida)
        text = re.sub(r"\{\{[^{}]*\}\}", "", re.sub(r"\{\{[^{}]*\}\}", "", text))
        text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.S)
        delar = re.split(r"(?m)^===\s*(\d+)\s*===\s*$", text)
        if len(delar) == 1:
            ut.append((bok, None, rensa_wiki(text.replace("'''Praefatio'''", ""))))
            continue
        for kap, stycke in zip(delar[1::2], delar[2::2]):
            ut.append((bok, int(kap), rensa_wiki(stycke)))
    return ut


def danska_avsnitt() -> list[tuple[int, str, str, str]]:
    """(bok, avsnittets namn, text, sida) i Winkel Horns översättning, i innehållsförteckningens ordning."""
    index, _ = hamta_wikitext("Danmarks krønike")
    ut, bok = [], 0
    for rad in index.split("\n"):
        if m := re.search(r"'''(\w+) Bog'''", rad):
            bok = DANSKA_BOCKER.index(m.group(1)) + 1 if m.group(1) in DANSKA_BOCKER else bok
        elif m := re.match(r"\*\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", rad.strip()):
            sida, namn = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
            if sida.startswith("Oversætterens"):
                # Översättarens förord är inte en del av Saxos text
                continue
            if sida.startswith("Saxos Fortale"):
                bok_nr = 0
            elif bok == 0:
                continue
            else:
                bok_nr = bok
            text, _ = hamta_wikitext(sida)
            if "Velg språk" in text:
                text = text[text.find("|}", text.find("Velg språk")) + 2:]
            text = re.sub(r"<center>.*?</center>", "", text, flags=re.S)
            text = re.sub(r"\[\[(?:Fil|Bilde|File|Kategori):[^\]]*\]\]", "", text)
            text = html.unescape(rensa_wiki(re.sub(r"<br\s*/?>", "\n", text))).replace("]]", "")
            if len(text) > 100:
                ut.append((bok_nr, namn, text, sida))
    return ut


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="saxo", namn="Saxo Grammaticus, Gesta Danorum (latin; Winkel Horns danska översättning)",
            utgivare="Wikisource (latin); heimskringla.no (danska)",
            url="https://la.wikisource.org/wiki/Gesta_Danorum",
            licens="Public domain; transkriptionerna CC BY-SA 4.0", version="2026-10"),
        verk=[Verk(id=VERK_ID, titel="Gesta Danorum", upphov="Saxo Grammaticus", genre="kronika", sprak=["lat"],
                   datering_edtf="1185/1216", datering_fran=11850101, datering_till=12161231,
                   beskrivning="Danmarks historia i 16 böcker från sagotiden till 1185, skriven på latin på "
                               "uppdrag av ärkebiskop Absalon. Böckerna 1–9 bygger på sagor och kväden och är "
                               "legendariska; böckerna 10–16 skildrar tiden från Harald Blåtand.",
                   extern_url="https://la.wikisource.org/wiki/Gesta_Danorum")],
        utgavor=[(VERK_ID, Utgava(UTG_LAT, "Saxo Grammaticus, Gesta Danorum, latinsk text på latinska Wikisource "
                                           "efter Det Kongelige Biblioteks e-text; bok- och kapitelindelning efter "
                                           "den utgåvan.", "Public domain; transkription CC BY-SA 4.0")),
                 (VERK_ID, Utgava(UTG_DAN, "Fr. Winkel Horn (övers.), Saxo Grammaticus: Danmarks Krønike, "
                                           "København 1898, heimskringla.no.", "Public domain"))])
    for ordning, (bok, kap, text) in enumerate(latinska_kapitel(), start=1):
        adress = "förord" if bok == 0 else f"bok {bok}" + (f", kap. {kap}" if kap else "")
        pid = f"saxo:{bok}" + (f".{kap}" if kap else "") + ":lat"
        # Kapitelrubrikerna på latinska Wikisource är ankare (#4)
        url = "https://la.wikisource.org/wiki/Gesta_Danorum/" + BOCKER[bok].replace(" ", "_") + (f"#{kap}" if kap else "")
        paket.passager.append((VERK_ID, Passage(id=pid, typ="originaltext", adress=adress, sprak="lat", text=text,
                                                ordning=ordning, utgava_id=UTG_LAT, url=url)))
    sett: dict[str, int] = {}
    for ordning, (bok, namn, text, sida) in enumerate(danska_avsnitt(), start=1):
        slug = re.sub(r"[^a-z0-9]+", "_", namn.lower().replace("ø", "o").replace("æ", "ae").replace("å", "a"))
        sett[slug] = sett.get(slug, 0) + 1
        pid = f"saxo:dan:{bok}:{slug}" + (f"_{sett[slug]}" if sett[slug] > 1 else "")
        adress = (f"bok {bok}: " if bok else "") + f"{namn} (Winkel Horn 1898)"
        paket.passager.append((VERK_ID, Passage(id=pid, typ="oversattning", adress=adress, sprak="dan", text=text,
                                                ordning=10000 + ordning, utgava_id=UTG_DAN, url=sidlank(sida))))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    lat = [p for _, p in paket.passager if p.sprak == "lat"]
    dan = [p for _, p in paket.passager if p.sprak == "dan"]
    log.info("%d latinska kapitel (%d tecken), %d danska avsnitt (%d tecken)", len(lat),
             sum(len(p.text) for p in lat), len(dan), sum(len(p.text) for p in dan))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

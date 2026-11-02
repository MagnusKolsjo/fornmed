"""
Tolk för Snorres Heimskringla ur heimskringla.no.

- Fornvästnordisk text: N. Linder & H. A. Haggson, Heimskringla, Uppsala
  1869–72 (normaliserad stavning).
- Svensk översättning: Emil Olson, Norges konungasagor, Lund 1919–26.

Båda är fria (public domain). heimskringla.no ber att sajten anges som
källa. Varje saga blir ett verk med passager per kapitel. Kapitlen står
som fetstilta nummer i wikitexten; Olsons sakupplysande noter (<ref>) tas
inte med. Utgåvorna numrerar kapitlen var för sig, så original och
översättning paras inte ihop rad för rad.

Användning:
    python -m tolkar.heimskringla_no
    python -m tolkar.heimskringla_no --torr
"""

import argparse
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

log = logging.getLogger("tolkar.heimskringla_no")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "heimskringla"
API = "https://heimskringla.no/api.php"
USER_AGENT = "fornmed-forskningsdatabas/0.1 (öppen forskningsdatabas över medeltida källor)"
INNEHALL = "Heimskringla"

UTG_ON = "utgava:heimskringla:linder-haggson"
UTG_SV = "utgava:heimskringla:olson"

# Sagor vars verk redan finns i databasen behåller sitt id
KANDA_ID = {"Ynglinga saga": "verk:ynglinga_saga"}


def _slug(titel: str) -> str:
    t = titel.lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ý", "y"), ("ð", "d"),
                 ("þ", "th"), ("æ", "ae"), ("œ", "oe"), ("ö", "o"), ("ø", "o"), ("ǫ", "o")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def hamta_wikitext(sida: str) -> str:
    """Sidans wikitext via MediaWiki-API:t, cachad i data/raw/heimskringla/."""
    fil = KATALOG / f"{_slug(sida)}.json"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        url = API + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": sida, "prop": "wikitext|links", "format": "json", "formatversion": 2})
        log.info("Hämtar %s", sida)
        # Servern svarar ibland 500 vid tät trafik; några omförsök med paus räcker
        for forsok in range(12):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
                                            timeout=60) as svar:
                    innehall = svar.read()
                # Ett felsvar sparas inte, så att nästa körning försöker igen
                if b'"parse"' not in innehall[:200] and b'"missingtitle"' not in innehall:
                    raise urllib.error.HTTPError(url, 503, "ofullständigt svar", None, None)
                fil.write_bytes(innehall)
                break
            except urllib.error.HTTPError:
                if forsok == 11:
                    raise
                time.sleep(min(5 * (forsok + 1), 40))
        time.sleep(1.5)
    data = json.loads(fil.read_text(encoding="utf-8"))
    if "parse" not in data:
        raise RuntimeError(f"Sidan '{sida}' finns inte på heimskringla.no")
    return data["parse"]["wikitext"], [l["title"] for l in data["parse"].get("links", [])]


def sidlank(sida: str) -> str:
    """Sidans adress på heimskringla.no."""
    return "https://heimskringla.no/wiki/" + urllib.parse.quote(sida.replace(" ", "_"))


def svensk_sida(wikitext: str) -> str | None:
    """Den svenska översättningens sidnamn ur sidans språktabell (första svenska länken)."""
    m = re.search(r"Svensk\.gif\|32px\|link=([^\]]+)\]\]", wikitext)
    return m.group(1).strip() if m else None


def rensa_wiki(text: str) -> str:
    text = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"[ \t]+", " ", text)
    # Versrader är indragna med kolon i wikitexten ('::Än jag sporde,'); de blir
    # indragna med ett blanksteg, som i Linder & Haggsons text
    text = re.sub(r"(?m)^:+[ \t]*", " ", text)
    return re.sub(r"\n(?:[ \t]*\n)+", "\n", text).strip()


def kapitel(wikitext: str) -> list[tuple[int, str, str]]:
    """(nummer, rubrik, text) per kapitel; kapitlen inleds med ett fetstilt nummer."""
    # Språktabellen överst hör inte till texten
    if "Velg språk" in wikitext:
        wikitext = wikitext[wikitext.find("|}", wikitext.find("Velg språk")) + 2:]
    # Kapitelraden börjar med ett fetstilt nummer; formen varierar mellan
    # sidorna ('''1.''' ''Rubrik'', ''' 1. ''', '''51. Rubrik</center> utan
    # avslutande fetstil), så resten av raden tas som rubrik
    traffar = list(re.finditer(r"(?m)^(?:<center>)?'''\s*(\d+)\.(.*)$", wikitext))
    ut, forra = [], 0
    for i, m in enumerate(traffar):
        nr = int(m.group(1))
        # Bara stigande nummer; fetstilta tal i texten (årtal, strofnummer) hoppas över
        if nr != forra + 1:
            continue
        slut = next((t.start() for t in traffar[i + 1:] if int(t.group(1)) == nr + 1), len(wikitext))
        rubrik = rensa_wiki(m.group(2)).strip(" .")
        ut.append((nr, rubrik, rensa_wiki(wikitext[m.end():slut])))
        forra = nr
    return ut


def sagor() -> list[str]:
    """Sagornas sidnamn i Heimskringlas innehållsförteckning."""
    _, lankar = hamta_wikitext(INNEHALL)
    return [l for l in lankar if l.startswith(("Ynglinga saga", "Saga", "Sagan", "Haralds saga",
                                                "Prologus"))
            and "(" not in l]


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="heimskringla_no", namn="heimskringla.no: Heimskringla (Linder & Haggson; Olson)",
            utgivare="heimskringla.no", url="https://heimskringla.no/wiki/Heimskringla",
            licens="Public domain (enligt heimskringla.no; sajten anges som källa)", version="2026-10"),
        verk=[],
        utgavor=[],
    )
    for sida in sagor():
        on_text, _ = hamta_wikitext(sida)
        on_kap = kapitel(on_text)
        if not on_kap:
            log.warning("%s: inga kapitel hittades", sida)
            continue
        verk_id = KANDA_ID.get(sida, f"verk:heimskringla:{_slug(sida)}")
        paket.verk.append(Verk(
            id=verk_id, titel=sida, upphov="Snorri Sturluson", genre="saga", sprak=["non"],
            datering_edtf="1225/1235", datering_fran=12250101, datering_till=12351231,
            beskrivning=("Första sagan i Heimskringla; bygger uttalat på Ynglingatal."
                         if sida == "Ynglinga saga" else "Saga i Snorres Heimskringla."),
            extern_url=f"https://heimskringla.no/wiki/{urllib.parse.quote(sida.replace(' ', '_'))}"))
        on_utg, sv_utg = f"{UTG_ON}:{_slug(sida)}", f"{UTG_SV}:{_slug(sida)}"
        paket.utgavor.append((verk_id, Utgava(
            on_utg, f"N. Linder & H. A. Haggson (utg.), Heimskringla. Snorra Sturlusonar, Uppsala "
                    f"1869–72: {sida}. heimskringla.no.", "Public domain")))
        for nr, rubrik, text in on_kap:
            paket.passager.append((verk_id, Passage(
                id=f"{_slug(sida)}:non:{nr}", typ="originaltext", adress=f"kap. {nr}", sprak="non",
                text=(f"{nr}. {rubrik}\n" if rubrik else "") + text, ordning=nr, utgava_id=on_utg,
                url=sidlank(sida))))

        sv_sida = svensk_sida(on_text)
        if not sv_sida:
            log.warning("%s: ingen svensk översättning länkad", sida)
            continue
        sv_text, _ = hamta_wikitext(sv_sida)
        sv_kap = kapitel(sv_text)
        paket.utgavor.append((verk_id, Utgava(
            sv_utg, f"Emil Olson (övers.), Snorre Sturlasson: Norges konungasagor, Lund 1919–26: "
                    f"{sv_sida}. heimskringla.no.", "Public domain")))
        for nr, rubrik, text in sv_kap:
            paket.passager.append((verk_id, Passage(
                id=f"{_slug(sida)}:swe:{nr}", typ="oversattning", adress=f"kap. {nr}", sprak="swe",
                text=(f"{nr}. {rubrik}\n" if rubrik else "") + text, ordning=1000 + nr, utgava_id=sv_utg,
                url=sidlank(sv_sida))))
        log.info("%-48s %3d kap. original, %3d kap. svenska (%s)", sida, len(on_kap), len(sv_kap), sv_sida)
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

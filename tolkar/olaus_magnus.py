"""
Tolk för Olaus Magnus, Historia de gentibus septentrionalibus (Rom 1555),
ur Project Runebergs elektroniska utgåva (public domain).

Runeberg har sidbilder och OCR-text från Nasjonalbiblioteket i Norge,
delvis korrekturläst. Förteckningen på verkets startsida anger varje boks
och varje kapitels sidor; kapitlen börjar ofta mitt på en sida. Bokens
sidor slås därför ihop och delas vid kapitelrubrikerna ("CAP. V."), och
rubrikraden ovanför följer med till sitt kapitel. Passagens adress anger
bok, kapitel och tryckets sidor. Kapitel vars rubrikrad OCR:en tappat letas
upp med hjälp av kapitelrubrikerna i Runebergs förteckning.

Trycket har marginalanteckningar (stickord, källhänvisningar som
"Jordanes", "Paulus Diaconus"), som OCR:en lägger in i raderna. De är
Olaus egna och står kvar i texten.

Svenska översättningar gjorda av språkmodell ligger i data/oversattningar/olaus_magnus/
(se RIKTLINJER.md där) och laddas som egna utgåvor märkta som maskinöversättning.

Användning:
    python -m tolkar.olaus_magnus
    python -m tolkar.olaus_magnus --torr
"""

import argparse
import html
import logging
import re
import time
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "olaus_magnus"

log = logging.getLogger("tolkar.olaus_magnus")

BAS = "https://runeberg.org/olmagnus/"
KATALOG = Path(__file__).parent.parent / "data" / "raw" / "runeberg_olmagnus"
USER_AGENT = "fornmed-forskningsdatabas/0.1 (öppen forskningsdatabas över medeltida källor)"
VERK_ID = "verk:olaus_magnus"
UTGAVA_ID = "utgava:olaus_magnus:1555"
ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def romersk(tal: str) -> int:
    v = [ROMERSKA[c] for c in tal]
    return sum(-a if a < b else a for a, b in zip(v, v[1:] + [0]))


def hamta(namn: str) -> str:
    fil = KATALOG / namn
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        # Runeberg bryter ibland förbindelsen vid många anrop i följd; några omförsök med paus räcker
        for forsok in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(BAS + namn, headers={"User-Agent": USER_AGENT}),
                                            timeout=60) as svar:
                    fil.write_bytes(svar.read())
                break
            except OSError:
                if forsok == 5:
                    raise
                time.sleep(10 * (forsok + 1))
        time.sleep(1)
    return fil.read_text(encoding="utf-8", errors="replace")


def sidtext(fil: str) -> str:
    """En sidas OCR-text utan sidhuvud (sidnummer och löprubrik på första raden)."""
    sida = hamta(fil)
    m = re.search(r"<!-- mode=normal -->(.*?)<!-- NEWIMAGE2 -->", sida, re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "", m.group(1) if m else ""))
    rader = text.strip("\n").split("\n")
    # Första raden är sidhuvudet: "14        DE RITV GENT. SEPTEN." eller "LIBER PRIMVS.     15"
    if rader and re.search(r"^\s*\d+\s+\S|\S\s+\d+\s*$", rader[0]) and len(rader[0].strip()) < 70:
        rader = rader[1:]
    return "\n".join(rader)


def forteckning() -> list[tuple[str, str, list[tuple[str, str]], dict[int, str]]]:
    """(bok, boktitel, [(sidfil, sidnummer)], {kapitelnummer: rubrik}) per bok ur startsidans förteckning."""
    t = hamta("index.html")
    ut = []
    bocker = list(re.finditer(r'<b>(Liber [^<]+)</b>\s*([^<]*)</a>\s*-\s*((?:<a href="\d+\.html"\s*>\w+</a>,?\s*)+)', t))
    for i, m in enumerate(bocker):
        sidor = re.findall(r'<a href="(\d+\.html)"\s*>(\w+)</a>', m.group(3))
        avsnitt = t[m.end():bocker[i + 1].start() if i + 1 < len(bocker) else len(t)]
        rubriker = {}
        for nr, rub in re.findall(r">Cap\.\s*([IVXLC]+)\.\s*([^<]+)</a>", avsnitt):
            rubriker.setdefault(romersk(nr), html.unescape(rub).strip())
        ut.append((m.group(1).strip(" ."), m.group(2).strip(), sidor, rubriker))
    return ut


def _jamfor(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower().replace("v", "u").replace("j", "i"))


def fyll_luckor(text: str, kap: list[tuple[int, str, int, int]], rubriker: dict[int, str]) -> list[tuple[int, str, int, int]]:
    """
    Lägger in kapitel vars "CAP."-rad OCR:en tappat: kapitlets rubrik ur
    förteckningen söks som egen rad mellan grannkapitlen (de 20 första
    bokstäverna i jämförelseform).
    """
    funna = {nr for nr, *_ in kap}
    starter = [(nr, rub, start) for nr, rub, start, _ in kap]
    rader = [(m.start(), _jamfor(m.group(0))) for m in re.finditer(r"(?m)^.*$", text)]
    for nr, rubrik in sorted(rubriker.items()):
        if nr in funna:
            continue
        fore = max((s for n, _, s in starter if n < nr), default=0)
        efter = min((s for n, _, s in starter if n > nr), default=len(text))
        mal = _jamfor(rubrik)[:20]
        if len(mal) < 8:
            continue
        traff = next((pos for pos, rad in rader if fore < pos < efter and rad.startswith(mal)), None)
        if traff is not None:
            starter.append((nr, rubrik, traff))
    starter.sort(key=lambda x: x[2])
    return [(nr, rub, start, starter[i + 1][2] if i + 1 < len(starter) else len(text))
            for i, (nr, rub, start) in enumerate(starter)]


def kapitel(text: str) -> list[tuple[int, str, int, int]]:
    """(nummer, rubrik, start, slut); kapitlet börjar vid rubrikraden ovanför "CAP. N."."""
    # OCR:en tappar ibland punkten ("CAP XI") och läser I som l ("XlX"); första kapitlet heter "CAP. PRIMVM."
    traffar = list(re.finditer(r"(?m)^\s*CAP\.?\s*([IVXLCl]+|PRIMVM)\.?\s*$", text))
    starter = []
    forra = 0
    for m in traffar:
        nr = 1 if m.group(1) == "PRIMVM" else romersk(m.group(1).replace("l", "I"))
        if nr <= forra:
            continue
        # Rubriken är närmaste icke-tomma rad ovanför
        fore = text[:m.start()].rstrip("\n")
        rad_start = fore.rfind("\n") + 1
        rubrik = fore[rad_start:].strip()
        starter.append((nr, rubrik, rad_start, m.end()))
        forra = nr
    return [(nr, rub, start, starter[i + 1][2] if i + 1 < len(starter) else len(text))
            for i, (nr, rub, start, _) in enumerate(starter)]


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(id="runeberg_olmagnus", namn="Project Runeberg: Olaus Magnus, Historia de gentibus "
                                "septentrionalibus (1555)", utgivare="Project Runeberg; Nasjonalbiblioteket",
                                url=BAS, licens="Public domain"),
        verk=[Verk(
            id=VERK_ID, titel="Historia de gentibus septentrionalibus", upphov="Olaus Magnus", genre="geografi",
            sprak=["lat"], datering_edtf="1555", datering_fran=15550101, datering_till=15551231,
            beskrivning="Olaus Magnus beskrivning av de nordiska folken, deras seder, näringar, krig och natur, "
                        "i 22 böcker; bl.a. om samerna (Scricfinni), birkarlarna, Finnmarken och Bjarmaland.",
            extern_url=BAS)],
        utgavor=[(VERK_ID, Utgava(UTGAVA_ID, "Olaus Magnus, Historia de gentibus septentrionalibus, Rom 1555 "
                                  "(Project Runeberg efter Nasjonalbibliotekets skanning och OCR).",
                                  "Public domain"))])
    ordning = 0
    for bok, boktitel, sidor, rubriker in forteckning():
        boknr = bok.split()[-1] if bok.split()[-1].isupper() else bok
        # Bokens sidor i ordning; samma sida kan förekomma två gånger i förteckningen
        filer = list(dict.fromkeys(f for f, _ in sidor))
        sidnr = {f: n for f, n in sidor}
        delar, positioner = [], []
        pos = 0
        for f in filer:
            t = sidtext(f) + "\n"
            positioner.append((pos, sidnr[f]))
            delar.append(t)
            pos += len(t)
        text = "".join(delar)

        def sida_vid(p: int) -> str:
            return [n for start, n in positioner if start <= p][-1]

        kap = fyll_luckor(text, kapitel(text), rubriker)
        inledning = text[:kap[0][2]] if kap else text
        stycken = ([(0, "inledning", 0, kap[0][2])] if kap and len(inledning.strip()) > 40 else []) + kap
        if not kap:
            stycken = [(0, "inledning", 0, len(text))]
        for nr, rubrik, start, slut in stycken:
            innehall = re.sub(r"[ \t]{2,}", "  ", text[start:slut]).strip()
            if not innehall:
                continue
            ordning += 1
            s1, s2 = sida_vid(start), sida_vid(max(start, slut - 1))
            sidor_txt = f"s. {s1}" + (f"–{s2}" if s2 != s1 else "")
            del_id = re.sub(r"[^a-z0-9]+", "_", bok.lower()).strip("_")
            pid = f"olaus_magnus:{del_id}:{nr if nr else 'inledning'}"
            adress = f"{bok}" + (f", kap. {nr}" if nr else ", inledning") + f" ({sidor_txt})"
            paket.passager.append((VERK_ID, Passage(
                id=pid, typ="originaltext", adress=adress, sprak="lat", text=innehall, ordning=ordning,
                utgava_id=UTGAVA_ID, url=BAS + [f for f in filer if sidnr[f] == s1][0])))
        log.info("%-14s %3d kapitel (%s)", bok, len(kap), boktitel[:50])
    for fil in sorted(OVERSATTNINGAR.glob("*.json")):
        paket.lagg_till_maskinoversattningar(fil, "latinet")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    log.info("%d passager, %d tecken", len(paket.passager), sum(len(p.text) for _, p in paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

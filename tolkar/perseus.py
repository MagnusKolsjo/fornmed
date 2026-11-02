"""
Läsare för Perseus Digital Librarys TEI-filer (canonical-latinLit och
canonical-greekLit på GitHub, CC BY-SA 4.0).

Texten lämnas per textdel (bok, kapitel …) som löptext. Utgivarens noter,
som i Mayhoffs Plinius innehåller hela den textkritiska apparaten, tas bort;
paragrafnummer (milestone unit="section") behålls i hakparentes, så att
avsnitt kan citeras med paragraf ("4.96").
"""

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "perseus"
REPO = {"lat": "https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/master/data",
        "grc": "https://raw.githubusercontent.com/PerseusDL/canonical-greekLit/master/data"}
# Äldre filer är TEI P4 utan namnrymd och med div1, div2 …; taggarna jämförs utan namnrymd
DELAR = {"div", "div1", "div2", "div3", "div4"}


def _tagg(el) -> str:
    return el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""


def hamta(urn: str) -> Path:
    """Fil efter CTS-urn utan prefix, t.ex. 'phi1351.phi002.perseus-lat2'."""
    fil = KATALOG / f"{urn}.xml"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        forfattare, verk, _ = urn.split(".", 2)
        repo = REPO["grc" if forfattare.startswith("tlg") else "lat"]
        urllib.request.urlretrieve(f"{repo}/{forfattare}/{verk}/{urn}.xml", fil)
    return fil


def _text(el) -> str:
    """Elementets text utan noter; paragrafnummer som [96]."""
    delar = [el.text or ""]
    for barn in el:
        if _tagg(barn) == "milestone" and barn.get("unit") == "section":
            delar.append(f" [{barn.get('n')}] ")
        elif _tagg(barn) not in ("note", "bibl", "head"):
            delar.append(_text(barn))
        delar.append(barn.tail or "")
    return "".join(delar)


def las(urn: str) -> list[tuple[tuple[str, ...], str]]:
    """((bok, kapitel, …), text) för varje textdel som inte delas vidare."""
    xml = hamta(urn).read_text(encoding="utf-8")
    # Engelska översättningar använder HTML-entiteter som XML-tolken inte känner
    xml = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)\w+;", lambda m: html.unescape(m.group(0)), xml)
    # Dokumenttypen hänvisar till Perseus DTD:er som inte behövs för texten
    xml = re.sub(r"<!DOCTYPE.*?\]>", "", xml, count=1, flags=re.S)
    rot = ET.fromstring(xml)
    ut: list[tuple[tuple[str, ...], str]] = []

    def ga(el, vag):
        delar = [d for d in el if _tagg(d) in DELAR]
        if not delar:
            if vag:
                ut.append((tuple(vag), re.sub(r"\s+", " ", _text(el)).strip()))
            return
        for d in delar:
            # Utgåvans div bär urn:en som n; den ingår inte i adressen
            n = d.get("n")
            ga(d, vag + [n] if n and not n.startswith("urn:") else vag)

    ga(next(e for e in rot.iter() if _tagg(e) == "body"), [])
    return ut


def paragrafer(text: str) -> dict[str, str]:
    """Texten uppdelad på paragrafnummer: {'96': 'Incipit deinde …'}."""
    delar = re.split(r"\s*\[(\d+[a-z]?)\]\s*", text)
    return {nr: stycke.strip() for nr, stycke in zip(delar[1::2], delar[2::2])}

"""
Importerar Diplomatarium Norvegicum (band 1–23) ur Nasjonalbibliotekets korpus till databasen.

Källan är `data/raw/dn/MIDLAT_XML.zip` (https://www.nb.no/sbfil/tekst/MIDLAT_XML.zip) med
ett TEI-dokument per band. Varje brev ger ett verk `dn:{band}:{nr}` med regest (på danska
eller norska), proveniens som vittne, datering, ort och brevtext. Brevtextens språk kommer
från sprakklassning.py (data/sprak/dn_sprak.tsv), som körs efter en första import. Där
klassaren är osäker gäller språkmodellens svar (data/sprak/dn_sprak_modell.tsv, sprak_samla.py)
när två av tre bedömningar är överens (kolumnen beslut). SDHK-brev som hänvisar
till samma band och nummer och har samma datum får DN-numret i verkets extra-fält.
Importen kan köras om.

Användning:
    python importera_dn.py
"""

import csv
import json
import logging
import re
import unicodedata
import urllib.parse
import zipfile
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import db
from importera_df import samma_datum
from importera_sdhk import tolka_datum

log = logging.getLogger("importera_dn")

ARKIV = Path(__file__).parent / "data" / "raw" / "dn" / "MIDLAT_XML.zip"
KALLA_URL = "https://www.nb.no/forskning/medieval-latin/corpus/"
# Dokumentasjonsprosjektets söktjänst visar brevet utifrån band och nummer
BREVLANK = "https://www.dokpro.uio.no/cgi-bin/middelalder/diplom_soek.cgi?s=n&BIND={band}&NR={nr}&start=S%C3%B8k"
BREV = re.compile(r'<div type="document" xml:id="DN(\d+)_([^"]+)"[^>]*>(.*?)(?=<div type="document"|</body>)', re.S)
MANADER = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "maj": 5, "jun": 6, "jul": 7,
           "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dec": 12, "des": 12}
ROMERSKA = {"I": 1, "V": 5, "X": 10, "L": 50}
HANVISNING = re.compile(r"(?:DN|Dipl\.?\s*Norv\.?)\s*([IVXL]+|\d+)\s*[:,]?\s*(?:nr\.?\s*)?(\d+)")
# Brevtextens språk enligt sprakklassning.py; bara säkra bedömningar blir brevets språk
SPRAKFIL = Path(__file__).parent / "data" / "sprak" / "dn_sprak.tsv"
SAKER = 0.8
MODELLFIL = Path(__file__).parent / "data" / "sprak" / "dn_sprak_modell.tsv"


# Korpusens teckenkoder: /th/ för þ, /edd/ för ð, /´a/ för á, /,o/ för ǫ och så vidare
KODER = {"th": "þ", "Th": "Þ", "TH": "Þ", "edd": "ð", "Edd": "Ð", "oe": "ø", "Oe": "Ø", "OE": "Ø",
         "aa": "ꜳ", "AA": "Ꜳ", "kors": "✠"}
ÖVERSKRIVNA = {"a": "\u0363", "e": "\u0364", "i": "\u0365", "o": "\u0366", "u": "\u0367"}
DIAKRITER = {"´": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303", ")": "\u0306"}
# Kursiv markerar upplösta förkortningar mitt i ord, så de taggarna får inte bli mellanrum
INLINE = re.compile(r"</?(?:hi|ref|rs|add|seg|sic|quote)\b[^>]*>")


def tecken(text: str) -> str:
    """Ersätter korpusens teckenkoder med Unicode."""
    text = re.sub(r"/(%s)/" % "|".join(sorted(KODER, key=len, reverse=True)), lambda m: KODER[m[1]], text)
    text = re.sub(r"/([´`^~)])(\w)/", lambda m: m[2] + DIAKRITER[m[1]], text)
    # Komma under: cedilj under c, annars ogonek (ę, ǫ)
    text = re.sub(r"/,(\w)/", lambda m: m[1] + ("\u0327" if m[1] in "cC" else "\u0328"), text)
    # Bokstav över bokstav: /o+e/ är o med litet e ovanför
    text = re.sub(r"/(\w)\+([aeiou])/", lambda m: m[1] + ÖVERSKRIVNA[m[2]], text)
    # Tillägg ovan raden (/l-/…/-l/) och liknande markeringar behåller bara texten
    text = re.sub(r"/[l1!]-/(.*?)/-[l1!]/", r"\1", text)
    text = re.sub(r"/l-(\w)-l/", r"\1", text)
    text = re.sub(r"/[l1]-/", "", text)
    text = re.sub(r"/-(\w+)/", r"\1", text)
    text = re.sub(r"/([\w-]{1,10}|\+)/", r"\1", text)
    return unicodedata.normalize("NFC", text)


def _text(fragment: str) -> str:
    utan = re.sub(r"<pb[^>]*/>|<note.*?</note>|<corr>.*?</corr>", " ", fragment, flags=re.S)
    utan = re.sub(r"<[^>]+>", " ", INLINE.sub("", utan))
    return re.sub(r"\s+", " ", tecken(unescape(utan))).replace(" .", ".").strip()


def _div(brev: str, typ: str) -> str:
    traff = re.search(rf'<div type="{typ}"\s*>(.*?)</div>', brev, re.S)
    return _text(traff.group(1)) if traff else ""


def _romersk(tal: str) -> int:
    if tal.isdigit():
        return int(tal)
    varden = [ROMERSKA[t] for t in tal]
    return sum(-v if i + 1 < len(varden) and v < varden[i + 1] else v for i, v in enumerate(varden))


def datum(text: str) -> tuple:
    """Dateringen som SDHK:s form, ur t.ex. "9 Decbr. 1247", "Uden Dag 1290", "153*" och "Midten av 16. h.å."."""
    ren = re.sub(r"[\[\]?]", "", text)
    ren = re.sub(r"\((1[0-7])\)(\d\d)", r"\1\2", ren)          # "(15)49": utgivaren har fyllt i seklet
    ren = re.sub(r"\b(1[0-7]\d)O\b|\b(1[0-7])O(\d)\b", lambda m: (m[1] + "0") if m[1] else (m[2] + "0" + m[3]), ren)
    osaker = "?" in text or "[" in text
    # Ett ofullständigt årtal ("148..", "153*") är ett årtionde
    if (dec := re.search(r"\b(1[0-7]\d)(?:\*|\.\.)", ren)) and not re.search(r"\b1[0-7]\d\d\b", ren):
        fran = tolka_datum(f"{dec[1]}00000")[1]
        till = tolka_datum(f"{dec[1]}90000")[2]
        return f"{dec[1]}X" + ("?" if osaker else ""), fran, till, text
    if (sek := re.search(r"\b(1[0-7])\.\.", ren)) and not re.search(r"\b1[0-7]\d", ren.replace(sek[0], "")):
        fran, till = tolka_datum(f"{sek[1]}000000")[1], tolka_datum(f"{sek[1]}990000")[2]
        return f"{sek[1]}XX" + ("?" if osaker else ""), fran, till, text
    # Århundrade: "15. h.å.", "Midten av 16. h. å.", "Slutten av 15 h.å."
    if (sek := re.search(r"\b(1[0-6])\.?\s*h\.\s*å", ren)):
        start = (int(sek[1]) - 1) * 100
        del_ = re.search(r"(Begynnelsen|Midten|Slutten|andre halvdel|første halvdel)", ren, re.I)
        bit = {"begynnelsen": (0, 25), "midten": (25, 75), "slutten": (75, 99), "andre halvdel": (50, 99),
               "første halvdel": (0, 49)}.get(del_[1].lower() if del_ else "", (0, 99))
        fran, till = tolka_datum(f"{start + bit[0]}0000")[1], tolka_datum(f"{start + bit[1]}0000")[2]
        return f"{start + bit[0]}/{start + bit[1]}" + ("?" if osaker else ""), fran, till, text
    ar = [a for a in re.findall(r"\b(\d{3,4})\b", ren) if 800 <= int(a) <= 1799]
    if not ar:
        return None, None, None, text or None
    ar = [a.zfill(4) for a in ar]
    traff = re.search(r"\b(\d{1,2})\.?\s+([A-Za-zæøå]{3})[a-zæøå]*\.?\s+\d{3,4}", ren)
    manad = re.search(r"\b([A-Za-zæøå]{3})[a-zæøå]*\.?\s+\d{3,4}", ren)
    if traff and traff[2].lower() in MANADER:
        form = f"{ar[0]}{MANADER[traff[2].lower()]:02}{int(traff[1]):02}"
    elif manad and manad[1].lower() in MANADER:
        form = f"{ar[0]}{MANADER[manad[1].lower()]:02}00"
    else:
        form = f"{ar[0]}0000"
    edtf, fran, till, _ = tolka_datum(form)
    if len(set(ar)) > 1:
        till = tolka_datum(f"{ar[-1]}0000")[2]
        edtf = f"{ar[0]}/{ar[-1]}"
    return (edtf + "?" if osaker and edtf else edtf), fran, till, text if osaker or len(set(ar)) > 1 else None


def _sidor(sidbrytningar: list[tuple[int, str]], start: int, slut: int) -> list[str]:
    """Sidorna ett brev står på: sidan före brevets början och sidbrytningarna inom det."""
    fore = [n for p, n in sidbrytningar if p < start]
    inom = [n for p, n in sidbrytningar if start <= p < slut]
    return list(dict.fromkeys(fore[-1:] + inom))


def _sidnummer(text: str) -> list[str]:
    """Sidhänvisningar som "77-79. 83. 109 f." till enskilda sidor."""
    sidor = []
    for a, b in re.findall(r"(\d+)(?:\s*-\s*(\d+))?", text):
        sidor += [str(x) for x in range(int(a), int(b) + 1)] if b and 0 <= int(b) - int(a) <= 20 else [a]
    return sidor


def las_sprak(sprakfil: Path = SPRAKFIL, modellfil: Path = MODELLFIL) -> dict[str, dict]:
    """Klassarens bedömning per brev: språket när den är säker, och alltid andelarna."""
    if not sprakfil.exists():
        return {}
    bedomningar = {}
    with sprakfil.open(encoding="utf-8", newline="") as f:
        for rad in csv.DictReader(f, delimiter="\t"):
            andelar = {k: float(v) for k, v in (x.split(":") for x in rad["andelar"].split())}
            saker = bool(rad["sprak"]) and float(rad["sakerhet"]) >= SAKER and andelar.get(rad["sprak"], 0) >= SAKER
            bedomningar[rad["verk_id"]] = {"sprak": rad["sprak"] if saker else None, "andelar": andelar,
                                           "sakerhet": float(rad["sakerhet"]), "metod": "sprakklassning.py"}
    # Där klassaren är osäker gäller språkmodellens svar om det är klassarens huvudspråk
    if modellfil.exists():
        with modellfil.open(encoding="utf-8", newline="") as f:
            for rad in csv.DictReader(f, delimiter="\t"):
                b = bedomningar.get(rad["verk_id"])
                if not b:
                    continue
                b["sprakmodell"] = {k: rad[k] for k in ("sprak", "sakerhet", "overens", "motivering", "sprak2", "motivering2")}
                if b["sprak"] is None and rad["beslut"]:
                    b["sprak"] = rad["beslut"]
                    b["metod"] = ("sprakklassning.py och språkmodell, överens" if rad["overens"] == "huvud"
                                  else "två av tre bedömningar överens (klassare och två språkmodeller)")
    return bedomningar


def _sdhk_per_dn() -> dict[tuple[int, int], list[tuple[int, int | None]]]:
    p = db._prefix()
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(f"""SELECT b.sdhk_nr, b.tryck, v.datering_fran FROM {p}sdhk_brev b
                        JOIN {p}verk v ON v.id = 'sdhk:' || b.sdhk_nr
                        WHERE b.tryck LIKE '%DN%' OR b.tryck LIKE '%Norv%'""")
        per_dn: dict[tuple[int, int], list] = {}
        for nr, tryck, fran in cur.fetchall():
            for band, dn in HANVISNING.findall(tryck):
                per_dn.setdefault((_romersk(band), int(dn)), []).append((nr, fran))
        return per_dn
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db.initiera_schema()
    per_dn = _sdhk_per_dn()
    sprakbedomningar = las_sprak()
    verk, passager, vittnen, kopplade = [], [], [], 0
    with zipfile.ZipFile(ARKIV) as z:
        filer = [n for n in z.namelist() if "DiplomatariumNorvegicum" in n and n.endswith(".xml")]
        for fil in sorted(filer, key=lambda n: int(re.search(r"bind(\d+)", n)[1])):
            band_text = z.read(fil).decode("utf-8")
            urn = re.search(r'target="(https://urn\.nb\.no/[^"]+)"', band_text)
            utgivet = re.search(r'<date when="(\d{4})"', band_text)
            utgivare = re.findall(r"<editor>([^<]+)</editor>", band_text)
            # Sidbrytningen anger sidan först, ibland följd av årtal: <pb n="1 aar1247-1248"/>
            sidbrytningar = [(m.start(), m[1]) for m in re.finditer(r'<pb n="([0-9IVXLCivxlc]+)\b[^"]*"', band_text)]
            brev_per_sida: dict[str, list[str]] = {}
            for traff in BREV.finditer(band_text):
                band, nr, brev = traff.groups()
                band = int(band)
                sidor = _sidor(sidbrytningar, traff.start(), traff.end())
                for sida in sidor:
                    brev_per_sida.setdefault(sida, []).append(f"dn:{band}:{nr}")
                verk_id = f"dn:{band}:{nr}"
                rad = re.search(r"<dateline>(.*?)</dateline>", brev, re.S)
                dateline = rad.group(1) if rad else ""
                datum_text = _text(re.search(r"<date>(.*?)</date>", dateline, re.S).group(1)) if "<date>" in dateline else ""
                ort = re.search(r"<placeName>(.*?)</placeName>", dateline, re.S)
                ort = re.sub(r"[\[\]]", "", _text(ort.group(1))).strip(" .?") if ort else None
                edtf, fran, till, anm = datum(datum_text)
                texten = " ".join(_text(t) for t in re.findall(r'<div type="text"\s*>(.*?)</div>', brev, re.S))
                bedomning = sprakbedomningar.get(verk_id)
                # Ett blandat språk ("dan-nor") ger verket båda språken men texten inget enskilt
                brevsprak_lista = bedomning["sprak"].split("-") if bedomning and bedomning["sprak"] else []
                brevsprak = brevsprak_lista[0] if len(brevsprak_lista) == 1 else None
                sdhk = [n for n, sdhk_fran in per_dn.get((band, int(re.match(r"\d+", nr)[0])), [])
                        if re.fullmatch(r"\d+", nr) and samma_datum(edtf, fran, sdhk_fran) == "saker"]
                kopplade += bool(sdhk)
                verk.append((verk_id, "dn", f"DN {band} nr {nr}", None, "diplom",
                             db.sprakvarde(brevsprak_lista), ort or None, edtf, fran, till, anm,
                             BREVLANK.format(band=band, nr=urllib.parse.quote(nr)),
                             json.dumps({"band": band, "nr": nr, "sidor": sidor, "band_url": urn.group(1) if urn else None,
                                         "utgivet": utgivet.group(1) if utgivet else None,
                                         "utgivare": utgivare, "sdhk": sdhk,
                                         "sprakbedomning": bedomning}, ensure_ascii=False)))
                if regest := _div(brev, "ingress"):
                    passager.append((f"{verk_id}:regest", verk_id, None, "regest", f"DN {band} nr {nr}", 0, "dan", regest))
                if texten:
                    passager.append((f"{verk_id}:originaltext", verk_id, None, "originaltext", f"DN {band} nr {nr}", 1,
                                     brevsprak, texten))
                if proveniens := _div(brev, "provenance"):
                    vittnen.append((f"{verk_id}:proveniens:0", verk_id, "proveniens", proveniens))
                adress = f"DN {band} nr {nr}"
                # Tillägg, påskrifter och tabellspalter hör till brevets text och söks som originaltext
                for typ, namn in (("tillegg", "tillagg"), ("accMat", "paskrift"), ("vkolonne", "spalt"), ("sted", "lista")):
                    for i, del_ in enumerate(re.findall(rf'<div type="{typ}"\s*>(.*?)</div>', brev, re.S)):
                        if (t := _text(del_)):
                            passager.append((f"{verk_id}:{namn}:{i}", verk_id, None, "originaltext", f"{adress}, {namn}", 2 + i, None, t))
                # Utgivarnas noter och rättelser; digitaliseringens egna anmärkningar tas inte med
                noter = [_text(n) for a, n in re.findall(r"<note([^>]*)>(.*?)</note>", brev, re.S) if "resp=" not in a]
                noter += [_text(r) for r in re.findall(r'<div type="rettelser"\s*>(.*?)</div>', brev, re.S)]
                if (noter := [n for n in noter if n]):
                    passager.append((f"{verk_id}:anmarkning", verk_id, None, "anmarkning", f"{adress}, noter", 20, "dan", " | ".join(noter)))
            # Namn- och sakregistren hänvisar till sidor; en post gäller breven på den sidan
            for typ, rubrik in (("navneregister", "Namnregistret"), ("sagregister", "Sakregistret")):
                per_brev: dict[str, list[str]] = {}
                for div in re.findall(rf'<div type="{typ}"\s*>(.*?)(?=<div type=|</body>)', band_text, re.S):
                    for post in re.findall(r"<p>(.*?)</p>", div, re.S):
                        post = _text(post)
                        # Namnet följs av sidhänvisningarna: "Aake, Kantsler. 77-79. 83."
                        if not (m := re.match(r"(.*?\D)[\s.,]+(\d[\d\s.,f-]*)$", post)):
                            continue
                        for sida in _sidnummer(m[2]):
                            for b in brev_per_sida.get(sida, []):
                                per_brev.setdefault(b, []).append(m[1].strip(" .,"))
                for b, namn in per_brev.items():
                    passager.append((f"{b}:{typ}", b, None, "register", f"{rubrik}, DN {b.split(':')[1]}", 30, "dan",
                                     f"{rubrik} (poster på brevets sidor): " + "; ".join(dict.fromkeys(namn))))
    conn = db._hamta_db()
    try:
        db.upsert(conn, "kallsamling", ["id", "namn", "utgivare", "url", "licens", "version", "importerad"], ["id"],
                  [("dn", "Diplomatarium Norvegicum", "Nasjonalbiblioteket; Dokumentasjonsprosjektet, Universitetet i Oslo",
                    KALLA_URL, "Inga förbehåll angivna vid materialet", "2020-02-26",
                    datetime.now(timezone.utc).isoformat(timespec="seconds"))])
        db.upsert(conn, "verk", ["id", "kallsamling_id", "titel", "upphov", "genre", "sprak", "utfardandeort", "datering_edtf",
                                 "datering_fran", "datering_till", "datering_anm", "extern_url", "extra"], ["id"], verk)
        db.upsert(conn, "passage", ["id", "verk_id", "utgava_id", "typ", "adress", "ordning", "sprak", "text"], ["id"], passager)
        db.upsert(conn, "vittne", ["id", "verk_id", "typ", "beskrivning"], ["id"], vittnen)
    finally:
        conn.close()
    log.info("%d brev, %d passager, %d vittnen, %d kopplade till SDHK", len(verk), len(passager), len(vittnen), kopplade)


if __name__ == "__main__":
    main()

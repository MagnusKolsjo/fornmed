"""
Bygger data/auktoriteter/biskopar.json ur svenska Wikipedias stiftslistor
och Wikidata.

Listorna över biskopar i Uppsala, Linköpings, Skara, Strängnäs, Västerås,
Växjö, Åbo och Lunds stift ger namn och ämbetsår; biskoparnas artiklar ger
Wikidata-id, och Wikidata ger levnadsår. En person som var biskop på flera
säten (Stenar i Linköping och Växjö) blir en post med flera titlar.

Listornas år är ofta ungefärliga ("omkring 1150 till cirka 1190",
"1050-talet", "omnämnd 1081"). Det ursprungliga uttrycket sparas i
'ar_text', och spannet vidgas med fem år där listan säger omkring eller
cirka. Skriptet skriver om filen; poster som finns i regenter.json under
samma Wikidata-id får regentens id, så att samma person har ett id.

    .venv/bin/python bygg_biskopslista.py
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

AUKTORITETER = Path(__file__).parent / "data" / "auktoriteter"
WIKI_API = "https://sv.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
ANVANDARAGENT = "fornmed/1.0 (icke-kommersiell forskningsdatabas)"
SISTA_TILLTRADE = 1536

# (sida, säte, titel, format)
STIFT = [
    ("Lista över biskopar i Uppsala stift", "Uppsala", "arkebiskop", "tabell"),
    ("Lista över biskopar i Linköpings stift", "Linköping", "biskop", "punkt"),
    ("Lista över biskopar i Skara stift", "Skara", "biskop", "punkt"),
    ("Lista över biskopar i Strängnäs stift", "Strängnäs", "biskop", "punkt"),
    ("Lista över biskopar i Västerås stift", "Västerås", "biskop", "punkt"),
    ("Lista över biskopar i Växjö stift", "Växjö", "biskop", "punkt"),
    ("Lista över biskopar i Åbo stift", "Åbo", "biskop", "abo"),
    ("Lista över ärkebiskopar och biskopar i Lunds stift", "Lund", "arkebiskop", "tabell"),
]

LANK = re.compile(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]")
AR = re.compile(r"(?<!\d)(\d{3,4})(?:-tal(?:et)?)?(?!\d)")


def _hamta(url: str, **parametrar) -> dict:
    parametrar |= {"format": "json", "formatversion": "2"}
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(parametrar)}",
                                 headers={"User-Agent": ANVANDARAGENT})
    for forsok in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as svar:
                return json.load(svar)
        except Exception as fel:  # noqa: BLE001 — Wikimedia svarar ibland med tom kropp vid hög last
            log.warning("%s, försöker igen", fel)
            time.sleep(5 * (forsok + 1))
    raise RuntimeError(f"Kunde inte hämta {parametrar}")


def _ar(text: str) -> tuple[int | None, int | None]:
    """Första och sista året i texten; vidgat vid omkring/cirka och decennier."""
    text = re.sub(r"\[\[(\d{1,2} \w+)\]\]", " ", text)   # dagar som [[5 augusti]]
    ar = []
    for m in AR.finditer(text):
        a = int(m.group(1))
        if 800 <= a <= 1700:
            ar.append(((a, a + 99) if a % 100 == 0 else (a, a + 9)) if "-tal" in m.group(0) else (a, a))
    if not ar:
        return None, None
    fran, till = ar[0][0], ar[-1][1]
    if re.search(r"omkring|cirka|ca\.?\s|troligen|\?", text, re.I):
        fran, till = fran - 5, till + 5
    return fran, till


def _rensa(text: str) -> str:
    text = LANK.sub(lambda m: m.group(2) or m.group(1), text)
    if text.count("(") > text.count(")"):
        text += ")"
    text = re.sub(r"'''?|<[^>]+>|\{\{[^}]*\}\}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def punktlista(wikitext: str) -> list[dict]:
    rader = []
    for rad in wikitext.splitlines():
        if not rad.startswith("*"):
            continue
        lank = LANK.search(rad)
        artikel = lank.group(1).strip() if lank else None
        namn = _rensa(lank.group(2) or lank.group(1)) if lank else _rensa(re.sub(r"^\*\s*[\d–\-/ ]*:?", "", rad))
        artal = _rensa(LANK.sub("", rad).lstrip("* "))
        if re.search(r"administrerades|[Vv]akant", rad):
            continue
        fran, till = _ar(artal)
        rader.append({"namn": namn, "artikel": artikel, "ar_text": artal.strip(" :,"), "fran": fran,
                      "till": till, "tilltradde_ej": "tillträd" in rad and "ej" in rad})
    return rader


def _celler(rad: str) -> list[str]:
    """Cellerna i en tabellrad. Tomma celler behålls, annars förskjuts kolumnerna."""
    celler = []
    for cell in re.split(r"\n\|(?![-}])", "\n" + rad)[1:]:
        for del_ in cell.split("||"):
            del_ = del_.strip()
            m = re.match(r"colspan=\"?(\d+)\"?\s*\|(.*)", del_, re.S)
            if m:
                celler += [m.group(2).strip()] * int(m.group(1))
            else:
                celler.append(del_)
    return celler


def tabell(wikitext: str) -> list[dict]:
    """Uppsala- och Lundalistornas tabeller: namn, bild, född, tillträde, avgång, död."""
    rader = []
    for rad in wikitext.split("\n|-"):
        celler = _celler(rad.split("\n|}")[0])
        if len(celler) < 5 or "Vakans" in celler[0]:
            continue
        lank = LANK.search(celler[0])
        if not lank or lank.group(1).startswith(("Fil:", "File:")):
            continue
        tilltrade, avgang = celler[3], celler[4]
        fran, _ = _ar(tilltrade)
        _, till = _ar(avgang)
        if fran is None:
            continue
        rader.append({"namn": _rensa(lank.group(2) or lank.group(1)), "artikel": lank.group(1).strip(),
                      "ar_text": f"{_rensa(tilltrade)} – {_rensa(avgang)}", "fran": fran,
                      "till": till or fran, "tilltradde_ej": "ej vigd" in tilltrade or "aldrig vigd" in tilltrade})
    return rader


def abo(wikitext: str) -> list[dict]:
    rader = []
    del_ = wikitext.split("Lutherska")[0]
    for rad in del_.split("\n|-"):
        celler = [c for c in _celler(rad) if c and not c.startswith(("[[File:", "[[Fil:"))]
        if len(celler) < 2:
            continue
        lank = LANK.search(celler[0])
        if not lank:
            continue
        fran, till = _ar(celler[1])
        rader.append({"namn": _rensa(lank.group(2) or lank.group(1)), "artikel": lank.group(1).strip(),
                      "ar_text": _rensa(celler[1]) + (f" ({_rensa(celler[2])})" if len(celler) > 2 and
                                                      celler[2].strip() else ""),
                      "fran": fran, "till": till, "tilltradde_ej": False})
    return rader


def wikidata(artiklar: list[str]) -> dict[str, dict]:
    """
    Artikel -> {qid, fodd, dod}. Omdirigeringar följs. Bara objekt för
    människor (P31 Q5) godtas: en artikel om en biskop utan eget objekt kan
    vara en omdirigering till stiftets lista eller ämbete.
    """
    ut: dict[str, dict] = {}
    for i in range(0, len(artiklar), 50):
        grupp = artiklar[i:i + 50]
        svar = _hamta(WIKI_API, action="query", titles="|".join(grupp), prop="pageprops",
                      ppprop="wikibase_item", redirects=1)["query"]
        alias = {r["from"]: r["to"] for r in svar.get("redirects", [])} | \
            {n["from"]: n["to"] for n in svar.get("normalized", [])}
        qid = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in svar["pages"]}
        for a in grupp:
            mal = alias.get(a, a)
            mal = alias.get(mal, mal)
            if qid.get(mal):
                ut[a] = {"qid": qid[mal]}
        time.sleep(3)
    qids = sorted({v["qid"] for v in ut.values()})
    liv: dict[str, tuple] = {}
    manniskor: set[str] = set()
    for i in range(0, len(qids), 50):
        svar = _hamta(WIKIDATA_API, action="wbgetentities", ids="|".join(qids[i:i + 50]), props="claims")
        for q, ent in svar["entities"].items():
            def ar(prop: str) -> int | None:
                for c in ent.get("claims", {}).get(prop, []):
                    v = c["mainsnak"].get("datavalue", {}).get("value", {})
                    m = re.match(r"[+-](\d{4})", v.get("time", ""))
                    # Precision under 9 är decennium eller sämre; sådana år används inte
                    if m and v.get("precision", 0) >= 9:
                        return int(m.group(1))
                return None
            liv[q] = (ar("P569"), ar("P570"))
            if any(c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == "Q5"
                   for c in ent.get("claims", {}).get("P31", [])):
                manniskor.add(q)
        time.sleep(3)
    ut = {a: v for a, v in ut.items() if v["qid"] in manniskor}
    for v in ut.values():
        v["fodd"], v["dod"] = liv.get(v["qid"], (None, None))
    return ut


def _slug(s: str) -> str:
    # Utan ordform: id:t ska kunna läsas som namnet ("johannes", inte "johanes")
    s = re.sub(r"\s*\(.*?\)", "", s).lower()
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o").replace("æ", "ae")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def bygg() -> dict:
    poster: dict[str, dict] = {}
    tolkare = {"punkt": punktlista, "tabell": tabell, "abo": abo}
    for sida, sate, titel, format_ in STIFT:
        text = _hamta(WIKI_API, action="parse", page=sida, prop="wikitext")["parse"]["wikitext"]
        rader = [r for r in tolkare[format_](text) if r["fran"] and r["fran"] <= SISTA_TILLTRADE]
        log.info("%s: %d biskopar", sate, len(rader))
        for r in rader:
            nyckel = r["artikel"] or f"{sate}:{r['namn']}"
            p = poster.setdefault(nyckel, {"namn": r["namn"], "artikel": r["artikel"], "titlar": []})
            # Lund var biskopssäte till 1103 och ärkesäte därefter; Uppsala ärkesäte från 1164
            t = "biskop" if (sate == "Lund" and r["fran"] < 1103) else titel
            p["titlar"].append([t, sate, r["fran"], r["till"] or r["fran"], r["ar_text"]]
                               + (["tillträdde ej"] if r["tilltradde_ej"] else []))
        time.sleep(2)

    wd = wikidata([a for a in poster if poster[a]["artikel"]])
    regenter = json.loads((AUKTORITETER / "regenter.json").read_text(encoding="utf-8"))["personer"]
    regent_qid = {r["wikidata"]: r["id"] for r in regenter if r.get("wikidata")}
    # Ett id som en gång delats ut behålls, även om Wikipedia byter namn på
    # artikeln eller listan ändras: nyckeln är Wikidata-id, artikel eller
    # namn och första säte
    tidigare: dict[str, str] = {}
    # Biskopar utan artikel har fått sitt Wikidata-id genom stift och år
    # (P39 med P708), inte genom artikeln; det id:t behålls också
    tidigare_qid: dict[str, str] = {}
    fil = AUKTORITETER / "biskopar.json"
    if fil.exists():
        for g in json.loads(fil.read_text(encoding="utf-8"))["personer"]:
            if g.get("wikidata"):
                tidigare_qid[g["id"]] = g["wikidata"]
            for k in (g.get("wikidata"), g.get("wikipedia"), f"{g['namn']}|{g['titlar'][0][1]}"):
                if k:
                    tidigare.setdefault(k, g["id"])
    personer, anvanda = [], set()
    for nyckel, p in poster.items():
        info = wd.get(nyckel, {})
        pid = regent_qid.get(info.get("qid")) or next(
            (tidigare[k] for k in (info.get("qid"), p["artikel"], f"{p['namn']}|{p['titlar'][0][1]}")
             if k and k in tidigare), None) or f"person:{_slug(p['namn'])}_{_slug(p['titlar'][0][1])}"
        while pid in anvanda:
            pid += "_2"
        anvanda.add(pid)
        fornamn = re.split(r"[ /(]", p["namn"])[0]
        personer.append({
            "id": pid, "namn": p["namn"], "fodd": info.get("fodd"), "dod": info.get("dod"),
            "fornamn": [fornamn], "titlar": [t[:4] for t in p["titlar"]],
            "ar_text": {t[1]: t[4] + (" (tillträdde ej)" if len(t) > 5 else "") for t in p["titlar"]},
            "wikidata": info.get("qid") or tidigare_qid.get(pid), "wikipedia": p["artikel"],
        })
    return {
        "beskrivning": "Biskopar och ärkebiskopar i Uppsala, Linköpings, Skara, Strängnäs, Västerås, Växjö, "
                       "Åbo och Lunds stift som tillträdde senast 1536. Byggd av bygg_biskopslista.py ur svenska "
                       "Wikipedias stiftslistor (CC BY-SA 4.0) och Wikidata (CC0). 'titlar' är [titel, säte, "
                       "från, till]; år som listan anger som ungefärliga är vidgade med fem år, och listans "
                       "ursprungliga uttryck står i 'ar_text'. Listorna bygger på äldre biskopslängder och "
                       "skiljer sig ibland från varandra och från nyare forskning. Biskopar utan artikel har "
                       "Wikidata-id när Wikidata anger dem som biskopar i samma stift och med samma år för tillträde, avgång eller död (högst tre års skillnad).",
        "hamtad": time.strftime("%Y-%m-%d"),
        "personer": personer,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = bygg()
    with open(AUKTORITETER / "biskopar.json", "w", encoding="utf-8") as ut:
        ut.write("{\n")
        for k in ("beskrivning", "hamtad"):
            ut.write(f' "{k}": {json.dumps(data[k], ensure_ascii=False)},\n')
        ut.write(' "personer": [\n')
        ut.write(",\n".join("  " + json.dumps(p, ensure_ascii=False) for p in data["personer"]))
        ut.write("\n ]\n}\n")
    log.info("%d personer, %d med Wikidata-id", len(data["personer"]),
             sum(1 for p in data["personer"] if p["wikidata"]))


if __name__ == "__main__":
    main()

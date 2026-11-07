"""
Prövar språkmodellens förslag på nutida namn för Diplomatarium Norvegicums utfärdandeorter mot
Kartverket och Wikidata, och skriver de som håller till data/platser/dn_orter.tsv.

Förslagen (data/platser/dn_normalisering/svar_*.jsonl) godtas aldrig på modellens ord. En norsk
ort måste vara entydig i Kartverkets register under sitt nutida namn, på samma sätt som i
platser.py. En ort i ett annat land måste finnas i Wikidata med koordinater, i rätt land och
med det föreslagna namnet som etikett eller alias. Landskap och andra regioner får inget läge.

Användning:
    python dn_orter.py
"""

import csv
import glob
import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

import hamta_ssr
from platser import _ssr, _ssr_lage

log = logging.getLogger("dn_orter")

KATALOG = Path(__file__).parent / "data" / "platser"
UT = KATALOG / "dn_orter.tsv"
WIKIDATA = "https://www.wikidata.org/w/api.php"
USER_AGENT = "fornmed/1.0 (https://fornmed.se)"
UTAN_LAGE = {"region", "okand"}


def _wikidata(**param) -> dict:
    url = WIKIDATA + "?" + urllib.parse.urlencode({"format": "json", **param})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as svar:
        return json.load(svar)


def _landkod(qid: str, cache: dict) -> str | None:
    if qid not in cache:
        e = _wikidata(action="wbgetentities", ids=qid, props="claims").get("entities", {}).get(qid, {})
        varden = [c["mainsnak"].get("datavalue", {}).get("value") for c in e.get("claims", {}).get("P297", [])]
        cache[qid] = (varden[0] or "").lower() if varden else None
    return cache[qid]


def wikidata_lage(forslag: dict, landcache: dict) -> dict | None:
    """Läget i Wikidata, om entiteten har förslagets namn, koordinater och rätt land."""
    qid = (forslag.get("wikidata") or "").strip()
    namn = forslag["nutida"].casefold()
    if not qid:
        traffar = _wikidata(action="wbsearchentities", search=forslag["nutida"], language="en", type="item", limit=5)
        qids = [t["id"] for t in traffar.get("search", [])]
    else:
        qids = [qid]
    for q in qids:
        time.sleep(0.1)
        e = _wikidata(action="wbgetentities", ids=q, props="labels|aliases|claims").get("entities", {}).get(q, {})
        etiketter = {v["value"].casefold() for v in e.get("labels", {}).values()}
        etiketter |= {a["value"].casefold() for lista in e.get("aliases", {}).values() for a in lista}
        koord = e.get("claims", {}).get("P625", [])
        lander = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P17", [])]
        if namn not in etiketter or not koord:
            continue
        if forslag.get("land") and not any(_landkod(l, landcache) == forslag["land"] for l in lander if l):
            continue
        v = koord[0]["mainsnak"]["datavalue"]["value"]
        return {"latitud": v["latitude"], "longitud": v["longitude"], "kalla": f"Wikidata {q}", "wikidata": q}
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    forslag = []
    for fil in sorted(glob.glob(str(KATALOG / "dn_normalisering" / "svar_*.jsonl"))):
        forslag += [json.loads(r) for r in open(fil, encoding="utf-8") if r.strip()]
    # Norska nutida namn som ännu inte är hämtade från Kartverket
    ssr = _ssr()
    saknas = sorted({f["nutida"] for f in forslag if f.get("land") == "no" and f.get("nutida")
                     and f["nutida"].casefold() not in ssr})
    if saknas:
        with hamta_ssr.FIL.open("a", encoding="utf-8") as fh:
            for n in saknas:
                fh.write(json.dumps({"namn": n, "traffar": hamta_ssr.hamta(n)}, ensure_ascii=False) + "\n")
                time.sleep(hamta_ssr.PAUS)
        ssr = _ssr()
    landcache: dict = {}
    rader, utfall = [], {}
    for f in forslag:
        if not f.get("nutida") or f.get("typ") in UTAN_LAGE:
            utfall["utan läge"] = utfall.get("utan läge", 0) + 1
            continue
        lage = None
        if f.get("land") == "no":
            if (s := _ssr_lage(f["nutida"], ssr)):
                lage = {"latitud": s["latitud"], "longitud": s["longitud"], "kalla": f"Kartverket ({s['typ']})", "wikidata": ""}
        else:
            try:
                lage = wikidata_lage(f, landcache)
            except Exception as e:
                log.warning("%s: %s", f["namn"], e)
        nyckel = "godtagen" if lage else "inte bekräftad"
        utfall[nyckel] = utfall.get(nyckel, 0) + 1
        if lage:
            rader.append([f["namn"], f["nutida"], f.get("land", ""), f.get("typ", ""), lage["latitud"], lage["longitud"],
                          lage["kalla"], lage["wikidata"], f.get("sakerhet", ""), f.get("motivering", "")])
    with UT.open("w", encoding="utf-8", newline="") as fh:
        skrivare = csv.writer(fh, delimiter="\t", lineterminator="\n")
        skrivare.writerow(["namn", "nutida", "land", "typ", "lat", "lon", "kalla", "wikidata", "sakerhet", "motivering"])
        skrivare.writerows(rader)
    log.info("%d förslag: %s", len(forslag), utfall)


if __name__ == "__main__":
    main()

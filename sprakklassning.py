"""
Bestämmer brevtextens språk med en klassare på teckenföljder, utan språkmodell.

Klassaren lär sig latin, fornsvenska, forndanska, fornnorska, fornisländska och (låg)tyska av
texter vars språk redan är känt (fornisländskan av sagorna i databasen): SDHK:s original med språkuppgift, Diplomatarium Norvegicums brev som
SDHK anger språket för, och Diplomatarium Danicums brevtexter med språkuppgift. Danicum
används bara för att lära klassaren och läses aldrig in i databasen.

Varje text delas i stycken om cirka 300 tecken som bedöms var för sig. Brevets språk är det
som har flest tecken, och ett stycke på ett annat språk (ett latinskt citat i ett norskt
brev) syns i fördelningen i stället för att avgöra brevet.

Användning:
    python sprakklassning.py --utvardera          # korsvalidering per brev
    python sprakklassning.py --klassa dn --fil ut.tsv
"""

import argparse
import csv
import glob
import logging
import random
import re
from collections import Counter, defaultdict
from html import unescape
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from fragor import _rader

log = logging.getLogger("sprakklassning")

DD_KATALOG = Path(__file__).parent / "data" / "raw" / "dd"
SPRAK = ["lat", "swe", "dan", "nor", "isl", "deu"]
# Danicums språkkoder: gda och xda är forndanska, gsv fornsvenska, xno fornnorska, gml och gmh tyska
DD_SPRAK = {"gda": "dan", "xda": "dan", "gsv": "swe", "xno": "nor", "gml": "deu", "gmh": "deu", "la": "lat"}
SDHK_SPRAK = {"{lat}": "lat", "{swe}": "swe", "{dan}": "dan", "{nor}": "nor", "{deu}": "deu"}
FONSTER = 300
MINSTA = 80
PER_SPRAK = 2500


def normalisera(text: str) -> str:
    text = re.sub(r"[\d\[\]().,:;!?«»\"'*†♦|/<>-]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def fonster(text: str) -> list[str]:
    """Stycken om cirka FONSTER tecken, delade vid mellanslag; korta rester slås ihop med föregående."""
    ord_, delar, nu = normalisera(text).split(), [], []
    for o in ord_:
        nu.append(o)
        if sum(len(x) + 1 for x in nu) >= FONSTER:
            delar.append(" ".join(nu))
            nu = []
    rest = " ".join(nu)
    if len(rest) >= MINSTA or not delar:
        delar.append(rest)
    elif delar:
        delar[-1] += " " + rest
    return [d for d in delar if len(d) >= MINSTA]


def _dd_text(fragment: str) -> str:
    fragment = re.sub(r"<rdg>.*?</rdg>|<note.*?</note>", "", fragment, flags=re.S)
    return unescape(re.sub(r"<[^>]+>", "", fragment))


def danicum() -> list[tuple[str, str, str]]:
    """(id, språk, text) ur Danicums grundtexter med språkuppgift; översättningarna tas inte med."""
    poster = []
    for fil in glob.glob(str(DD_KATALOG / "dd-*" / "*" / "*.xml")):
        t = Path(fil).read_text(encoding="utf-8")
        for lang, body in re.findall(r'<div(?: type="base_text")? xml:lang="([^"]+)"[^>]*>(.*?)</div>', t, re.S):
            if (sprak := DD_SPRAK.get(lang)):
                poster.append((f"dd:{Path(fil).stem}", sprak, _dd_text(body)))
    return poster


def kanda() -> list[tuple[str, str, str]]:
    """Brev med känt språk: SDHK:s original, DN-brev via SDHK-kopplingen och Danicum."""
    poster = [(r["id"], SDHK_SPRAK[r["sprak"]], r["text"]) for r in _rader(
        """SELECT v.id, v.sprak::text AS sprak, p.text FROM fornmed.verk v
           JOIN fornmed.passage p ON p.id = v.id || ':originaltext'
           WHERE v.kallsamling_id = 'sdhk' AND v.sprak::text IN ('{lat}', '{swe}', '{dan}', '{nor}', '{deu}')""")]
    poster += [(r["id"], SDHK_SPRAK[r["sprak"]], r["text"]) for r in _rader(
        """SELECT DISTINCT ON (d.id) d.id, s.sprak::text AS sprak, p.text FROM fornmed.verk d
           CROSS JOIN LATERAL jsonb_array_elements_text((d.extra::jsonb)->'sdhk') n
           JOIN fornmed.verk s ON s.id = 'sdhk:' || n
           JOIN fornmed.passage p ON p.id = d.id || ':originaltext'
           WHERE d.kallsamling_id = 'dn' AND s.sprak::text IN ('{lat}', '{swe}', '{dan}', '{nor}', '{deu}')""")]
    # Fornisländska: sagorna och kungasagorna i normaliserad stavning (inte runtexterna)
    poster += [(r["id"], "isl", r["text"]) for r in _rader(
        """SELECT p.id, p.text FROM fornmed.passage p WHERE p.typ = 'originaltext' AND p.sprak = 'non'
           AND (p.verk_id LIKE 'verk:saga%%' OR p.verk_id LIKE '%%heimskringla%%' OR p.verk_id LIKE '%%morkinskinna%%'
                OR p.verk_id LIKE '%%fagrskinna%%' OR p.verk_id LIKE '%%knytlinga%%' OR p.verk_id LIKE '%%edda%%')""")]
    # Isländsk brevstavning: DI-brev utfärdade på säkert isländska platser (alþingi, biskopssätena,
    # klostren). Sagorna ovan är normaliserade och liknar inte brevens stavning.
    poster += [(r["id"], "isl", r["text"]) for r in _rader(
        """SELECT v.id, p.text FROM fornmed.verk v JOIN fornmed.passage p ON p.id = v.id || ':originaltext'
           WHERE v.kallsamling_id = 'di' AND (v.extra::jsonb)->>'grans_osaker' = 'false'
           AND v.utfardandeort ~* '(alþing|alþíng|skálholt|skálliolt|hólum|þingvell|helgafell|viðey|þingeyr|munkaþver|möðruvöll|reykholt|oddi|flatey|vatnsfjörð|saurbæ|grund|ögri|skarði)'""")]
    poster += danicum()
    return [p for p in poster if len(p[2]) >= MINSTA]


def urval(poster: list[tuple], seed: int = 1) -> list[tuple]:
    """Högst PER_SPRAK brev per språk, så att latinet inte tränger undan de andra."""
    rng = random.Random(seed)
    per: dict[str, list] = defaultdict(list)
    for p in poster:
        per[p[1]].append(p)
    return [p for lista in per.values() for p in rng.sample(lista, min(PER_SPRAK, len(lista)))]


def tranad(poster: list[tuple]):
    texter, etiketter = [], []
    for _, sprak, text in poster:
        for f in fonster(text):
            texter.append(f)
            etiketter.append(sprak)
    vektor = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), min_df=3, sublinear_tf=True, max_features=300000)
    modell = LogisticRegression(max_iter=2000, C=5, class_weight="balanced")
    modell.fit(vektor.fit_transform(texter), etiketter)
    return vektor, modell


def bedom(vektor, modell, text: str) -> dict:
    """Brevets språk, andel per språk (räknat på tecken) och den lägsta säkerheten bland styckena."""
    delar = fonster(text)
    if not delar:
        return {"sprak": None, "andelar": {}, "sakerhet": 0.0, "stycken": 0}
    sannolikheter = modell.predict_proba(vektor.transform(delar))
    klasser = modell.classes_
    andelar: Counter = Counter()
    for del_, p in zip(delar, sannolikheter):
        andelar[klasser[int(np.argmax(p))]] += len(del_)
    summa = sum(andelar.values())
    andelar = {k: round(v / summa, 2) for k, v in andelar.most_common()}
    huvud = next(iter(andelar))
    sakerhet = float(np.mean([p[list(klasser).index(huvud)] for p in sannolikheter]))
    return {"sprak": huvud, "andelar": andelar, "sakerhet": round(sakerhet, 2), "stycken": len(delar)}


def utvardera(folder: int = 5) -> None:
    poster = urval(kanda())
    log.info("%d brev: %s", len(poster), dict(Counter(p[1] for p in poster)))
    rng = random.Random(7)
    grupp = {pid: rng.randrange(folder) for pid in {p[0] for p in poster}}
    forvaxling: Counter = Counter()
    dn: Counter = Counter()
    sakra = [0, 0]
    for f in range(folder):
        vektor, modell = tranad([p for p in poster if grupp[p[0]] != f])
        for pid, sprak, text in (p for p in poster if grupp[p[0]] == f):
            res = bedom(vektor, modell, text)
            forvaxling[(sprak, res["sprak"])] += 1
            if pid.startswith("dn:"):
                dn[(sprak, res["sprak"])] += 1
            if res["sakerhet"] >= 0.8 and next(iter(res["andelar"].values())) >= 0.8:
                sakra[0] += 1
                sakra[1] += sprak == res["sprak"]
        log.info("vikning %d klar", f + 1)
    for namn, tabell in (("alla", forvaxling), ("DN-brev med SDHK:s språk", dn)):
        print(f"\n{namn}: rätt {sum(v for (a, b), v in tabell.items() if a == b)} av {sum(tabell.values())}")
        print("känt \\ bedömt  " + "  ".join(f"{s:>5}" for s in SPRAK + ["-"]))
        for a in SPRAK:
            rad = [tabell[(a, b)] for b in SPRAK + [None]]
            if sum(rad):
                print(f"{a:>13}  " + "  ".join(f"{v:>5}" for v in rad) + f"   {rad[SPRAK.index(a)] / sum(rad):.1%}")
    print(f"\nSäkra bedömningar (säkerhet och huvudandel minst 0,8): {sakra[0]} brev, rätt {sakra[1] / max(1, sakra[0]):.1%}")


def klassa(kallsamling: str, fil: str) -> None:
    vektor, modell = tranad(urval(kanda()))
    rader = _rader("""SELECT v.id, p.text FROM fornmed.verk v JOIN fornmed.passage p ON p.id = v.id || ':originaltext'
                      WHERE v.kallsamling_id = %s ORDER BY v.id""", (kallsamling,))
    with open(fil, "w", encoding="utf-8", newline="") as f:
        skrivare = csv.writer(f, delimiter="\t", lineterminator="\n")
        skrivare.writerow(["verk_id", "sprak", "sakerhet", "andelar", "stycken"])
        for r in rader:
            res = bedom(vektor, modell, r["text"])
            skrivare.writerow([r["id"], res["sprak"] or "", res["sakerhet"],
                               " ".join(f"{k}:{v}" for k, v in res["andelar"].items()), res["stycken"]])
    log.info("%d brev klassade till %s", len(rader), fil)


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--utvardera", action="store_true")
    tolk.add_argument("--klassa", help="källsamling vars brev ska klassas, t.ex. dn")
    tolk.add_argument("--fil", default="sprak.tsv")
    argument = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if argument.utvardera:
        utvardera()
    elif argument.klassa:
        klassa(argument.klassa, argument.fil)


if __name__ == "__main__":
    main()

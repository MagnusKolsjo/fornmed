"""
Tar ut två eller tre stycken ur brev vars språk klassaren inte kunnat avgöra, för bedömning
av en språkmodell.

Urvalet styrs av klassarens bedömning av varje stycke: ett eller två stycken på brevets
troliga huvudspråk (helst början och mitten) och det stycke som avviker mest. Stycken som
klassaren säkert bedömt som latin tas bara med om hela brevet är latin, så att ett citat inte
blir hela underlaget. Styckena återges som i källan, utan normalisering.

Användning:
    python sprak_urval.py --prov 100 --kanda 100 --ut data/sprak/prov
    python sprak_urval.py --alla --kanda 100 --uteslut data/sprak/prov/facit.tsv --ut data/sprak/omgang
"""

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np

import sprakklassning as sk
from fragor import _rader

STORLEK = 300


def stycken(text: str) -> list[str]:
    ord_, delar, nu = text.split(), [], []
    for o in ord_:
        nu.append(o)
        if sum(len(x) + 1 for x in nu) >= STORLEK:
            delar.append(" ".join(nu))
            nu = []
    if nu:
        if delar and len(" ".join(nu)) < sk.MINSTA:
            delar[-1] += " " + " ".join(nu)
        else:
            delar.append(" ".join(nu))
    return delar


def utdrag(vektor, modell, text: str) -> list[dict]:
    delar = stycken(text)
    if not delar:
        return []
    p = modell.predict_proba(vektor.transform([sk.normalisera(d) for d in delar]))
    klasser = list(modell.classes_)
    etikett = [klasser[int(np.argmax(x))] for x in p]
    langd = {}
    for d, e in zip(delar, etikett):
        langd[e] = langd.get(e, 0) + len(d)
    huvud = max((e for e in langd if e != "lat"), key=langd.get, default="lat")
    lage = lambda i: "början" if i == 0 else "slutet" if i == len(delar) - 1 else "mitten"
    ej_citat = [i for i, e in enumerate(etikett) if not (e == "lat" and huvud != "lat" and p[i][klasser.index("lat")] > 0.9)]
    valda = []
    huvudstycken = [i for i in ej_citat if etikett[i] == huvud]
    if huvudstycken:
        valda.append(huvudstycken[0])
        if len(huvudstycken) > 2:
            valda.append(huvudstycken[len(huvudstycken) // 2])
    avvikande = sorted((i for i in ej_citat if i not in valda), key=lambda i: p[i][klasser.index(huvud)])
    if avvikande:
        valda.append(avvikande[0])
    if not valda:
        valda = [0]
    return [{"lage": lage(i), "stycke": f"{i + 1} av {len(delar)}", "text": delar[i]} for i in sorted(set(valda))[:3]]


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--prov", type=int, default=100, help="antal osäkra brev")
    tolk.add_argument("--kanda", type=int, default=100, help="antal brev med känt språk, för kontroll")
    tolk.add_argument("--ut", default="data/sprak/prov")
    tolk.add_argument("--alla", action="store_true", help="ta alla osäkra brev")
    tolk.add_argument("--uteslut", help="facit från ett tidigare prov; de kontrollbreven tas inte igen")
    tolk.add_argument("--kallsamling", default="dn", help="dn eller di; klassningen läses ur data/sprak/{kallsamling}_sprak.tsv")
    a = tolk.parse_args()
    rng = random.Random(11)
    bedomt = {r["verk_id"]: r for r in csv.DictReader(open(f"data/sprak/{a.kallsamling}_sprak.tsv", encoding="utf-8"), delimiter="\t")}
    meta = {r["id"]: (r["datering_edtf"], r["utfardandeort"]) for r in _rader(
        "SELECT id, datering_edtf, utfardandeort FROM fornmed.verk WHERE kallsamling_id = %s", (a.kallsamling,))}
    texter = {r["id"]: r["text"] for r in _rader("""SELECT v.id, p.text FROM fornmed.verk v
        JOIN fornmed.passage p ON p.id = v.id || ':originaltext' WHERE v.kallsamling_id = %s""", (a.kallsamling,))}
    saker = {r["id"]: r["sprak"] for r in _rader("""SELECT id, sprak::text AS sprak FROM fornmed.verk
        WHERE kallsamling_id = %s AND sprak IS NOT NULL AND sprak::text <> '{}'""", (a.kallsamling,))}
    osakra = sorted(i for i in texter if i in bedomt and i not in saker and len(texter[i]) >= sk.MINSTA)
    facit = []
    tidigare = set()
    if a.uteslut:
        tidigare = {r["verk_id"] for r in csv.DictReader(open(a.uteslut, encoding="utf-8"), delimiter="\t")}
    urval = osakra if a.alla else rng.sample(osakra, a.prov)
    if a.kanda:
        # Kontrollbrev: SDHK:s språk där det finns, annars klassarens säkra bedömning, jämnt över språken
        sdhk = {r["id"]: sk.SDHK_SPRAK[r["sprak"]] for r in _rader("""SELECT DISTINCT ON (d.id) d.id, s.sprak::text AS sprak
            FROM fornmed.verk d CROSS JOIN LATERAL jsonb_array_elements_text((d.extra::jsonb)->'sdhk') n
            JOIN fornmed.verk s ON s.id = 'sdhk:' || n WHERE d.kallsamling_id = 'dn'
            AND s.sprak::text IN ('{lat}', '{swe}', '{dan}', '{nor}', '{deu}')""")}
        per_sprak = {}
        for i, s in sdhk.items():
            if i in tidigare:
                continue
            per_sprak.setdefault(s, []).append((i, s, "SDHK"))
        for i, s in saker.items():
            if i not in sdhk and i not in tidigare:
                per_sprak.setdefault(s.strip("{}"), []).append((i, s.strip("{}"), "klassaren"))
        kandidater = [rng.sample(v, len(v)) for v in per_sprak.values()]
        while len(facit) < a.kanda and any(kandidater):
            for lista in kandidater:
                if lista and len(facit) < a.kanda:
                    facit.append(lista.pop())
        urval += [f[0] for f in facit]
    rng.shuffle(urval)
    vektor, modell = sk.tranad(sk.urval(sk.kanda()))
    ut = Path(a.ut)
    ut.mkdir(parents=True, exist_ok=True)
    with (ut / "urval.jsonl").open("w", encoding="utf-8") as f:
        for i in urval:
            f.write(json.dumps({"id": i, "datum": meta[i][0], "ort": meta[i][1],
                                "utdrag": utdrag(vektor, modell, texter[i])}, ensure_ascii=False) + "\n")
    with (ut / "facit.tsv").open("w", encoding="utf-8") as f:
        f.write("verk_id\tsprak\tkalla\n" + "".join(f"{i}\t{s}\t{k}\n" for i, s, k in facit))
    print(len(urval), "brev,", len(facit), "kontrollbrev")


if __name__ == "__main__":
    main()

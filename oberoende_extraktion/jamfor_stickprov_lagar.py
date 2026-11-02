"""
Jämför vår extraktion av lagstickprovet med den oberoende och skriver en
rapport över skillnaderna, flock för flock.

    python oberoende_extraktion/jamfor_stickprov_lagar.py \\
        oberoende_extraktion/jamforelse_lagar/A_stickprov.json \\
        oberoende_extraktion/lagar/utdata_lagar_stickprov.json \\
        oberoende_extraktion/jamforelse_lagar/jamforelse.md [indata.json]

För delarna av hela materialet anges delens indatafil som fjärde argument.

Påståendena paras på passage, predikat, subjekt och objektets id. Fria
värden och värdedelen efter '|' jämförs för sig, så att olika ordval inte
räknas som olika påståenden. Har en nyckel flera påståenden, till exempel
olika bot för fri man och träl, paras de efter hur lika värdena är.
Påståenden som bara finns i den ena versionen men har samma passage och
predikat som ett i den andra ställs upp bredvid varandra, eftersom de oftast
är samma regel modellerad på olika sätt. Ed, tylftered och edgärd räknas som
samma objekt, eftersom gränsen mellan dem är en modelleringsfråga.
"""

import difflib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

INDATA = Path(__file__).resolve().parent / "lagar" / "indata_lagar_stickprov.json"
EDER = {"begrepp:ed", "begrepp:tylftered", "begrepp:edgard"}


def las(fil):
    d = json.load(open(fil, encoding="utf-8"))
    ut = []
    for rad in d["pastaenden"]:
        objekt = rad[3].strip()
        if objekt.startswith("="):
            oid, varde = "=", objekt[1:]
        elif "|" in objekt:
            oid, varde = (x.strip() for x in objekt.split("|", 1))
        else:
            oid, varde = objekt, ""
        ut.append({"passage": rad[0], "subjekt": rad[1], "predikat": rad[2], "oid": oid, "varde": varde,
                   "citat": rad[5], "anm": rad[6] if len(rad) > 6 and rad[6] else "", "rad": rad})
    return ut


def lika(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    a, b = las(sys.argv[1]), las(sys.argv[2])
    indata = json.load(open(sys.argv[4] if len(sys.argv) == 5 else INDATA, encoding="utf-8"))
    namn = {k["id"]: k["namn"] for g in indata["kandidater"].values() for k in g}
    n = lambda eid: "=" if eid == "=" else namn.get(eid, eid)

    nyckel = lambda p: (p["passage"], p["predikat"], p["subjekt"], "ed" if p["oid"] in EDER else p["oid"])
    a_idx, b_idx = defaultdict(list), defaultdict(list)
    for p in a:
        a_idx[nyckel(p)].append(p)
    for p in b:
        b_idx[nyckel(p)].append(p)

    par, bara_a, bara_b = [], [], []
    for k in set(a_idx) | set(b_idx):
        xa, xb = list(a_idx.get(k, [])), list(b_idx.get(k, []))
        while xa and xb:
            i, j = max(((i, j) for i in range(len(xa)) for j in range(len(xb))),
                       key=lambda ij: lika(xa[ij[0]]["varde"], xb[ij[1]]["varde"]))
            par.append((xa.pop(i), xb.pop(j)))
        bara_a += xa
        bara_b += xb

    per_passage = defaultdict(lambda: {"par": [], "a": [], "b": []})
    for pa, pb in par:
        per_passage[pa["passage"]]["par"].append((pa, pb))
    for p in bara_a:
        per_passage[p["passage"]]["a"].append(p)
    for p in bara_b:
        per_passage[p["passage"]]["b"].append(p)

    rad = lambda p: (f"{n(p['subjekt'])} · {p['predikat']} · {n(p['oid'])}"
                     + (f": {p['varde']}" if p["varde"] else "") + f" — «{p['citat']}»"
                     + (f" ({p['anm']})" if p["anm"] else ""))
    ut = [f"# Jämförelse av lagstickprovet: A {sys.argv[1]}, B {sys.argv[2]}", "",
          f"- flockar: {len(indata['passager'])}",
          f"- A: {len(a)} påståenden, B: {len(b)}",
          f"- gemensamma: {len(par)} (A {len(par) / max(len(a), 1):.0%}, B {len(par) / max(len(b), 1):.0%})",
          f"- bara i A: {len(bara_a)}, bara i B: {len(bara_b)}", ""]

    per_lag = defaultdict(Counter)
    for pid, p in indata["passager"].items():
        per_lag[p["lag"]]["flockar"] += 1
        per_lag[p["lag"]]["gemensamma"] += len(per_passage[pid]["par"])
        per_lag[p["lag"]]["bara A"] += len(per_passage[pid]["a"])
        per_lag[p["lag"]]["bara B"] += len(per_passage[pid]["b"])
    ut += ["| lag | flockar | gemensamma | bara A | bara B |", "|---|---|---|---|---|"]
    for lag, c in per_lag.items():
        ut.append(f"| {lag} | {c['flockar']} | {c['gemensamma']} | {c['bara A']} | {c['bara B']} |")

    per_pred = Counter((p["predikat"], "gemensamma") for p, _ in par)
    per_pred.update((p["predikat"], "bara A") for p in bara_a)
    per_pred.update((p["predikat"], "bara B") for p in bara_b)
    ut += ["", "| predikat | gemensamma | bara A | bara B |", "|---|---|---|---|"]
    for pred in sorted({k for k, _ in per_pred}):
        ut.append(f"| {pred} | {per_pred[pred, 'gemensamma']} | {per_pred[pred, 'bara A']} | {per_pred[pred, 'bara B']} |")

    ut += ["", "## Flock för flock", ""]
    for pid, p in indata["passager"].items():
        x = per_passage[pid]
        rubrik = p["adress"] if p["adress"].startswith(p["lag"]) else f"{p['lag']} {p['adress']}"
        olika = [(pa, pb) for pa, pb in x["par"] if pa["varde"] and lika(pa["varde"], pb["varde"]) < 0.5]
        if not (x["a"] or x["b"] or olika):
            ut.append(f"- **{rubrik}** (`{pid}`): {len(x['par'])} gemensamma, inga skillnader")
            continue
        ut += ["", f"### {rubrik} (`{pid}`)", "", f"{len(x['par'])} gemensamma.", ""]
        samma_pred = {q["predikat"] for q in x["b"]}
        for q in x["a"]:
            ut.append(f"- **bara A**{' (B har annan modellering)' if q['predikat'] in samma_pred else ''}: {rad(q)}")
        samma_pred = {q["predikat"] for q in x["a"]}
        for q in x["b"]:
            ut.append(f"- **bara B**{' (A har annan modellering)' if q['predikat'] in samma_pred else ''}: {rad(q)}")
        for pa, pb in olika:
            ut.append(f"- **olika värde** {n(pa['subjekt'])} · {pa['predikat']} · {n(pa['oid'])}: "
                      f"A «{pa['varde']}», B «{pb['varde']}»")
    Path(sys.argv[3]).write_text("\n".join(ut) + "\n", encoding="utf-8")
    # Samma skillnader i maskinläsbar form, för bedömning flock för flock
    skillnader = []
    for pid, x in per_passage.items():
        for typ, lista in (("bara_A", x["a"]), ("bara_B", x["b"])):
            skillnader += [{"typ": typ, "passage": pid, "rad": q["rad"]} for q in lista]
        skillnader += [{"typ": "olika_varde", "passage": pid, "A": pa["rad"], "B": pb["rad"]}
                       for pa, pb in x["par"] if pa["varde"] and lika(pa["varde"], pb["varde"]) < 0.5]
    for i, sk in enumerate(skillnader, 1):
        sk["id"] = i
    Path(sys.argv[3]).with_suffix(".json").write_text(json.dumps(skillnader, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
    print("\n".join(ut[2:6]))


if __name__ == "__main__":
    main()

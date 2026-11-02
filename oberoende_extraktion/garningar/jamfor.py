"""
Jämför två extraktioner av samma källa och skriver en rapport över skillnaderna.

    python jamfor.py A.json B.json rapport.md

Entiteterna paras ihop i tre steg: samma id; en egen entitet i den ena
versionen som identifierats med en kandidat som den andra använder direkt;
och personer som är subjekt för ämbetet i samma post. Påståendena paras
sedan på passage, predikat, subjekt och objekt. Fria värden ("=dör
sotdöden") och platser jämförs för sig, så att olika ordval inte räknas som
olika påståenden.
"""

import json
import re
import sys
from collections import defaultdict


def las(fil):
    d = json.load(open(fil, encoding="utf-8"))
    prefix = d["passager"]
    pastaenden = []
    for rad in d["pastaenden"]:
        passage, subjekt, pred, objekt, plats, citat = rad[:6]
        m = re.match(r"([A-Za-z]+)(\d.*|inledning)", passage)
        kort = passage
        if m and m.group(1) in prefix:
            passage = prefix[m.group(1)] + m.group(2)
        pastaenden.append({"kort": kort, "passage": passage, "subjekt": subjekt, "predikat": pred,
                           "objekt": objekt, "plats": plats, "citat": citat,
                           "anm": rad[6] if len(rad) > 6 else None})
    d["pastaenden"] = pastaenden
    d["namn"] = {e[0]: e[2] for e in d["entiteter"]}
    return d


def para_entiteter(a, b):
    """Avbildning från B:s entiteter till A:s, och de identifieringsskillnader som syns."""
    till_a = {}
    anm = []
    # Identifieringar: B:s egen entitet = kandidat som A använder (och omvänt)
    for x, y, d in ((a, b, "A"), (b, a, "B")):
        for e, med, varde, motivering in x["identifieringar"]:
            anvand_direkt = any(med in (p["subjekt"], p["objekt"]) for p in y["pastaenden"])
            if anvand_direkt:
                if d == "B":
                    till_a[e] = med
                else:
                    till_a[med] = e
                anm.append((d, e, med, varde, motivering))
    # Ämbetsinnehavaren i samma post
    amb_a = defaultdict(list)
    for p in a["pastaenden"]:
        if p["predikat"] == "innehar_ambete":
            amb_a[p["passage"]].append(p["subjekt"])
    for p in b["pastaenden"]:
        if p["predikat"] == "innehar_ambete" and p["subjekt"] not in till_a:
            kandidater = [s for s in amb_a.get(p["passage"], []) if s not in till_a.values() or s == p["subjekt"]]
            if p["subjekt"] in amb_a.get(p["passage"], []):
                till_a[p["subjekt"]] = p["subjekt"]
            elif len(set(kandidater)) == 1:
                till_a[p["subjekt"]] = kandidater[0]
    # Platser och övriga med samma namn
    namn_a = {}
    for eid, n in a["namn"].items():
        namn_a.setdefault(n.lower().split(" (")[0], eid)
    for eid, n in b["namn"].items():
        if eid not in till_a and n.lower().split(" (")[0] in namn_a:
            till_a[eid] = namn_a[n.lower().split(" (")[0]]
    return till_a, anm


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    a, b = las(sys.argv[1]), las(sys.argv[2])
    indata_namn = {}
    try:
        ind = json.load(open("indata_vastgotalagens_langder.json", encoding="utf-8"))
        indata_namn = {k["id"]: k["namn"] for g in ind["kandidater"].values() for k in g}
    except FileNotFoundError:
        pass
    till_a, idanm = para_entiteter(a, b)
    m = lambda eid: till_a.get(eid, eid) if eid and not eid.startswith("=") else eid
    namn = {**indata_namn, **b["namn"], **a["namn"]}
    n = lambda eid: (namn.get(eid, eid) if eid and not eid.startswith("=") else (eid or "–"))

    def nyckel(p, mappa):
        obj = p["objekt"] if not p["objekt"].startswith("=") else "="
        return (p["passage"], p["predikat"], mappa(p["subjekt"]), mappa(obj))

    a_idx = defaultdict(list)
    for p in a["pastaenden"]:
        a_idx[nyckel(p, lambda x: x)].append(p)
    b_idx = defaultdict(list)
    for p in b["pastaenden"]:
        b_idx[nyckel(p, m)].append(p)

    gemensamma = sorted(set(a_idx) & set(b_idx))
    bara_a = sorted(set(a_idx) - set(b_idx))
    bara_b = sorted(set(b_idx) - set(a_idx))
    olika_plats, olika_varde = [], []
    for k in gemensamma:
        pa, pb = a_idx[k][0], b_idx[k][0]
        if m(pb["plats"]) != pa["plats"]:
            olika_plats.append((pa, pb))
        if pa["objekt"].startswith("=") and pa["objekt"] != pb["objekt"]:
            olika_varde.append((pa, pb))

    ord_ = lambda k: (k[0].split(":")[0], int(re.sub(r"\D", "", k[0].split(":")[1]) or 0), k[1])
    ut = [f"# Jämförelse: {sys.argv[1]} (A) och {sys.argv[2]} (B)", "",
          f"- A: {len(a['pastaenden'])} påståenden, B: {len(b['pastaenden'])}",
          f"- gemensamma: {len(gemensamma)}, bara i A: {len(bara_a)}, bara i B: {len(bara_b)}",
          f"- gemensamma med olika plats: {len(olika_plats)}, med olika fritt värde: {len(olika_varde)}", ""]
    ut += ["## Identifieringar", ""]
    for d, e, med, varde, mot in idanm:
        ut.append(f"- {d}: {n(e)} = {n(med)} ({varde}) — {mot}")
    for rubrik, nycklar, idx in (("Bara i A", bara_a, a_idx), ("Bara i B", bara_b, b_idx)):
        ut += ["", f"## {rubrik}", "", "| post | subjekt | predikat | objekt | plats | citat | anm. |", "|---|---|---|---|---|---|---|"]
        for k in sorted(nycklar, key=ord_):
            for p in idx[k]:
                ut.append(f"| {p['kort']} | {n(p['subjekt'])} | {p['predikat']} | {n(p['objekt'])} | "
                          f"{n(p['plats'])} | {p['citat']} | {p['anm'] or ''} |")
    ut += ["", "## Gemensamma med olika plats", ""]
    for pa, pb in olika_plats:
        ut.append(f"- {pa['kort']} {n(pa['subjekt'])} {pa['predikat']}: A {n(pa['plats'])}, B {n(pb['plats'])}")
    ut += ["", "## Gemensamma med olika fritt värde", ""]
    for pa, pb in olika_varde:
        ut.append(f"- {pa['kort']} {n(pa['subjekt'])} {pa['predikat']}: A {pa['objekt']!r}, B {pb['objekt']!r}")
    open(sys.argv[3], "w", encoding="utf-8").write("\n".join(ut) + "\n")
    print("\n".join(ut[:6]))


if __name__ == "__main__":
    main()

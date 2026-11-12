"""Delar Olaus Petris och Peder Swarts krönikor i jobb om högst MAX tecken."""
import json, sys
sys.path.insert(0, "<projektmapp>")
import db
MAX = 72000
# (verk, utgåvor att översätta; None = alla) i prioritetsordning
VERK = [("verk:olaus_petris_kronika", None), ("verk:peder_swarts_kronika", None)]
cur = db._hamta_db().cursor()
jobb = []
for verk, utgavor in VERK:
    cur.execute("select id, utgava_id, length(text) from fornmed.passage where verk_id=%s and typ='originaltext' order by ordning, id", (verk,))
    rader = cur.fetchall()
    slug = verk.split(":")[-1]
    i = 0
    while i < len(rader):
        utg = rader[i][1]
        if utgavor and utg not in utgavor:
            i += 1; continue
        fran, tecken = i, 0
        while i < len(rader) and rader[i][1] == utg and (not tecken or tecken + rader[i][2] <= MAX):
            tecken += rader[i][2]; i += 1
        jobb.append({"verk": verk, "fran": fran, "till": i, "tecken": tecken, "sprak": "äldre nysvenska",
                     "utgava": utg, "fil": f"data/oversattningar/fornsvenska/{slug}__{fran}-{i}.json"})
uppdrag = []
for d in jobb:  # små delar packas ihop, i prioritetsordning
    for u in uppdrag:
        if sum(x["tecken"] for x in u) + d["tecken"] <= MAX and len(u) < 6:
            u.append(d); break
    else:
        uppdrag.append([d])
json.dump(uppdrag, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(len(uppdrag), "uppdrag,", sum(d["tecken"] for d in jobb), "tecken")
for n, u in enumerate(uppdrag, 147):
    print(n, sum(x["tecken"] for x in u), [f"{x['verk'].split(':')[-1]} {x['fran']}-{x['till']}" for x in u])

"""Delar verken i jobb om högst MAX tecken och skriver uppdrag.json."""
import json, sys
sys.path.insert(0, "<projektmapp>")
import db
MAX = 72000
SAGOR = ["ragnarssona_thattr", "yngvars_saga_vidforla", "gautreks_saga", "hrolfs_saga_gautrekssonar",
         "bosa_saga_ok_herrauds", "orvar_odds_saga", "sturlaugs_saga_starfsama"]
LEGENDER = ["erikslegenden", "om_erik_den_helige", "ansgarii_leverne", "sigfridslegenden", "olavslegenden",
            "magnus_jarl", "katarina_av_sverige", "birgittas_liv", "birgittaautograferna"]
cur = db._hamta_db().cursor()
def delar(verk, katalog, sprak):
    cur.execute("select id, length(text) from fornmed.passage where verk_id=%s and typ='originaltext' order by ordning, id", (verk,))
    rader = cur.fetchall(); ut = []; fran = 0; tecken = 0
    for i, (_, n) in enumerate(rader):
        if tecken and tecken + n > MAX:
            ut.append((fran, i, tecken)); fran, tecken = i, 0
        tecken += n
    ut.append((fran, len(rader), tecken))
    slug = verk.split(":")[-1]
    return [{"verk": verk, "fran": a, "till": b, "tecken": t, "sprak": sprak,
             "fil": f"data/oversattningar/{katalog}/{slug}__{a}-{b}.json"} for a, b, t in ut]
jobb = [d for s in SAGOR for d in delar(f"verk:saga:{s}", "sagor", "fornvästnordiska")] + \
       [d for s in LEGENDER for d in delar(f"verk:fsv:{s}", "fornsvenska", "fornsvenska")]
# Packa små delar av samma språk i samma uppdrag
uppdrag = []
for d in sorted(jobb, key=lambda d: (d["sprak"], -d["tecken"])):
    for u in uppdrag:
        if u[0]["sprak"] == d["sprak"] and sum(x["tecken"] for x in u) + d["tecken"] <= MAX:
            u.append(d); break
    else:
        uppdrag.append([d])
json.dump(uppdrag, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
for i, u in enumerate(uppdrag, 60):
    print(i, sum(x["tecken"] for x in u), [f"{x['verk'].split(':')[-1]} {x['fran']}-{x['till']}" for x in u])

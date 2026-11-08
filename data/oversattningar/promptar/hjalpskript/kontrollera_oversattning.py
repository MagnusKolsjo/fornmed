"""Kontrollerar en översättningsfil: rätt id-mängd, inga tomma värden, rimlig längdkvot per passage.
python kontrollera_oversattning.py <fil> <verk_id> <fran> <till> [typer]"""
import sys, json, re
sys.path.insert(0, "<projektmapp>")
import db
fil, verk, fran, till = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
typer = (sys.argv[5] if len(sys.argv) > 5 else "originaltext").split(",")
cur = db._hamta_db().cursor()
cur.execute("select id, text from fornmed.passage where verk_id=%s and typ=any(%s) order by ordning, id", (verk, typer))
orig = dict(cur.fetchall()[fran:till])
try:
    d = json.load(open(fil, encoding="utf-8"))
except Exception as e:
    print(f"FEL {fil}: {e}"); sys.exit(1)
saknas, extra = set(orig) - set(d), set(d) - set(orig)
tomma = [k for k, v in d.items() if not str(v).strip()]
kvoter = {k: len(d[k]) / max(len(orig[k]), 1) for k in orig if k in d}
konstiga = sorted((round(q, 2), k) for k, q in kvoter.items() if (q < 0.6 or q > 2.2) and len(orig[k]) > 150)
tot = sum(len(d[k]) for k in kvoter) / max(sum(len(orig[k]) for k in kvoter), 1)
status = "OK" if not (saknas or extra or tomma) else "FEL"
print(f"{status} {fil.split('/')[-1]}: {len(d)}/{len(orig)} passager, längdkvot {tot:.2f}, saknas {len(saknas)}, extra {len(extra)}, tomma {len(tomma)}, avvikande kvot {konstiga[:6]}")

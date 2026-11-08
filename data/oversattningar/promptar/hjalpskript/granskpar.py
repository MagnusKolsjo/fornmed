"""Skriver ut original och nuvarande översättning för en äldre översättningsfil.
python granskpar.py <översättningsfil> [--nycklar k1,k2,...] [--fran N] [--till M]
Originalets id är nyckeln utan ':sv' (gutniska, liber_monstrorum) eller med ':sv'
utbytt mot originalets språkkod (romerska, arabiska)."""
import sys, json, argparse
sys.path.insert(0, "<projektmapp>")
import db
a = argparse.ArgumentParser(); a.add_argument("fil"); a.add_argument("--nycklar", default="")
a.add_argument("--fran", type=int, default=0); a.add_argument("--till", type=int, default=10**9)
arg = a.parse_args()
d = json.load(open(arg.fil, encoding="utf-8"))
nycklar = arg.nycklar.split(",") if arg.nycklar else list(d)[arg.fran:arg.till]
cur = db._hamta_db().cursor()
ut = {}
for k in nycklar:
    bas = k[:-3]
    cur.execute("select id, sprak, adress, text from fornmed.passage where typ='originaltext' and (id=%s or id ~ %s) order by id",
                (bas, "^" + bas.replace(".", "\\.") + ":(lat|grc|ara)$"))
    r = cur.fetchone()
    ut[k] = {"original_id": r[0], "sprak": r[1], "adress": r[2], "original": r[3], "nuvarande": d[k]}
print(json.dumps(ut, ensure_ascii=False, indent=1))

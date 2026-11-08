"""Kontrollerar att en översättningsfil har exakt id:na i en JSON-lista: python kontroll_ids.py <utfil> <idfil.json>"""
import sys, json
sys.path.insert(0, "<projektmapp>")
import db
fil, idfil = sys.argv[1], sys.argv[2]
ids = json.load(open(idfil)); d = json.load(open(fil, encoding="utf-8"))
cur = db._hamta_db().cursor(); cur.execute("select id, text from fornmed.passage where id = any(%s)", (ids,)); orig = dict(cur.fetchall())
saknas, extra = set(ids) - set(d), set(d) - set(ids)
tomma = [k for k, v in d.items() if not str(v).strip()]
kv = sorted((round(len(d[k]) / max(len(orig[k]), 1), 2), k) for k in ids if k in d)
konst = [x for x in kv if (x[0] < 0.6 or x[0] > 2.2) and len(orig[x[1]]) > 150]
print(("OK" if not (saknas or extra or tomma) else "FEL"), f"{len(d)}/{len(ids)}, saknas {len(saknas)}, extra {len(extra)}, tomma {len(tomma)}, avvikande kvot {konst[:6]}")

"""Skriver ut originalpassager för id i en JSON-lista: python kalltext_ids.py <idfil.json> [--fran N --till M]"""
import sys, json, argparse
sys.path.insert(0, "<projektmapp>")
import db
a = argparse.ArgumentParser(); a.add_argument("idfil"); a.add_argument("--fran", type=int, default=0); a.add_argument("--till", type=int, default=10**9)
arg = a.parse_args()
ids = json.load(open(arg.idfil))[arg.fran:arg.till]
cur = db._hamta_db().cursor()
cur.execute("select id, adress, sprak, text from fornmed.passage where id = any(%s)", (ids,))
r = {x[0]: x for x in cur.fetchall()}
print(json.dumps({i: {"adress": r[i][1], "sprak": r[i][2], "text": r[i][3]} for i in ids if i in r}, ensure_ascii=False, indent=1))

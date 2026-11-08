"""Skriver ut originalpassager som JSON: python kalltext.py <verk_id eller id-prefix> [--fran N] [--till M]"""
import sys, json, argparse
sys.path.insert(0, "<projektmapp>")
import db
a = argparse.ArgumentParser(); a.add_argument("urval"); a.add_argument("--fran", type=int, default=0); a.add_argument("--till", type=int, default=10**9)
a.add_argument("--typer", default="originaltext,skolion")
arg = a.parse_args()
cur = db._hamta_db().cursor()
cur.execute("select id, adress, sprak, text from fornmed.passage where (verk_id = %s or id like %s) and typ = any(%s) order by ordning, id",
            (arg.urval, arg.urval + "%", arg.typer.split(",")))
rader = cur.fetchall()[arg.fran:arg.till]
print(json.dumps({r[0]: {"adress": r[1], "sprak": r[2], "text": r[3]} for r in rader}, ensure_ascii=False, indent=1))

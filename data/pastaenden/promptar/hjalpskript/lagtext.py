"""
Skriver ut fornsvensk originaltext (och, med --sv, översättningen som läshjälp)
för en lags flockar.

    cd <projektmapp>
    python <denna fil> VERK_ID [ADRESSMÖNSTER ...] [--sv] [--sok ORD ...]

ADRESSMÖNSTER är reguljära uttryck mot passagens adress, t.ex. ' Mb ' eller
' Kgb '. --sok begränsar till flockar vars översättning innehåller något av
orden. Utan mönster skrivs hela lagen ut.
"""
import re
import sys

sys.path.insert(0, "<projektmapp>")
import db  # noqa: E402

args = sys.argv[1:]
sv = "--sv" in args
args = [a for a in args if a != "--sv"]
sok = []
if "--sok" in args:
    i = args.index("--sok")
    sok, args = args[i + 1:], args[:i]
verk, monster = args[0], args[1:]
cur = db._hamta_db().cursor()
cur.execute("SELECT id, adress, text FROM fornmed.passage WHERE verk_id = %s AND typ = 'originaltext' ORDER BY ordning",
            (verk,))
for pid, adress, text in cur.fetchall():
    if monster and not any(re.search(m, adress or "") for m in monster):
        continue
    cur.execute("SELECT text FROM fornmed.passage WHERE id = %s", (pid + ":sv",))
    r = cur.fetchone()
    oversattning = r[0] if r else ""
    if sok and not any(re.search(o, oversattning, re.I) for o in sok):
        continue
    print(f"### {pid}  [{adress}]\n{text}")
    if sv:
        print(f"--- sv (maskinöversättning, får inte citeras): {oversattning}")
    print()

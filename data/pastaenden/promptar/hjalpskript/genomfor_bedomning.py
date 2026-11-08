"""För in bedömningarna av hela lagmaterialet i data/pastaenden/lagar/ och skriv en logg."""
import glob
import json
import re
import shutil
from pathlib import Path

ROT = Path("<projektmapp>")
OE = ROT / "oberoende_extraktion"
SCR = Path(__file__).parent
DELAR = [f"{i:02d}" for i in range(1, 10)]
# Personkopplingen i Alsnö stadga är avsiktlig (stadgan utfärdades av Magnus Ladulås)
HOPPA = {("01", 214)}
# A_fel där bara mottagaren arv var fel: mottagaren blir arvinge
ARVINGE = {("03", 64), ("04", 32), ("07", 22), ("07", 151), ("09", 1), ("03", 139)}

backup = SCR / "backup_lagar_fore_hela_kontrollen"
if not backup.exists():
    shutil.copytree(ROT / "data/pastaenden/lagar", backup)
filer = {f: json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(str(ROT / "data/pastaenden/lagar/*.json")))}


def hitta(rad):
    for f, d in filer.items():
        for i, p in enumerate(d["pastaenden"]):
            if p == rad:
                return f, i
    return None, None


def fil_for(pid):
    for f, d in filer.items():
        if any(p[0] == pid for p in d["pastaenden"]):
            return f
    pre = pid.rsplit(":", 1)[0]
    for f, d in filer.items():
        if any(p[0].rsplit(":", 1)[0] == pre for p in d["pastaenden"]):
            return f
    raise KeyError(pid)


def varde(obj):
    return obj[1:] if obj.startswith("=") else (obj.split("|", 1)[1] if "|" in obj else "")


logg = ["# Genomförda ändringar efter den oberoende kontrollen av hela lagmaterialet", "",
        "| del | id | beslut | lag | passage | före | efter |", "|---|---|---|---|---|---|---|"]
ta_bort, ersatt, lagg_till, ej = [], {}, [], []
kort = lambda r: "–" if not r else f"{r[1]} · {r[2]} · {r[3]}".replace("|", "/")
for n in DELAR:
    sk = {x["id"]: x for x in json.load(open(OE / f"jamforelse_lagar_hela/jamforelse_del_{n}.json", encoding="utf-8"))}
    for b in json.load(open(OE / f"jamforelse_lagar_hela/bedomning_del_{n}.json", encoding="utf-8")):
        if b["beslut"] not in ("A_fel", "A_utanfor", "B_lagg_till") or (n, b["id"]) in HOPPA:
            continue
        s = sk[b["id"]]
        ny = b.get("ny_rad")
        if b["beslut"] == "B_lagg_till":
            ny = list(ny)
            if ny[3].startswith("begrepp:arv|"):
                ny[3] = "begrepp:arvinge|" + ny[3].split("|", 1)[1]
            lagg_till.append((n, b["id"], ny))
            logg.append(f"| {n} | {b['id']} | lägg till | {Path(fil_for(ny[0])).stem} | {ny[0].split(':')[-1]} | – | {kort(ny)} |")
            continue
        gammal = s.get("rad") or s.get("A")
        f, i = hitta(gammal)
        if f is None:
            ej.append((n, b["id"], gammal))
            continue
        if b["beslut"] == "A_utanfor" or ny is None:
            ta_bort.append((f, i))
            logg.append(f"| {n} | {b['id']} | {'utanför' if b['beslut'] == 'A_utanfor' else 'ta bort'} | {Path(f).stem} | {gammal[0].split(':')[-1]} | {kort(gammal)} | – |")
        else:
            ny = list(ny)
            if (n, b["id"]) in ARVINGE:
                ny[3] = "begrepp:arvinge|" + varde(ny[3])
            ersatt[(f, i)] = ny
            logg.append(f"| {n} | {b['id']} | rätta | {Path(f).stem} | {gammal[0].split(':')[-1]} | {kort(gammal)} | {kort(ny)} |")

for (f, i), ny in ersatt.items():
    filer[f]["pastaenden"][i] = ny
for f, i in sorted(ta_bort, reverse=True):
    filer[f]["pastaenden"][i] = None
for f in filer:
    filer[f]["pastaenden"] = [p for p in filer[f]["pastaenden"] if p is not None]
for n, id_, ny in lagg_till:
    f = fil_for(ny[0])
    d = filer[f]["pastaenden"]
    idx = max([k for k, q in enumerate(d) if q[0] == ny[0]], default=len(d) - 1)
    d.insert(idx + 1, ny)
# Kvarvarande arv som mottagare betyder arvingarna
for d in filer.values():
    for p in d["pastaenden"]:
        if p[3].startswith("begrepp:arv|") or p[3] == "begrepp:arv":
            p[3] = "begrepp:arvinge" + p[3][len("begrepp:arv"):]
for f, d in filer.items():
    Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
logg[1:1] = [f"Tillagda {len(lagg_till)}, rättade {len(ersatt)}, borttagna {len(ta_bort)}. "
             "Personkopplingen till Magnus Ladulås i Alsnö stadga står kvar. `begrepp:arv` som mottagare "
             "är ersatt med det nya begreppet `begrepp:arvinge`.", ""]
(OE / "jamforelse_lagar_hela/genomforda_andringar.md").write_text("\n".join(logg) + "\n", encoding="utf-8")
print(f"lägg till {len(lagg_till)}, rätta {len(ersatt)}, ta bort {len(ta_bort)}, ej funna {len(ej)}")
for e in ej:
    print("EJ FUNNEN", e)
print(sum(len(d["pastaenden"]) for d in filer.values()), "påståenden")

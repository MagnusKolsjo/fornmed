"""Visar vilka delar som har fullständiga svar, och vilka som saknas eller är ofullständiga."""
import json, sys
from pathlib import Path
klara, fel, saknas = [], [], []
for d in sorted(Path("delar").glob("del_*")):
    s = Path("svar") / f"{d.name}.jsonl"
    if not s.exists():
        saknas.append(d.name[4:]); continue
    a = [json.loads(l)["id"] for l in d.open(encoding="utf-8")]
    try:
        b = [json.loads(l)["id"] for l in s.open(encoding="utf-8") if l.strip()]
    except Exception:
        b = []
    (klara if set(a) == set(b) else fel).append(d.name[4:])
print("klara", len(klara), "| ofullständiga", fel, "| ej påbörjade/svar saknas", ",".join(saknas))

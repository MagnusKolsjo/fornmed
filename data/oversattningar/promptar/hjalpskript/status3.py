"""Visar vilka jobb från 133 som är klara (kontrollen ger OK) och vilka som återstår."""
import json, subprocess, sys
S = sys.argv[1]; PY = sys.argv[2]
u = json.load(open(f"{S}/uppdrag_fornsvenska_3.json"))
klara, kvar = [], []
for nr, jobb in enumerate(u, 133):
    ok = all(subprocess.run([PY, f"{S}/kontrollera_oversattning.py", j["fil"], j["verk"], str(j["fran"]), str(j["till"])],
                            capture_output=True, text=True).stdout.startswith("OK") for j in jobb)
    (klara if ok else kvar).append(nr)
print("klara:", klara); print("kvar:", kvar)

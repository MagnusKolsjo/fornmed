"""
Samlar språkmodellens bedömningar (data/sprak/omgang/svar) till data/sprak/dn_sprak_modell.tsv.

Varje svar jämförs med klassarens bedömning i data/sprak/dn_sprak.tsv: "huvud" när modellen
valt klassarens huvudspråk, "andra" när den valt klassarens näst vanligaste språk, annars
"inget". Bland kontrollbreven var svaren rätt i 83 av 84 fall när modellen och klassaren
var överens, men bara i 2 av 16 när de var oense.

Där de var oense har en starkare modell bedömt brevet en gång till (data/sprak/omgang2).
Brevet får språk när två av de tre bedömningarna är överens; det står i kolumnen beslut.

Användning:
    python sprak_samla.py                    # Diplomatarium Norvegicum
    python sprak_samla.py --kallsamling di   # Diplomatarium Islandicum
"""

import argparse
import csv
import glob
import json
from pathlib import Path

KATALOG = Path(__file__).parent / "data" / "sprak"


def stammer(klass: str | None, svar: str) -> bool:
    return bool(klass) and klass in svar.split("-")


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--kallsamling", default="dn", help="dn eller di")
    k_ = tolk.parse_args().kallsamling
    forsta, andra_omgang = ("omgang", "omgang2") if k_ == "dn" else (f"{k_}_omgang", f"{k_}_omgang2")
    klassning = {r["verk_id"]: r for r in csv.DictReader((KATALOG / f"{k_}_sprak.tsv").open(encoding="utf-8"), delimiter="\t")}
    svar = {}
    for fil in sorted(glob.glob(str(KATALOG / forsta / "svar" / "del_*.jsonl"))):
        for rad in open(fil, encoding="utf-8"):
            if rad.strip():
                r = json.loads(rad)
                svar[r["id"]] = r
    andra = {}
    for fil in sorted(glob.glob(str(KATALOG / andra_omgang / "svar" / "del_*.jsonl"))):
        for rad in open(fil, encoding="utf-8"):
            if rad.strip():
                r = json.loads(rad)
                andra[r["id"]] = r
    with (KATALOG / f"{k_}_sprak_modell.tsv").open("w", encoding="utf-8", newline="") as f:
        skrivare = csv.writer(f, delimiter="\t", lineterminator="\n")
        skrivare.writerow(["verk_id", "sprak", "sakerhet", "overens", "motivering", "sprak2", "motivering2", "beslut"])
        for verk_id, r in sorted(svar.items()):
            k = klassning.get(verk_id, {})
            andelar = [x.split(":")[0] for x in k.get("andelar", "").split()]
            overens = ("huvud" if stammer(k.get("sprak"), r["sprak"])
                       else "andra" if len(andelar) > 1 and stammer(andelar[1], r["sprak"]) else "inget")
            r2 = andra.get(verk_id, {})
            beslut = r["sprak"] if overens == "huvud" else ""
            if r2 and not beslut and r2["sprak"] not in ("annat",):
                if r2["sprak"] == r["sprak"] or stammer(k.get("sprak"), r2["sprak"]):
                    beslut = r2["sprak"]
            skrivare.writerow([verk_id, r["sprak"], r["sakerhet"], overens, r["motivering"],
                               r2.get("sprak", ""), r2.get("motivering", ""), beslut])
    print(len(svar), "svar")


if __name__ == "__main__":
    main()

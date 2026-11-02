"""
Delar upp hela lagmaterialet i paket för en oberoende kontrollextraktion.

    DATABASE_URL=... python oberoende_extraktion/bygg_hela_lagar.py

Paketen omfattar varje flock som har påståenden i data/pastaenden/lagar/,
och grannflockarna utan påståenden, så att även missade regler syns.
Stickprovets flockar är redan jämförda och tas inte med. Flockarna delas i
lagordning upp i delar om högst MAX_TECKEN tecken text.

Varje del blir en egen mapp lagar_hela/del_NN/ med indata, instruktion och
kontrollskript. AGENTS.md i lagar_hela/ låter en kodagent som Codex arbeta
sig igenom alla delar i en körning; delarna kan också lämnas ut en i taget. Våra
påståenden för samma flockar skrivs till jamforelse_lagar_hela/A_del_NN.json,
som inte ska lämnas ut. Finns paketen redan avbryts skriptet, eftersom
indelningen beror på lagfilerna; --skriv-over tvingar.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

UT = Path(__file__).resolve().parent
sys.path.insert(0, str(UT.parent))
sys.path.insert(0, str(UT))
import db  # noqa: E402
from bygg_stickprov_lagar import kandidater_och_predikat  # noqa: E402
from jamfor_lagar import LAGAR  # noqa: E402

MAX_TECKEN = 120_000
MIN_GRANNE = 50       # rubrikrader och tomma stycken är inte värda att skicka


def main() -> None:
    paket, facit = UT / "lagar_hela", UT / "jamforelse_lagar_hela"
    if paket.exists() and "--skriv-over" not in sys.argv:
        sys.exit("Paketen finns redan; kör med --skriv-over för att dela upp om dem.")
    cur = db._hamta_db().cursor()
    filer = {fil: json.loads((UT.parent / "data/pastaenden/lagar" / f"{fil}.json").read_text(encoding="utf-8"))
             for fil, _, _ in LAGAR}
    stickprov = set(json.loads((UT / "lagar" / "indata_lagar_stickprov.json").read_text(encoding="utf-8"))["passager"])
    kort = {fil: k for fil, k, _ in LAGAR}

    flockar = []                  # (fil, passage-id, adress, text, typ, plats) i lagordning
    for fil, _, _ in LAGAR:
        egna = {p[0]: p[4] for p in filer[fil]["pastaenden"]}
        cur.execute("SELECT DISTINCT verk_id, typ FROM fornmed.passage WHERE id = ANY(%s)", (list(egna),))
        for verk, typ in sorted(cur.fetchall()):
            cur.execute("SELECT id, ordning, adress, text FROM fornmed.passage WHERE verk_id = %s AND typ = %s "
                        "ORDER BY ordning", (verk, typ))
            rader = cur.fetchall()
            plats = next(iter(egna.values()))
            for i, (pid, _, adress, text) in enumerate(rader):
                granne = pid not in egna and any(r[0] in egna for r in rader[max(i - 1, 0):i + 2])
                if (pid in egna or (granne and len(text) >= MIN_GRANNE)) and pid not in stickprov:
                    flockar.append((fil, pid, adress, text, typ, egna.get(pid, plats)))

    delar, aktuell, tecken = [], [], 0
    for f in flockar:
        if aktuell and tecken + len(f[3]) > MAX_TECKEN:
            delar.append(aktuell)
            aktuell, tecken = [], 0
        aktuell.append(f)
        tecken += len(f[3])
    delar.append(aktuell)

    kandidater, predikat = kandidater_och_predikat(cur, filer, {f[5] for f in flockar})
    mall = (UT / "PROMPT_mall_lagar.md").read_text(encoding="utf-8")
    shutil.rmtree(paket, ignore_errors=True)
    shutil.rmtree(facit, ignore_errors=True)
    facit.mkdir()
    agents = (UT / "AGENTS_mall_lagar.md").read_text(encoding="utf-8")
    agents = agents.replace("{delar}", str(len(delar))).replace("{sista}", f"{len(delar):02d}")
    paket.mkdir()
    (paket / "AGENTS.md").write_text(agents, encoding="utf-8")
    (paket / "STATUS.md").write_text("# Status\n\n", encoding="utf-8")
    for nr, del_ in enumerate(delar, 1):
        namn = f"del_{nr:02d}"
        mapp = paket / namn
        mapp.mkdir()
        lagar = list(dict.fromkeys(kort[f[0]] for f in del_))
        indata = {"kalla": f"Del {nr} av {len(delar)} av de medeltida nordiska lagarna: {', '.join(lagar)}. "
                           "Fornsvensk text efter Schlyters utgåvor via svenska Wikisource och Fornsvenska "
                           "textbanken; Grágás i Finsens danska översättning.",
                  "passager": {f[1]: {"lag": kort[f[0]], "adress": f[2], "plats": f[5],
                                      "sprak": "danska (översättning)" if f[4] == "oversattning" else "fornsvenska",
                                      "text": f[3]} for f in del_},
                  "kandidater": kandidater, "predikat": predikat}
        (mapp / f"indata_{namn}.json").write_text(json.dumps(indata, ensure_ascii=False, indent=1), encoding="utf-8")
        text = mall
        for nyckel, varde in (("{antal}", str(len(del_))), ("{lagar}", ", ".join(lagar)), ("{del}", str(nr)),
                              ("{delar}", str(len(delar))), ("{indata}", f"indata_{namn}.json"),
                              ("{utdata}", f"utdata_{namn}.json")):
            text = text.replace(nyckel, varde)
        (mapp / "PROMPT.md").write_text(text, encoding="utf-8")
        shutil.copy(UT / "lagar" / "kontrollera.py", mapp / "kontrollera.py")

        ids = {f[1] for f in del_}
        vara = [p for fil, _, _ in LAGAR for p in filer[fil]["pastaenden"] if p[0] in ids]
        (facit / f"A_{namn}.json").write_text(json.dumps(
            {"beskrivning": f"Våra påståenden för {namn}, ur data/pastaenden/lagar/.",
             "extraherad_av": "språkmodell (Claude Opus 5.5)", "passager": {}, "entiteter": [],
             "identifieringar": [], "pastaenden": vara}, ensure_ascii=False, indent=1), encoding="utf-8")
        grannar = sum(1 for f in del_ if not any(p[0] == f[1] for p in vara))
        print(f"{namn}: {len(del_):3} flockar ({grannar:2} grannar), {sum(len(f[3]) for f in del_):6} tecken, "
              f"{len(vara):3} påståenden — {', '.join(lagar)}")


if __name__ == "__main__":
    main()

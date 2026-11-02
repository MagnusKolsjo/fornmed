"""
Ställer upp normpåståendena ur landskapslagarna i en jämförande tabell per
ämne och lag.

Läser filerna i data/pastaenden/lagar/ och skriver en markdownrapport där
varje rad är ett påstående (brott, påföljd, bötesdelning, forum, bevis, jäv)
och lagarna står i ungefärlig tidsordning inom sina landsdelar, så att
skillnader mellan Götaland, Svealand, Gotland och Skåne och förändringar
fram till landslagen syns direkt.

    .venv/bin/python jamfor_lagar.py rapport/jamforelse_lagar.md
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import db

KATALOG = Path(__file__).parent / "data" / "pastaenden" / "lagar"

# (fil, kort namn, landsdel) i ungefärlig tidsordning inom landsdelen
LAGAR = [
    ("hednalagen", "Hednalagen", "Götaland"),
    ("aldre_vastgotalagen", "ÄVgL", "Götaland"),
    ("vidhemsprastens_anteckningar", "Vidhemsprästen", "Götaland"),
    ("lydekini", "YVgL fragm./Lydekini", "Götaland"),
    ("yngre_vastgotalagen", "YVgL", "Götaland"),
    ("ostgotalagen", "ÖgL", "Götaland"),
    ("ostgotalagen_fragment", "ÖgL fragm.", "Götaland"),
    ("smalandslagens_kyrkobalk", "SmL Kkb", "Götaland"),
    ("upplandslagen", "UL (hskr A)", "Svealand"),
    ("upplandslagen_hskr_b", "UL (hskr B)", "Svealand"),
    ("upplandslagen_tillagg", "UL tillägg", "Svealand"),
    ("sodermannalagen", "SdmL", "Svealand"),
    ("dalalagen", "DL", "Svealand"),
    ("yngre_vastmannalagen", "VmL", "Svealand"),
    ("halsingelagen", "HL", "Norrland"),
    ("gutalagen", "GL", "Gotland"),
    ("gutalagens_additamenta", "GL add.", "Gotland"),
    ("skanelagen", "SkL", "Skåne"),
    ("bjarkoaratten", "BjR", "Städerna"),
    ("magnus_erikssons_stadslag", "MESt", "Städerna"),
    ("magnus_erikssons_landslag", "MEL", "Riket"),
    ("kristoffers_landslag", "KrL", "Riket"),
    ("gragas", "Grágás", "Island"),
]

# Ämne -> (predikat, subjekt eller None för alla)
AMNEN = {
    "Dråp och ogilt dödande": [("definieras_som", {"begrepp:drap", "begrepp:vadadrap", "begrepp:nidingsverk"}),
                               ("paforljd", {"begrepp:drap", "begrepp:vadadrap", "begrepp:mord"}),
                               ("tillfaller", {"begrepp:mansbot", "begrepp:attebot", "begrepp:sakore", "begrepp:boter"}),
                               ("handlaggs_vid", {"begrepp:drap", "begrepp:vadadrap"}),
                               ("kraver", {"begrepp:drap", "begrepp:vadadrap"})],
    "Edsöre": [("definieras_som", {"begrepp:edsore"}),
               ("paforljd", {"begrepp:edsore", "begrepp:hemsokn", "begrepp:valdtakt"}),
               ("tillfaller", {"begrepp:fredloshet", "begrepp:gods"}),
               ("handlaggs_vid", {"begrepp:edsore", "begrepp:hemsokn", "begrepp:valdtakt"}),
               ("kraver", {"begrepp:edsore", "begrepp:hemsokn", "begrepp:valdtakt"})],
    "Jäv, oväld och nämnd": [("diskvalificerar", None), ("utses_av", None),
                             ("definieras_som", {"begrepp:jav", "begrepp:ovald", "begrepp:muta"}),
                             ("kraver", {"begrepp:namnd", "begrepp:domare", "begrepp:ovald"})],
    "Konungaval och lagstiftning": [("utses_av", {"begrepp:kung", "begrepp:lagman"}),
                                    ("kraver", {"begrepp:konungaval", "begrepp:eriksgata"}),
                                    ("stiftar_lag", None)],
}


def las_filer() -> dict[str, list[list]]:
    ut = {}
    for fil, _, _ in LAGAR:
        sokvag = KATALOG / f"{fil}.json"
        if sokvag.exists():
            ut[fil] = json.loads(sokvag.read_text(encoding="utf-8"))["pastaenden"]
    return ut


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    filer = las_filer()
    cur = db._hamta_db().cursor()
    cur.execute(f"SELECT id, namn FROM {db._prefix()}entitet WHERE id LIKE 'begrepp:%' OR id LIKE 'person:%'")
    namn = dict(cur.fetchall())
    n = lambda eid: namn.get(eid, eid)

    def objekt(o: str) -> str:
        if o.startswith("="):
            return o[1:]
        if "|" in o:
            eid, varde = o.split("|", 1)
            return f"{n(eid)}: {varde}"
        return n(o)

    rader = ["# Jämförelse mellan lagarna: dråp, edsöre och jäv", "",
             "Påståenden ur data/pastaenden/lagar/, extraherade av språkmodell och ogranskade. "
             "Varje rad hänvisar till passagen; citaten finns i filerna och i databasen. "
             "Grágás citeras efter dansk översättning.", "",
             "| lag | påståenden |", "|---|---|"]
    rader += [f"| {kort} ({landsdel}) | {len(filer.get(fil, []))} |" for fil, kort, landsdel in LAGAR]
    for amne, urval in AMNEN.items():
        rader += ["", f"## {amne}", ""]
        for predikat, subjekt in urval:
            traffar = defaultdict(list)
            for fil, _, _ in LAGAR:
                for p in filer.get(fil, []):
                    if p[2] == predikat and (subjekt is None or p[1] in subjekt):
                        traffar[fil].append(p)
            if not traffar:
                continue
            rader += [f"### {predikat}", "", "| lag | subjekt | objekt | anmärkning | passage |", "|---|---|---|---|---|"]
            for fil, kort, landsdel in LAGAR:
                for p in traffar.get(fil, []):
                    anm = p[6] if len(p) > 6 and p[6] else ""
                    rader.append(f"| {kort} | {n(p[1])} | {objekt(p[3])} | {anm} | {p[0].split(':', 2)[-1]} |")
            rader.append("")
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_text("\n".join(rader) + "\n", encoding="utf-8")
    print(f"{sum(len(v) for v in filer.values())} påståenden ur {len(filer)} lagar")


if __name__ == "__main__":
    main()

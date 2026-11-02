"""
Väljer ett stratifierat stickprov av flockar ur lagpåståendena och bygger
indata för en oberoende kontrollextraktion.

    DATABASE_URL=... python oberoende_extraktion/bygg_stickprov_lagar.py

Varje lag får en kvot efter hur många påståenden den har. Inom lagen väljs
flockar så att ämnena (dråp, edsöre, jäv och lagstiftning) täcks, och
flockar som normaliseringen pekat ut som osäkra tas alltid med. Några
flockar utan påståenden, granne med en vald flock, tas med för att pröva om
vår extraktion missat något. Urvalet är deterministiskt.

Skriver lagar/indata_lagar_stickprov.json, som lämnas till den andra
modellen, och jamforelse_lagar/A_stickprov.json med våra påståenden för
samma flockar. Den senare ska inte lämnas ut. Finns indata redan avbryts
skriptet, eftersom urvalet beror på lagfilerna och en ny körning ger andra
grannflockar än de den andra modellen redan extraherat; --skriv-over tvingar.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))
import db  # noqa: E402
from jamfor_lagar import LAGAR  # noqa: E402

UT = Path(__file__).resolve().parent
KVOT = {"hednalagen": 1, "aldre_vastgotalagen": 3, "vidhemsprastens_anteckningar": 1, "lydekini": 1,
        "yngre_vastgotalagen": 3, "ostgotalagen": 4, "ostgotalagen_fragment": 2, "smalandslagens_kyrkobalk": 1,
        "upplandslagen": 3, "upplandslagen_hskr_b": 2, "upplandslagen_tillagg": 1, "sodermannalagen": 3,
        "dalalagen": 2, "yngre_vastmannalagen": 2, "halsingelagen": 2, "gutalagen": 2,
        "gutalagens_additamenta": 1, "skanelagen": 2, "bjarkoaratten": 1, "magnus_erikssons_stadslag": 2,
        "magnus_erikssons_landslag": 4, "kristoffers_landslag": 4, "gragas": 2}
# Flockar som normaliseringen markerade som osäkra, och Alsnö stadga i Vidhemsprästens
# anteckningar (domarregeln i vidhemspr_4 är för lång för stickprovet)
ALLTID_MED = ["lag:aldre_vastgotalagen:avgl_md_13", "lag:yngre_vastgotalagen_enligt_holm_b_58:yvgl_db_24",
              "lag:magnus_erikssons_landslag:mel_dmv_22",
              "lag:upplandslagen_enl_schlyters_utgava_och_codex_ups_c_12_hskr_a:ul_kgb_11",
              "lag:vidhemsprastens_anteckningar:vidhemspr_2"]
ANTAL_TOMMA = 4
MAXLANGD = {"gragas": 4500, "hednalagen": 4000, "smalandslagens_kyrkobalk": 4000,
            "gutalagens_additamenta": 4000, "bjarkoaratten": 4000, "vidhemsprastens_anteckningar": 4500}

DRAP = {"begrepp:drap", "begrepp:vadadrap", "begrepp:mord", "begrepp:mansbot", "begrepp:dulgadrap",
        "begrepp:radsbane", "begrepp:hallbane", "begrepp:asyna_man", "begrepp:forsat", "begrepp:attebot"}
EDSORE = {"begrepp:edsore", "begrepp:hemsokn", "begrepp:valdtakt", "begrepp:fridsbrott",
          "begrepp:forverkat_gods", "begrepp:fredloshet", "begrepp:orbotamal"}


def amne(p: list) -> str:
    if p[2] in ("diskvalificerar", "utses_av") or p[1] in ("begrepp:jav", "begrepp:ovald", "begrepp:muta"):
        return "jav"
    if p[2] == "stiftar_lag" or p[1] in ("begrepp:konungaval", "begrepp:eriksgata"):
        return "lag"
    if p[1] in EDSORE:
        return "edsore"
    if p[1] in DRAP:
        return "drap"
    return "ovrigt"


def kandidater_och_predikat(cur, filer: dict, platsid: set) -> tuple[dict, list]:
    """Begrepp, personer bakom lagarna, platser och normpredikat, som den andra modellen får välja bland."""
    cur.execute("SELECT id, namn, beskrivning FROM fornmed.entitet WHERE id LIKE 'begrepp:%' ORDER BY id")
    begrepp = [{"id": i, "namn": n, "beskrivning": b} for i, n, b in cur.fetchall()]
    personer_id = sorted({p[1] for d in filer.values() for p in d["pastaenden"] if p[1].startswith("person:")})
    cur.execute("SELECT id, namn, beskrivning FROM fornmed.entitet WHERE id = ANY(%s) ORDER BY id", (personer_id,))
    personer = [{"id": i, "namn": n, "beskrivning": b} for i, n, b in cur.fetchall()]
    cur.execute("SELECT id, namn FROM fornmed.entitet WHERE id = ANY(%s) ORDER BY id", (sorted(platsid),))
    platser = [{"id": i, "namn": n} for i, n in cur.fetchall()]
    predikat_koder = ["paforljd", "tillfaller", "handlaggs_vid", "kraver", "diskvalificerar", "utses_av",
                      "definieras_som", "stiftar_lag"]
    cur.execute("SELECT kod, etikett, beskrivning FROM fornmed.vokabular WHERE schema = 'predikat' AND kod = ANY(%s)",
                (predikat_koder,))
    predikat = sorted(({"kod": k, "betydelse": b, "anm": a} for k, b, a in cur.fetchall()),
                      key=lambda p: predikat_koder.index(p["kod"]))

    return {"begrepp": begrepp, "personer": personer, "platser": platser}, predikat


def main() -> None:
    if (UT / "lagar" / "indata_lagar_stickprov.json").exists() and "--skriv-over" not in sys.argv:
        sys.exit("Stickprovet finns redan; kör med --skriv-over för att välja om det.")
    cur = db._hamta_db().cursor()
    slump = random.Random(1285)
    filer = {fil: json.loads((ROT / "data/pastaenden/lagar" / f"{fil}.json").read_text(encoding="utf-8"))
             for fil, _, _ in LAGAR}
    valda: dict[str, str] = {}      # passage -> fil
    plats: dict[str, str] = {}
    for fil, _, _ in LAGAR:
        per_passage: dict[str, list] = {}
        for p in filer[fil]["pastaenden"]:
            per_passage.setdefault(p[0], []).append(p)
            plats[p[0]] = p[4]
        cur.execute("SELECT id, length(text) FROM fornmed.passage WHERE id = ANY(%s)", (list(per_passage),))
        langd = dict(cur.fetchall())
        tak = MAXLANGD.get(fil, 3000)
        kandidater = [pid for pid in per_passage if langd.get(pid, 10**6) <= tak]
        egna = [pid for pid in ALLTID_MED if pid in per_passage]
        for pid in egna:
            valda[pid] = fil
        kvot = max(KVOT[fil] - len(egna), 0)
        # Täck ämnena i tur och ordning; inom ämnet väljs slumpvis bland flockar med minst två påståenden
        slump.shuffle(kandidater)
        kandidater.sort(key=lambda pid: len(per_passage[pid]) < 2)
        tackta = {amne(p) for pid in egna for p in per_passage[pid]}
        for _ in range(kvot):
            val = next((pid for pid in kandidater if pid not in valda
                        and {amne(p) for p in per_passage[pid]} - tackta - {"ovrigt"}), None)
            val = val or next((pid for pid in kandidater if pid not in valda), None)
            if not val:
                break
            valda[val] = fil
            tackta |= {amne(p) for p in per_passage[val]}

    # Grannflockar utan påståenden
    alla = {p[0] for d in filer.values() for p in d["pastaenden"]}
    tomma = []
    for pid in sorted(valda, key=lambda x: slump.random()):
        cur.execute("""SELECT g.id, length(g.text) FROM fornmed.passage v
                       JOIN fornmed.passage g ON g.verk_id = v.verk_id AND g.typ = v.typ
                        AND abs(g.ordning - v.ordning) = 1
                       WHERE v.id = %s ORDER BY g.ordning""", (pid,))
        for gid, lg in cur.fetchall():
            if gid not in alla and gid not in valda and lg <= 2500 and valda[pid] not in {f for _, f in tomma}:
                tomma.append((gid, valda[pid]))
                plats[gid] = plats[pid]
                break
        if len(tomma) == ANTAL_TOMMA:
            break
    for gid, fil in tomma:
        valda[gid] = fil

    ordning = {fil: i for i, (fil, _, _) in enumerate(LAGAR)}
    passager = {}
    for pid in sorted(valda, key=lambda x: (ordning[valda[x]], x)):
        cur.execute("SELECT adress, text, typ FROM fornmed.passage WHERE id = %s", (pid,))
        adress, text, typ = cur.fetchone()
        kort = dict((f, k) for f, k, _ in LAGAR)[valda[pid]]
        passager[pid] = {"lag": kort, "adress": adress, "plats": plats[pid],
                         "sprak": "danska (översättning)" if typ == "oversattning" else "fornsvenska",
                         "text": text}

    kandidater, predikat = kandidater_och_predikat(cur, filer, set(plats.values()))

    indata = {"kalla": "Stratifierat stickprov av flockar ur de medeltida svenska lagarna, Bjärköarätten, "
                       "Magnus Erikssons stads- och landslag, Kristoffers landslag och Grágás (dansk översättning). "
                       "Fornsvensk text efter Schlyters utgåvor via svenska Wikisource och Fornsvenska textbanken.",
              "passager": passager,
              "kandidater": kandidater,
              "predikat": predikat}
    (UT / "lagar").mkdir(exist_ok=True)
    (UT / "lagar" / "indata_lagar_stickprov.json").write_text(
        json.dumps(indata, ensure_ascii=False, indent=1), encoding="utf-8")

    vara = [p for fil, _, _ in LAGAR for p in filer[fil]["pastaenden"] if p[0] in valda]
    (UT / "jamforelse_lagar").mkdir(exist_ok=True)
    (UT / "jamforelse_lagar" / "A_stickprov.json").write_text(json.dumps(
        {"beskrivning": "Våra påståenden för stickprovets flockar, ur data/pastaenden/lagar/.",
         "extraherad_av": "språkmodell (Claude Opus 5.5)", "passager": {},
         "entiteter": [],
         "identifieringar": [], "pastaenden": vara}, ensure_ascii=False, indent=1), encoding="utf-8")

    tecken = sum(len(p["text"]) for p in passager.values())
    print(f"{len(passager)} flockar ({len(tomma)} utan påståenden), {tecken} tecken, {len(vara)} av våra påståenden")
    for pid, p in passager.items():
        n = sum(1 for x in vara if x[0] == pid)
        print(f"  {p['lag']:22} {pid:55} {len(p['text']):5} tkn {n:3} påst.")


if __name__ == "__main__":
    main()

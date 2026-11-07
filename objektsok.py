"""
Sökning efter dokument och entiteter, med filter och fasetter.

Passagesökningen i sok.py hittar textställen. Här samlas träffarna per verk
och kompletteras med entiteter och verk vars namn eller titel matchar frågan.
Varje träff redovisas med typ, tider och platser ur sökindexet (sokindex.py),
så att en lista, en karta och en tidslinje kan visa samma resultat.

Utan fråga listas de objekt som filtren avgränsar, i tidsordning. Det är
så kartan och tidslinjen kan visa ett område eller en period utan sökord.

Fasetterna räknas bland alla kandidater för en fråga (de mest relevanta
passagernas verk och namnträffarna), och bland hela urvalet utan fråga.

Användning:
    python objektsok.py "Uppsala"
    python objektsok.py "kungen befriar ett kloster från skatt" --ar-fran 1300 --ar-till 1350
    python objektsok.py --plats plats:landskap:uppland --objekttyp verk --antal 5
"""

import argparse
import json
import re
from collections import Counter

import db
import sok
import stavning
from fragor import _rader, _sokform, _sprak

# Kandidater ur fulltext- och vektorsökningen. Fasetterna räknas bland alla
# kandidater, och ett filter kör om sökningen inom filtret; antalen stämmer
# därför bara om kandidaterna är alla träffar och inte de bästa av fler.
# Fulltextsökningen kräver här alla frågeord, så taket nås bara av mycket
# vanliga enskilda ord; svaret anger det i kapad.
FTS_KANDIDATER = 20000
# Vektorsökningen görs alltid i hela databasen och filtreras efteråt, så att
# ett filter ger en delmängd av samma semantiska träffar och inte nya grannar
VEKTOR_KANDIDATER = 100

# Lägsta cosinuslikhet för passager som bara vektorsökningen hittar, per
# embeddingmodell (roll i embeddings.MODELLER). Mätt med modellerna i
# config.example.env: frågor med kända relevanta svar ger 0,70–0,83 med den
# svenska modellen, medan ett ortnamn i en period där inget nämner orten ger
# 0,42–0,64. Den flerspråkiga modellen skiljer sämre (nästan allt ligger på
# 0,78–0,84), så där släpps bara de tydligaste igenom. Byts en modell måste
# gränserna mätas om.
MINSTA_LIKHET = {"svenska": 0.70, "flersprak": 0.83}

# Namnträffar som tas med bland kandidaterna
NAMNKANDIDATER = 5000

# Platser per träff i svaret; resten räknas i antal_platser
MAX_PLATSER_PER_TRAFF = 20

FASETT_MAX = 30

# Platser på kartan; fler blir oläsligt och tungt att skicka
KARTPUNKTER_MAX = 2000


def _ar(varde: int | None) -> int | None:
    """År ur datumheltalet ÅÅÅÅMMDD. Avrundas mot noll, så att -500101 blir år -50."""
    return None if varde is None else int(varde / 10000)


def _tidsspann(edtf: str | None, fran: int | None, till: int | None, **extra) -> dict | None:
    if fran is None and till is None and edtf is None:
        return None
    return {"edtf": edtf, "fran": _ar(fran), "till": _ar(till), **extra}


def hamta_poster(ids: list[str]) -> dict[str, dict]:
    """Sökposterna med tider och platser, som de redovisas i träfflistan."""
    if not ids:
        return {}
    p, ph = db._prefix(), db._ph()
    lista = ", ".join([ph] * len(ids))
    poster: dict[str, dict] = {}
    for r in _rader(f"SELECT * FROM {p}sokpost WHERE id IN ({lista})", ids):
        poster[r["id"]] = {
            "id": r["id"], "objekttyp": r["objekttyp"], "undertyp": r["undertyp"],
            "kallsamling": r["kallsamling_id"], "rubrik": r["rubrik"], "sammanfattning": r["sammanfattning"],
            "sprak": _sprak(r["sprak"]),
            "tid": {
                "visas": None if r["tid_kalla"] is None else
                {"fran": _ar(r["tid_fran"]), "till": _ar(r["tid_till"]), "kalla": r["tid_kalla"]},
                "handelse": None if r["handelse_fran"] is None else
                {"fran": _ar(r["handelse_fran"]), "till": _ar(r["handelse_till"])},
                "tillkomst": _tidsspann(r["tillkomst_edtf"], r["tillkomst_fran"], r["tillkomst_till"]),
                "forlaga": _tidsspann(r["forlaga_edtf"], r["forlaga_fran"], r["forlaga_till"],
                                      vittnestyp=r["forlaga_typ"]),
            },
            "antal_pastaenden": r["antal_pastaenden"],
            "platser": [],
            "antal_platser": 0,
            "bedomningar": [],
        }
    # Forskningens bedömningar av verket och av dess vittnen (äkthet, datering),
    # med motivering. En bedömning av ett vittne, t.ex. en förfalskad avskrift,
    # anger vittnet, så att den inte läses som en bedömning av hela verket.
    for r in _rader(f"""SELECT coalesce(b.verk_id, w.verk_id) AS verk, b.aspekt, b.varde, b.sakerhet, b.bedomare,
                               b.publikation, b.sidor, b.ar, b.motivering, b.granskad,
                               w.typ AS vittnestyp, w.beskrivning AS vittne
                        FROM {p}bedomning b LEFT JOIN {p}vittne w ON w.id = b.vittne_id
                        WHERE b.verk_id IN ({lista}) OR w.verk_id IN ({lista})
                        ORDER BY 1, b.vittne_id NULLS FIRST, b.aspekt, b.id""", ids + ids):
        if r["verk"] in poster:
            poster[r["verk"]]["bedomningar"].append({**{k: r[k] for k in r if k != "verk"},
                                                     "granskad": bool(r["granskad"])})
    for r in _rader(
        f"""SELECT sp.sokpost_id, sp.plats_id, e.namn, sp.roll, sp.primar, sp.osaker, sp.antal,
                   u.nutida_namn, ls.namn AS landskap, la.namn AS land, u.latitud, u.longitud
            FROM {p}sokpost_plats sp JOIN {p}entitet e ON e.id = sp.plats_id
            LEFT JOIN {p}plats_uppgift u ON u.entitet_id = sp.plats_id
            LEFT JOIN {p}entitet ls ON ls.id = u.landskap_id
            LEFT JOIN {p}entitet la ON la.id = u.land_id
            WHERE sp.sokpost_id IN ({lista})
            ORDER BY sp.sokpost_id, sp.primar DESC, sp.antal DESC, e.namn""",
        ids,
    ):
        post = poster.get(r["sokpost_id"])
        if post is None:
            continue
        post["antal_platser"] += 1
        if len(post["platser"]) < MAX_PLATSER_PER_TRAFF:
            post["platser"].append({
                "plats_id": r["plats_id"], "namn": r["namn"], "roll": r["roll"], "primar": bool(r["primar"]),
                "osaker": bool(r["osaker"]), "antal": r["antal"], "nutida_namn": r["nutida_namn"],
                "landskap": r["landskap"], "land": r["land"], "latitud": r["latitud"], "longitud": r["longitud"],
            })
    return poster


def _namntraffar(fraga: str, filter_: sok.Filter) -> tuple[list[str], dict[str, int], list[str]]:
    """
    Sökposter vars rubrik eller namnform innehåller frågan: först exakta
    namn (grupp 0), sedan namn som börjar med frågan (1), sedan övriga (2),
    och inom varje grupp de som flest påståenden bygger på. Returnerar id i
    rangordning och varje träffs grupp.
    """
    monster = _sokform(fraga.strip())
    if len(monster) < 3:
        return [], {}, []
    p, ph = db._prefix(), db._ph()
    villkor, param = filter_.sokpost_villkor("s")
    villkor.insert(0, f"s.soknamn LIKE {ph}")
    param.insert(0, f"%{monster}%")
    rader = _rader(f"SELECT s.id, s.soknamn, s.antal_pastaenden FROM {p}sokpost s WHERE {' AND '.join(villkor)}",
                   param)
    # Utan exakt namn slås frågan också upp på liknande stavning (Anskar →
    # Ansgar, Magnus Erikson → Magnus Eriksson). De närmaste formerna räknas
    # som namn som börjar med frågan. Bara namn räknas, inte begreppens
    # termer: ledning ska inte tolkas som ledung (det sköter sok.expandera).
    ungefarliga: set[str] = set()
    tolkningar: list[str] = []
    # Tolkningen görs utan filtren, så att den blir densamma med och utan
    # dem; filtren avgör bara vilka av de tolkade posterna som kommer med
    namnindex = stavning.namnindex()
    if not namnindex.finns(fraga):
        lika = namnindex.liknande(fraga)
        if lika:
            basta = min(d for _, _, d in lika)
            narmaste = [(form, ids) for form, ids, d in lika if d == basta]
            kandidat_ids = sorted({i for _, ids in narmaste for i in ids})
            namnposter = {r["id"] for r in _rader(
                f"SELECT s.id FROM {p}sokpost s WHERE s.id IN ({', '.join([ph] * len(kandidat_ids))}) "
                f"AND (s.undertyp IS NULL OR s.undertyp <> 'begrepp')", kandidat_ids)}
            tolkningar = [form for form, ids in narmaste if namnposter & set(ids)]
            if namnposter:
                lista = sorted(namnposter)
                filtrerade = _rader(
                    f"SELECT s.id, s.soknamn, s.antal_pastaenden FROM {p}sokpost s "
                    f"WHERE s.id IN ({', '.join([ph] * len(lista))})"
                    + (f" AND {' AND '.join(villkor[1:])}" if len(villkor) > 1 else ""),
                    [*lista, *param[1:]])
                ungefarliga = {r["id"] for r in filtrerade}
                rader += [r for r in filtrerade if r["id"] not in {x["id"] for x in rader}]

    def rang(r: dict) -> tuple:
        namn = r["soknamn"].split(" | ")
        if r["id"] in ungefarliga:
            grupp = 1
        elif monster in namn:
            grupp = 0
        elif any(n.startswith(monster) for n in namn):
            grupp = 1
        else:
            grupp = 2
        return grupp, -r["antal_pastaenden"], r["id"]

    return ([r["id"] for r in sorted(rader, key=rang)[:NAMNKANDIDATER]], {r["id"]: rang(r)[0] for r in rader},
            tolkningar)


def _inom_filter(passage_ids: list[str], filter_: sok.Filter) -> set[str]:
    """De passager vars verk uppfyller filtret."""
    if not passage_ids:
        return set()
    p, ph = db._prefix(), db._ph()
    filter_sql, filter_param = filter_.sql("v")
    return {r["id"] for r in _rader(
        f"""SELECT pa.id FROM {p}passage pa JOIN {p}verk v ON v.id = pa.verk_id
            WHERE pa.id IN ({', '.join([ph] * len(passage_ids))}){filter_sql}""",
        [*passage_ids, *filter_param])}


def _texttraffar(fraga: str, filter_: sok.Filter, texttyper: str, expandera: bool,
                 namnformer: list[str] = ()) -> tuple[dict[str, tuple[str, float]], list, bool]:
    """
    Verken med textträff: verk_id → (bästa passage, poäng) i rangordning,
    expansionen och om fulltextsökningen nådde taket.

    Fulltext- och vektorsökningen vägs samman som i sok.hybridsok, men en
    passage som bara vektorsökningen hittat måste nå MINSTA_LIKHET. Vektor-
    sökningen lämnar annars alltid sina närmaste grannar, hur avlägsna de än
    är, och här räknas varje kandidat in i fasetterna, kartan och tidslinjen.
    """
    typer = sok.ALLA_TYPER if texttyper == "alla" else sok.MODERNA_TYPER
    expansion = sok.expandera(fraga, felstavning=True) if expandera else sok.Expansion()
    # Namnformer som en felstavad fråga tolkades som (Kalmr → Kalmar) söks
    # också i texterna, som ett namn som täcker hela frågan, om inte
    # registret redan har tolkat frågans ord
    if namnformer and not expansion.begrepp:
        expansion.begrepp.append({"ord": fraga, "begrepp_id": "namnform:" + "|".join(namnformer),
                                  "huvudterm": ", ".join(f.title() for f in namnformer), "definition": "",
                                  "termer": [(form, "swe") for form in namnformer], "stavning": True,
                                  "fras": True})
    fts = sok.fulltextsok(fraga, FTS_KANDIDATER, filter_, typer, expansion, alla_grupper=True)
    # Namn (personer, platser, institutioner) söks som namn. Den semantiska
    # sökningen får bara fackordens definitioner: en persons beskrivning
    # ("ärkebiskop av Hamburg-Bremen") skulle annars göra varje brev om en
    # abbot likt frågan "Ansgar". Består frågan bara av namn hoppas den
    # semantiska sökningen över helt.
    begrepp = [b for b in expansion.begrepp if b["begrepp_id"].startswith("begrepp:")]
    namnord = {o.lower() for b in expansion.begrepp if not b["begrepp_id"].startswith("begrepp:")
               for o in b["ord"].split()}
    ovriga_ord = [o for o in re.findall(r"\w+", fraga.lower()) if o not in sok.SMAORD and o not in namnord]
    vektorlistor = []
    if ovriga_ord:
        for roll in sok.embeddings.MODELLER:
            grans = MINSTA_LIKHET.get(roll, 0.0)
            vektorlistor.append([(pid, likhet) for pid, likhet in
                                 sok.vektorsok(fraga, VEKTOR_KANDIDATER, None, sok.Expansion(begrepp), roll, typer)
                                 if likhet >= grans])
    if filter_.aktivt():
        inom = _inom_filter([pid for lista in vektorlistor for pid, _ in lista], filter_)
        vektorlistor = [[(pid, likhet) for pid, likhet in lista if pid in inom] for lista in vektorlistor]
    poang = sok.vag_samman([fts, *vektorlistor], typer)
    rangordnade = sorted(poang.items(), key=lambda r: r[1], reverse=True)
    verk_av: dict[str, str] = {}
    p, ph = db._prefix(), db._ph()
    pids = [pid for pid, _ in rangordnade]
    for i in range(0, len(pids), 1000):
        del_ = pids[i:i + 1000]
        for r in _rader(f"SELECT id, verk_id FROM {p}passage WHERE id IN ({', '.join([ph] * len(del_))})", del_):
            verk_av[r["id"]] = r["verk_id"]
    basta: dict[str, tuple[str, float]] = {}
    for pid, poang_ in rangordnade:
        if pid in verk_av:
            basta.setdefault(verk_av[pid], (pid, round(poang_, 4)))
    return basta, expansion.som_dict(), len(fts) >= FTS_KANDIDATER


def _fasetter(urval_sql: str, urval_param: list, tidsaxel: str = "primar") -> dict:
    """
    Antal objekt per typ, källsamling, sekel, land och landskap i urvalet.
    urval_sql är en SELECT som ger sökposternas id.
    """
    p = db._prefix()

    def rakna(sql: str) -> list[dict]:
        return [{"varde": r["varde"], "namn": r.get("namn"), "antal": r["antal"]}
                for r in _rader(sql, urval_param) if r["varde"] is not None]

    fasetter = {}
    for namn, kolumn in (("objekttyp", "objekttyp"), ("undertyp", "undertyp")):
        fasetter[namn] = rakna(f"""SELECT {kolumn} AS varde, count(*) AS antal FROM {p}sokpost
                                   WHERE id IN ({urval_sql}) GROUP BY {kolumn} ORDER BY antal DESC
                                   LIMIT {FASETT_MAX}""")
    fasetter["kallsamling"] = rakna(f"""SELECT s.kallsamling_id AS varde, k.namn, count(*) AS antal
                                        FROM {p}sokpost s JOIN {p}kallsamling k ON k.id = s.kallsamling_id
                                        WHERE s.id IN ({urval_sql}) GROUP BY s.kallsamling_id, k.namn
                                        ORDER BY antal DESC LIMIT {FASETT_MAX}""")
    # Sekel och decennier (tidslinjen) räknas som årsfiltret: ett objekt räknas
    # i varje period som dess tidsspann överlappar, så att ett klick på en
    # period ger lika många träffar som stapeln visar. En runsten daterad
    # 725–1100 räknas därför i fem sekel.
    kolumn = sok.TIDSAXLAR[tidsaxel]
    sekel, decennier = Counter(), Counter()
    for r in _rader(f"""SELECT {kolumn}_fran AS fran, {kolumn}_till AS till FROM {p}sokpost
                        WHERE id IN ({urval_sql}) AND {kolumn}_fran IS NOT NULL""", urval_param):
        fran = _ar(r["fran"])
        till = _ar(r["till"]) if r["till"] is not None else fran
        for d in range(fran // 10 * 10, till // 10 * 10 + 1, 10):
            decennier[d] += 1
        for s in range(fran // 100 * 100, till // 100 * 100 + 1, 100):
            sekel[s] += 1
    fasetter["sekel"] = [{"varde": s, "namn": None, "antal": n} for s, n in sorted(sekel.items())]
    fasetter["decennium"] = [{"varde": d, "namn": None, "antal": n} for d, n in sorted(decennier.items())]
    for namn, slag, kolumn in (("land", "land", "land_id"), ("landskap", "landskap", "landskap_id")):
        fasetter[namn] = rakna(f"""
            SELECT x.varde, e.namn, count(DISTINCT x.sokpost_id) AS antal FROM (
                SELECT sp.sokpost_id, CASE WHEN u.slag = '{slag}' THEN u.entitet_id ELSE u.{kolumn} END AS varde
                FROM {p}sokpost_plats sp JOIN {p}plats_uppgift u ON u.entitet_id = sp.plats_id
                WHERE sp.primar AND sp.sokpost_id IN ({urval_sql})
            ) x JOIN {p}entitet e ON e.id = x.varde
            GROUP BY x.varde, e.namn ORDER BY antal DESC LIMIT {FASETT_MAX}""")
    return fasetter


def _kartpunkter(urval_sql: str, urval_param: list) -> list[dict]:
    """
    Urvalets primära platser med läge, en punkt per plats med antalet
    objekt där. De vanligaste platserna först, högst KARTPUNKTER_MAX.
    """
    p = db._prefix()
    return _rader(f"""
        SELECT sp.plats_id, e.namn, u.latitud, u.longitud, count(DISTINCT sp.sokpost_id) AS antal
        FROM {p}sokpost_plats sp JOIN {p}plats_uppgift u ON u.entitet_id = sp.plats_id
        JOIN {p}entitet e ON e.id = sp.plats_id
        WHERE sp.primar AND u.latitud IS NOT NULL AND sp.sokpost_id IN ({urval_sql})
        GROUP BY sp.plats_id, e.namn, u.latitud, u.longitud
        ORDER BY antal DESC, e.namn LIMIT {KARTPUNKTER_MAX}""", urval_param)


def sok_objekt(fraga: str | None = None, filter_: sok.Filter | None = None, antal: int = 20, sida: int = 1,
               texttyper: str = "moderna", expandera: bool = True, fasetter: bool = True,
               karta: bool = False) -> dict:
    """
    Dokument och entiteter som matchar frågan och filtren.

    Med fråga kommer först entiteter och verk vars namn är frågan eller
    börjar med den, sedan verken med bäst textträff och sist övriga
    namnträffar. Textträffarna har med sitt bästa textställe som utdrag.
    Utan fråga listas urvalet i tidsordning.
    """
    filter_ = filter_ or sok.Filter(tidsaxel="primar")
    p, ph = db._prefix(), db._ph()
    fran = (sida - 1) * antal
    svar: dict = {"fraga": fraga, "expansion": []}

    if fraga and fraga.strip():
        namn_ids, namngrupp, tolkade_namn = _namntraffar(fraga, filter_)
        utdrag: dict[str, tuple[str, float]] = {}
        if filter_.objekttyp != "entitet":
            utdrag, svar["expansion"], svar["kapad"] = _texttraffar(fraga, filter_, texttyper, expandera,
                                                                    tolkade_namn)
        # Registerposter som ett felstavat ord tolkades som (ledong → ledung)
        # räknas som namnträffar, om de uppfyller filtren
        tolkade_poster = [b["begrepp_id"] for b in svar["expansion"]
                          if b["stavning"] and not b["begrepp_id"].startswith("namnform:")
                          and b["begrepp_id"] not in namngrupp]
        if tolkade_poster:
            villkor, param = filter_.sokpost_villkor("s")
            for r in _rader(f"SELECT s.id FROM {p}sokpost s WHERE s.id IN ({', '.join([ph] * len(tolkade_poster))})"
                            + (f" AND {' AND '.join(villkor)}" if villkor else ""), [*tolkade_poster, *param]):
                namn_ids.insert(0, r["id"])
                namngrupp[r["id"]] = 1
        # Hur en felstavad fråga tolkades: namnformer och register-termer
        tolkat = ([b["huvudterm"] for b in svar["expansion"] if b["stavning"] and not b["begrepp_id"].startswith("namnform:")]
                  or [n.title() for n in tolkade_namn])
        svar["stavning"] = list({n.casefold(): n for n in reversed(tolkat)}.values())[::-1]
        ordning: list[str] = []
        for pid in [i for i in namn_ids if namngrupp[i] < 2] + list(utdrag) + namn_ids:
            if pid not in ordning:
                ordning.append(pid)
        total = len(ordning)
        sidans = ordning[fran:fran + antal]
        poster = hamta_poster(sidans)
        passager = {r["passage_id"]: r for r in sok.hamta_passager([utdrag[i][0] for i in sidans if i in utdrag])}
        traffar = []
        for pid in sidans:
            if pid not in poster:
                continue
            traff = {**poster[pid], "traff": "text" if pid in utdrag and namngrupp.get(pid, 3) >= 2 else "namn"}
            if pid in utdrag and utdrag[pid][0] in passager:
                t = passager[utdrag[pid][0]]
                traff["poang"] = utdrag[pid][1]
                traff["utdrag"] = {"passage_id": t["passage_id"], "passagetyp": t["passagetyp"],
                                   "sprak": t["sprak"], "text": t["text"],
                                   "verkbedomningar": t["verkbedomningar"]}
            traffar.append(traff)
        if fasetter and ordning:
            svar["fasetter"] = _fasetter(", ".join([ph] * len(ordning)), ordning, filter_.tidsaxel)
        if karta and ordning:
            svar["karta"] = _kartpunkter(", ".join([ph] * len(ordning)), ordning)
    else:
        villkor, param = filter_.sokpost_villkor("s")
        where = f"WHERE {' AND '.join(villkor)}" if villkor else ""
        urval = f"SELECT s.id FROM {p}sokpost s {where}"
        total = _rader(f"SELECT count(*) AS antal FROM {p}sokpost s {where}", param)[0]["antal"]
        sidans = [r["id"] for r in _rader(
            f"""SELECT s.id FROM {p}sokpost s {where}
                ORDER BY CASE WHEN s.tid_fran IS NULL THEN 1 ELSE 0 END, s.tid_fran, s.id
                LIMIT {ph} OFFSET {ph}""", [*param, antal, fran])]
        poster = hamta_poster(sidans)
        traffar = [{**poster[pid], "traff": "urval"} for pid in sidans if pid in poster]
        if fasetter:
            svar["fasetter"] = _fasetter(urval, param, filter_.tidsaxel)
        if karta:
            svar["karta"] = _kartpunkter(urval, param)

    svar.update({"total": total, "sida": sida, "antal": antal, "traffar": traffar})
    svar.setdefault("fasetter", {})
    svar.setdefault("karta", [])
    svar.setdefault("kapad", False)
    svar.setdefault("stavning", [])
    return svar


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("fraga", nargs="?")
    tolk.add_argument("--ar-fran", type=int)
    tolk.add_argument("--ar-till", type=int)
    tolk.add_argument("--tidsaxel", default="primar", choices=sok.TIDSAXLAR)
    tolk.add_argument("--plats")
    tolk.add_argument("--platsroll", choices=sok.PLATSROLLER)
    tolk.add_argument("--objekttyp", choices=("verk", "entitet"))
    tolk.add_argument("--undertyp")
    tolk.add_argument("--kallsamling")
    tolk.add_argument("--antal", type=int, default=10)
    argument = tolk.parse_args()
    filter_ = sok.Filter(argument.ar_fran, argument.ar_till, tidsaxel=argument.tidsaxel, plats=argument.plats,
                         platsroll=argument.platsroll, objekttyp=argument.objekttyp, undertyp=argument.undertyp,
                         kallsamling=argument.kallsamling)
    print(json.dumps(sok_objekt(argument.fraga, filter_, argument.antal), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

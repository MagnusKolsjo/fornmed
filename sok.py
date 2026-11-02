"""
Fulltext-, vektor- och hybridsökning i passager, med termexpansion ur
begreppsregistret.

Användning:
    python sok.py "kungen befriar ett kloster från skatt"
    python sok.py "ledung" --metod fts
    python sok.py "brev om förläning av slott" --metod vektor --antal 5
    python sok.py "tionde till kyrkan" --ar-fran 1300 --ar-till 1350
    python sok.py "lagman" --texttyper alla      # även latinska och fornsvenska originaltexter
"""

import argparse
import math
import re
from dataclasses import dataclass, field

import db
import embeddings
from normalisering import ordform

MODERNA_TYPER = ("regest", "oversattning")
ALLA_TYPER = ("regest", "oversattning", "originaltext", "normaliserad", "skolion")

# Hur många kandidater varje metod lämnar till sammanvägningen
KANDIDATER = 100

# Konstanten i reciprocal rank fusion. 60 är det värde metoden föreslogs
# med och dämpar skillnaden mellan första och tionde plats lagom.
RRF_K = 60

# Hur mycket en passages placeringar i fler listor än den bästa räknas. Med
# vanlig RRF (summan, vikt 1) vinner en passage som syns måttligt högt i två
# listor över en som står överst i en enda. Det missgynnar texter som bara
# kan träffas på ett sätt: ett latinskt kapitel matchar inte en svensk fråga i
# fulltexten och har ingen svensk vektor, så det har bara sin vektorlista,
# medan Saxos danska text kan träffas både i fulltexten och semantiskt. Med
# halv vikt hamnade Gregorius 3.3 bland de tio första för en svensk fråga om
# Chlochilaicus, och i en provuppsättning med 22 frågor med kända svar fick
# fler frågor en relevant träff bland de tio första (16 mot 13, mätt innan
# fulltexten fick IDF-rankning; se utvardera_sok.py). Samstämmighet
# mellan listorna väger fortfarande, bara mindre.
# Vikten gäller bara när originaltexterna söks. Bland regester och moderna
# översättningar finns inte samma obalans, och där släppte den lägre vikten
# in fler toppträffar från den flerspråkiga listan (Saxo, runstenar) bland
# breven utan att ge fler relevanta träffar.
RRF_OVRIGA_VIKT = 0.5

# Största k som sqlite-vec accepterar i en grannsökning
SQLITE_VEC_MAX_K = 4096

# Ord kortare än så här söks exakt; längre även som prefix, så att ledung
# också hittar ledungslama. Korta ord som prefix (by*) skulle träffa för brett.
PREFIX_MIN_TECKEN = 5

# Svenska småord som inte söks ostemmat (se _fts_termer)
SMAORD = set("""
i och av på till med en ett som att den det de om för från vid under över hos mot ur är var
har hade sin sitt sina han hon hans hennes deras eller men så när där här
""".split())

# Böjningsändelser som prövas bort när ett frågeord matchas mot registret
# (lagmannen → lagman, häradet → härad), längsta först
SUFFIX = ("arnas", "ernas", "ornas", "arna", "erna", "orna", "nas", "ens", "ets", "en", "et", "er",
          "ar", "or", "na", "n", "s")


@dataclass
class Filter:
    """Avgränsning på verkets datering (överlappande årsintervall) och genre."""

    ar_fran: int | None = None
    ar_till: int | None = None
    genre: str | None = None

    def aktivt(self) -> bool:
        return any(v is not None for v in (self.ar_fran, self.ar_till, self.genre))

    def sql(self, alias: str = "v") -> tuple[str, list]:
        """
        WHERE-villkor mot verk-tabellen. Ett verk träffas om dess
        dateringsintervall överlappar det sökta; odaterade verk faller bort
        när ett årsfilter anges.
        """
        villkor, param = [], []
        if self.ar_fran is not None:
            villkor.append(f"{alias}.datering_till >= {db._ph()}")
            param.append(self.ar_fran * 10000 + 101)
        if self.ar_till is not None:
            villkor.append(f"{alias}.datering_fran <= {db._ph()}")
            param.append(self.ar_till * 10000 + 1231)
        if self.genre is not None:
            villkor.append(f"{alias}.genre = {db._ph()}")
            param.append(self.genre)
        return (" AND " + " AND ".join(villkor) if villkor else ""), param


@dataclass
class Expansion:
    """Begrepp som frågan träffade i registret och de termer de tillför."""

    begrepp: list[dict] = field(default_factory=list)

    def termer(self) -> list[tuple[str, str]]:
        """Alla tillagda termer som (term, språk), utan dubbletter."""
        sett, ut = set(), []
        for b in self.begrepp:
            for term, sprak in b["termer"]:
                former = [term]
                # Substantiv på -are har bestämd plural på -arna (väpnarna),
                # som varken prefixet väpnare* eller stemmingen fångar
                if sprak == "swe" and term.endswith("are") and len(term) >= 6:
                    former.append(term[:-1])
                for form in former:
                    if (form, sprak) not in sett:
                        sett.add((form, sprak))
                        ut.append((form, sprak))
        return ut

    def vektortext(self, fraga: str) -> str:
        """
        Frågan med begreppens definitioner tillagda. Embedding-modellen
        känner inte historiska fackord som ledung; definitionen ger den
        något att jämföra med.
        """
        if not self.begrepp:
            return fraga
        return fraga + ". " + " ".join(f"{b['huvudterm']}: {b['definition']}" for b in self.begrepp)

    def som_dict(self) -> list[dict]:
        return [{"ord": b["ord"], "begrepp_id": b["begrepp_id"], "huvudterm": b["huvudterm"],
                 "antal_termer": len(b["termer"])} for b in self.begrepp]


def _kandidatformer(ord_: str) -> list[str]:
    """Ordet och dess former utan vanliga böjningsändelser, normaliserade."""
    former = [ordform(ord_)]
    for suffix in SUFFIX:
        if ord_.lower().endswith(suffix) and len(ord_) - len(suffix) >= 3:
            former.append(ordform(ord_[: -len(suffix)]))
    # väpnarna → väpnare, domarna → domare
    if ord_.lower().endswith("arna") and len(ord_) >= 7:
        former.append(ordform(ord_[:-2] + "e"))
    return list(dict.fromkeys(former))


def expandera(fraga: str) -> Expansion:
    """
    Slår upp frågans ord och ordpar i begreppsregistret: begrepp, platser,
    folk och personer. Namn expanderas bara med stavningsvarianter av samma
    namn (Starkad, Starcatherus, Stærkodder), aldrig med identifieringar som
    forskningen diskuterar (Hygelac = Chlochilaicus); de ligger i
    identifieringstabellen med sina bedömningar.
    """
    ord_ = re.findall(r"\w+", fraga)
    kandidater: dict[str, str] = {}
    for o in ord_ + [f"{a} {b}" for a, b in zip(ord_, ord_[1:])]:
        for form in _kandidatformer(o):
            kandidater.setdefault(form, o)
    if not kandidater:
        return Expansion()
    p, ph = db._prefix(), db._ph()
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT DISTINCT t.sokform, e.id, e.namn, e.beskrivning
            FROM {p}term t JOIN {p}entitet e ON e.id = t.entitet_id
            WHERE e.typ IN ('begrepp', 'plats', 'grupp', 'person')
              AND t.sokform IN ({', '.join([ph] * len(kandidater))})
            """,
            list(kandidater),
        )
        traffar = cur.fetchall()
        begrepp = {}
        for sokform, begrepp_id, namn, beskrivning in traffar:
            begrepp.setdefault(begrepp_id, {"ord": kandidater[sokform], "begrepp_id": begrepp_id,
                                            "huvudterm": namn, "definition": beskrivning or ""})
        for begrepp_id, b in begrepp.items():
            cur.execute(f"SELECT term, sprak FROM {p}term WHERE entitet_id = {ph} ORDER BY id",
                        (begrepp_id,))
            b["termer"] = cur.fetchall()
    finally:
        conn.close()
    return Expansion(list(begrepp.values()))


def _fts_termer(termer: list[tuple[str, str, bool]]) -> tuple[str, str, str]:
    """
    Bygger fulltextfrågan ur (term, språk, stemma)-tripler, med ELLER
    mellan termerna, som (Postgres svensk, Postgres enkel, SQLite).
    Flerordstermer blir fraser. Latinska termer söks på stammen
    (advocatus → advocat*) eftersom originaltexterna böjer dem.

    Bara termer med stemma=True går till den svenska konfigurationen, och
    där utan prefix. Svensk stemming slår ihop fackord med vardagsord
    (fastar → fast, som träffar fasta och fast), och prefix efter stemming
    blir ännu bredare. För begrepp i registret ger registret formerna i
    stället, så de söks bara ostemmat.
    """
    pg_sv, pg_enkel, lite = [], [], []
    for term, sprak, stemma in termer:
        ord_ = re.findall(r"\w+", term)
        if not ord_:
            continue
        if sprak == "swe" and len(ord_) == 1 and ord_[0].lower() in SMAORD:
            # Den svenska konfigurationen har egna stoppord; i den ostemmade
            # sökningen skulle småorden träffa nästan varje fornsvensk text
            if stemma:
                pg_sv.append(ord_[0])
            continue
        prefix = len(ord_[-1]) >= PREFIX_MIN_TECKEN
        if sprak == "lat" and len(ord_[-1]) >= 6:
            ord_[-1] = ord_[-1][:-2]
        fras = " <-> ".join(ord_)
        if stemma:
            pg_sv.append(fras)
        pg_enkel.append(fras + (":*" if prefix else ""))
        lite.append('"' + " ".join(ord_) + '"' + ("*" if prefix else ""))
    return (" | ".join(dict.fromkeys(pg_sv)), " | ".join(dict.fromkeys(pg_enkel)),
            " OR ".join(dict.fromkeys(lite)))


def _idf(cur, grupper: list[list[tuple[str, str, bool]]]) -> list[tuple[str, list, float]]:
    """
    (SQL-villkor, parametrar, IDF) för varje termgrupp, med IDF räknad som i
    bm25 över alla passager: ln(1 + (N - df + 0,5) / (df + 0,5)).
    """
    p = db._prefix()
    cur.execute(f"SELECT count(*) FROM {p}passage")
    n = cur.fetchone()[0]
    ut = []
    for grupp in grupper:
        sv, enkel, _ = _fts_termer(grupp)
        delar, param = [], []
        if sv:
            delar.append("pa.sokvektor @@ to_tsquery('swedish', %s)")
            param.append(sv)
        if enkel:
            delar.append("pa.sokvektor @@ to_tsquery('simple', %s)")
            param.append(enkel)
        if not delar:
            continue
        villkor = "(" + " OR ".join(delar) + ")"
        cur.execute(f"SELECT count(*) FROM {p}passage pa WHERE {villkor}", param)
        df = cur.fetchone()[0]
        ut.append((villkor, param, math.log(1 + (n - df + 0.5) / (df + 0.5))))
    return ut


def _valj_stemming(termer: list[tuple[str, str, bool]]) -> list[tuple[str, str, bool]]:
    """
    Slår på svensk stemming för de moderna termer i begreppsregistret som
    stemmingen bara kortar marginellt (väpnare → väpnar, så att väpnarna
    träffas), men inte för dem den slår ihop med andra ord (fastar → fast).
    Gränsen är att stammen får vara högst ett tecken kortare än termen.
    """
    kandidater = [t for t, sprak, stemma in termer if sprak == "swe" and not stemma and " " not in t]
    if not kandidater:
        return termer
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT t, array_to_string(tsvector_to_array(to_tsvector('swedish', t)), ' ') "
            "FROM unnest(%s::text[]) AS t",
            (kandidater,),
        )
        stammar = dict(cur.fetchall())
    finally:
        conn.close()
    return [
        (t, sprak, stemma or (t in stammar and len(stammar[t]) >= len(t) - 1))
        for t, sprak, stemma in termer
    ]


def fulltextsok(fraga: str, antal: int = KANDIDATER, filter_: Filter | None = None,
                typer: tuple[str, ...] = MODERNA_TYPER, expansion: Expansion | None = None
                ) -> list[tuple[str, float]]:
    """
    Passager rankade på fulltexträff, som (passage_id, poäng).

    Orden i frågan och termerna från expansionen kombineras med ELLER så att
    en träff inte kräver exakt samma ord som frågan; rankningen sköter resten.
    """
    expansion = expansion or Expansion()
    traffade = {o for b in expansion.begrepp for o in b["ord"].split()}
    fragans_ord = re.findall(r"\w+", fraga)
    termer = [(o, "swe", o not in traffade) for o in fragans_ord]
    termer += [(t, sprak, False) for t, sprak in expansion.termer()]
    # Varje frågeord som inte expanderats är en grupp, och varje begrepp med
    # alla sina termer en; grupperna vägs efter hur sällsynta de är (_idf)
    grupper = [[(o, "swe", True)] for o in fragans_ord if o not in traffade and o.lower() not in SMAORD]
    grupper += [[(o, "swe", False) for o in b["ord"].split()] + [(t, sprak, False) for t, sprak in b["termer"]]
                for b in expansion.begrepp]
    if db._ar_postgres():
        termer = _valj_stemming(termer)
        grupper = [_valj_stemming(g) for g in grupper]
    pg_sv, pg_enkel, lite_fraga = _fts_termer(termer)
    if not lite_fraga:
        return []
    filter_sql, filter_param = (filter_ or Filter()).sql()
    p, ph = db._prefix(), db._ph()
    typ_sql = ", ".join([ph] * len(typer))
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        if db._ar_postgres():
            # Regester är indexerade med svensk stemming, originaltexter
            # utan; frågan ställs därför i båda konfigurationerna.
            # ts_rank_cd väger inte termerna efter hur vanliga de är, så en
            # passage som nämner kung och ö går före en som nämner Starkad.
            # Poängen är därför summan av IDF för de grupper passagen
            # träffar, som i bm25 (SQLite-backenden); ts_rank_cd, delad med
            # textens längd, skiljer bara passager med samma grupper åt.
            villkor, idf_param = [], []
            for villkor_sql, param, idf in _idf(cur, grupper):
                villkor.append(f"CASE WHEN {villkor_sql} THEN {ph} ELSE 0 END")
                idf_param += [*param, idf]
            idf_sql = " + ".join(villkor) or "0"
            cur.execute(
                f"""
                SELECT pa.id, {idf_sql}
                       + greatest(ts_rank_cd(pa.sokvektor, qs, 1), ts_rank_cd(pa.sokvektor, qe, 1)) AS poang
                FROM {p}passage pa
                JOIN {p}verk v ON v.id = pa.verk_id,
                     to_tsquery('swedish', {ph}) qs, to_tsquery('simple', {ph}) qe
                WHERE (pa.sokvektor @@ qs OR pa.sokvektor @@ qe)
                  AND pa.typ IN ({typ_sql}){filter_sql}
                ORDER BY poang DESC
                LIMIT {ph}
                """,
                (*idf_param, pg_sv, pg_enkel, *typer, *filter_param, antal),
            )
        else:
            cur.execute(
                f"""
                SELECT pa.id, -bm25(passage_fts) AS poang
                FROM passage_fts
                JOIN passage pa ON pa.rowid = passage_fts.rowid
                JOIN verk v ON v.id = pa.verk_id
                WHERE passage_fts MATCH {ph} AND pa.typ IN ({typ_sql}){filter_sql}
                ORDER BY bm25(passage_fts)
                LIMIT {ph}
                """,
                (lite_fraga, *typer, *filter_param, antal),
            )
        return cur.fetchall()
    finally:
        conn.close()


def vektorsok(fraga: str, antal: int = KANDIDATER, filter_: Filter | None = None,
              expansion: Expansion | None = None, roll: str = "svenska",
              typer: tuple[str, ...] = ALLA_TYPER) -> list[tuple[str, float]]:
    """
    Passager rankade på semantisk likhet, som (passage_id, cosinuslikhet).
    En passage med flera chunkar får sin bästa chunks likhet.

    roll väljer embeddingmodell (se embeddings.MODELLER): 'svenska' söker i
    regester och översättningar på modern svenska, 'flersprak' i översättningar
    till andra språk och de latinska krönikorna (se berakna_embeddings.urval).
    Frågan embeddas med samma modell som passagerna, och bara den modellens
    vektorer jämförs.
    """
    filter_ = filter_ or Filter()
    filter_sql, filter_param = filter_.sql()
    modell = embeddings.MODELLER[roll]
    vektor = embeddings.embedda_fraga(expansion.vektortext(fraga) if expansion else fraga, modell)
    typ_sql = " AND pa.typ IN (" + ", ".join(["%s" if db._ar_postgres() else "?"] * len(typer)) + ")"
    p = db._prefix()
    # Fler chunkar än passager hämtas eftersom flera chunkar kan höra till
    # samma passage. Med filter hämtas betydligt fler, eftersom filtret
    # tillämpas efter grannsökningen och kan sålla bort de flesta.
    k = antal * 10 if filter_.aktivt() else antal * 2
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        if db._ar_postgres():
            with conn:
                # HNSW returnerar som mest ef_search rader (standard 40),
                # oavsett LIMIT; höjs för den här transaktionen. Med filter
                # fortsätter iterativ sökning tills LIMIT fyllts.
                # Textypsfiltret tillämpas efter grannsökningen; iterativ
                # sökning fortsätter tills LIMIT fyllts. Villkoret på modell
                # matchar modellens partiella index (db.skapa_vektorindex).
                cur.execute(f"SET LOCAL hnsw.ef_search = {min(max(k, 40), 1000)}")
                cur.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
                cur.execute(
                    f"""
                    SELECT c.passage_id, 1 - (e.vektor <=> %s::vector) AS likhet
                    FROM {p}embedding e
                    JOIN {p}chunk c ON c.id = e.chunk_id
                    JOIN {p}passage pa ON pa.id = c.passage_id
                    JOIN {p}verk v ON v.id = pa.verk_id
                    WHERE e.modell = %s{typ_sql}{filter_sql}
                    ORDER BY e.vektor <=> %s::vector
                    LIMIT %s
                    """,
                    (str(vektor), modell, *typer, *filter_param, str(vektor), k),
                )
                rader = cur.fetchall()
        else:
            # vec0 kan inte filtrera på kolumner i andra tabeller under
            # grannsökningen; filtret tillämpas på de k närmaste, så med
            # filter hämtas så många som vec0 tillåter
            if filter_.aktivt() or set(typer) != set(ALLA_TYPER):
                k = SQLITE_VEC_MAX_K
            cur.execute(
                f"""
                SELECT c.passage_id, 1 - e.distance AS likhet
                FROM (SELECT chunk_id, distance FROM embedding
                      WHERE vektor MATCH ? AND k = ? AND modell = ?) e
                JOIN chunk c ON c.id = e.chunk_id
                JOIN passage pa ON pa.id = c.passage_id
                JOIN verk v ON v.id = pa.verk_id
                WHERE 1 = 1{typ_sql}{filter_sql}
                ORDER BY e.distance
                """,
                (db.sqlite_vec.serialize_float32(vektor), k, modell, *typer, *filter_param),
            )
            rader = cur.fetchall()
    finally:
        conn.close()

    basta: dict[str, float] = {}
    for passage_id, likhet in rader:
        basta[passage_id] = max(likhet, basta.get(passage_id, -1.0))
    return sorted(basta.items(), key=lambda r: r[1], reverse=True)[:antal]


def vag_samman(listor: list[list[tuple[str, float]]], typer: tuple[str, ...]) -> dict[str, float]:
    """
    Reciprocal rank fusion där passagens bästa placering räknas fullt och
    placeringarna i övriga listor med vikten RRF_OVRIGA_VIKT när
    originaltexter ingår, annars fullt (vanlig RRF).
    """
    vikt = RRF_OVRIGA_VIKT if "originaltext" in typer else 1.0
    bidrag: dict[str, list[float]] = {}
    for traffar in listor:
        for plats, (passage_id, _) in enumerate(traffar, start=1):
            bidrag.setdefault(passage_id, []).append(1 / (RRF_K + plats))
    return {pid: max(b) + vikt * (sum(b) - max(b)) for pid, b in bidrag.items()}


def hybridsok(fraga: str, antal: int = 10, filter_: Filter | None = None,
              typer: tuple[str, ...] = MODERNA_TYPER, expansion: Expansion | None = None
              ) -> list[dict]:
    """
    Väger samman fulltext- och vektorsökning med reciprocal rank fusion
    (se vag_samman).

    RRF använder bara placeringarna, inte poängen. Det gör sammanvägningen
    oberoende av att ts_rank, bm25 och cosinuslikhet ligger på helt olika
    skalor, och den beter sig likadant i båda backenderna.
    """
    fts = fulltextsok(fraga, filter_=filter_, typer=typer, expansion=expansion)
    # En vektorlista per embeddingmodell; varje modell har sina egna passager,
    # så listorna överlappar inte och vägs samman på placering som fulltexten
    vek = {roll: vektorsok(fraga, filter_=filter_, expansion=expansion, roll=roll, typer=typer)
           for roll in embeddings.MODELLER}
    poang = vag_samman([fts, *vek.values()], typer)
    fts_plats = {pid: i for i, (pid, _) in enumerate(fts, start=1)}
    vek_plats = {pid: i for traffar in vek.values() for i, (pid, _) in enumerate(traffar, start=1)}
    basta = sorted(poang.items(), key=lambda r: r[1], reverse=True)[:antal]
    return [
        {**rad, "poang": round(poang_, 4), "fts_plats": fts_plats.get(rad["passage_id"]),
         "vektor_plats": vek_plats.get(rad["passage_id"])}
        for rad, poang_ in zip(hamta_passager([pid for pid, _ in basta]), (s for _, s in basta))
    ]


def sok(fraga: str, metod: str = "hybrid", antal: int = 10, filter_: Filter | None = None,
        texttyper: str = "moderna", expandera_termer: bool = True) -> dict:
    """
    Gemensam ingång för de tre metoderna.

    texttyper: 'moderna' söker i regester och översättningar (på alla språk),
    'alla' även i originaltexter och normaliseringar. Båda embeddingmodellerna
    används; deras träfflistor vägs samman på placering, eftersom likheter
    från olika modeller inte går att jämföra. Svaret innehåller träffarna och
    vilka begrepp frågan expanderades med.
    """
    if metod not in ("hybrid", "fts", "vektor"):
        raise ValueError(f"Okänd sökmetod '{metod}'. Använd hybrid, fts eller vektor.")
    if texttyper not in ("moderna", "alla"):
        raise ValueError(f"Okänt värde för texttyper '{texttyper}'. Använd moderna eller alla.")
    typer = ALLA_TYPER if texttyper == "alla" else MODERNA_TYPER
    expansion = expandera(fraga) if expandera_termer else Expansion()

    if metod == "hybrid":
        traffar = hybridsok(fraga, antal, filter_, typer, expansion)
    else:
        if metod == "fts":
            rader = fulltextsok(fraga, antal, filter_, typer, expansion)
        else:
            rrf = vag_samman([vektorsok(fraga, antal, filter_, expansion, roll, typer)
                              for roll in embeddings.MODELLER], typer)
            rader = sorted(rrf.items(), key=lambda r: r[1], reverse=True)[:antal]
        poang = dict(rader)
        traffar = [{**r, "poang": round(poang[r["passage_id"]], 4)}
                   for r in hamta_passager([pid for pid, _ in rader])]
    return {"traffar": traffar, "expansion": expansion.som_dict()}


def hamta_passager(passage_ids: list[str]) -> list[dict]:
    """
    Passager med verkets titel, genre och datering samt bedömningar av
    verket (t.ex. misstänkt förfalskning), i samma ordning som indata.
    """
    if not passage_ids:
        return []
    p, ph = db._prefix(), db._ph()
    platser = ", ".join([ph] * len(passage_ids))
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT pa.id, pa.verk_id, v.titel, v.genre, v.datering_edtf, v.extern_url,
                   pa.url, COALESCE(u.licens, k.licens), pa.typ, pa.sprak, pa.text
            FROM {p}passage pa JOIN {p}verk v ON v.id = pa.verk_id
            LEFT JOIN {p}utgava u ON u.id = pa.utgava_id
            LEFT JOIN {p}kallsamling k ON k.id = v.kallsamling_id
            WHERE pa.id IN ({platser})
            """,
            passage_ids,
        )
        rader = {r[0]: r for r in cur.fetchall()}
        verk_ids = sorted({r[1] for r in rader.values()})
        bedomningar: dict[str, list[str]] = {}
        if verk_ids:
            cur.execute(
                f"""
                SELECT verk_id, aspekt, varde, bedomare FROM {p}bedomning
                WHERE verk_id IN ({', '.join([ph] * len(verk_ids))})
                """,
                verk_ids,
            )
            for verk_id, aspekt, varde, bedomare in cur.fetchall():
                bedomningar.setdefault(verk_id, []).append(f"{aspekt}: {varde} ({bedomare})")
    finally:
        conn.close()
    nycklar = ("passage_id", "verk_id", "titel", "genre", "datering", "url", "underlag_url", "licens",
               "passagetyp", "sprak", "text")
    return [
        {**dict(zip(nycklar, rader[pid])), "verkbedomningar": bedomningar.get(rader[pid][1], [])}
        for pid in passage_ids if pid in rader
    ]


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("fraga")
    tolk.add_argument("--metod", choices=("hybrid", "fts", "vektor"), default="hybrid")
    tolk.add_argument("--antal", type=int, default=10)
    tolk.add_argument("--ar-fran", type=int)
    tolk.add_argument("--ar-till", type=int)
    tolk.add_argument("--genre")
    tolk.add_argument("--texttyper", choices=("moderna", "alla"), default="moderna")
    tolk.add_argument("--utan-expansion", action="store_true")
    arg = tolk.parse_args()

    svar = sok(arg.fraga, arg.metod, arg.antal, Filter(arg.ar_fran, arg.ar_till, arg.genre),
               arg.texttyper, not arg.utan_expansion)
    for b in svar["expansion"]:
        print(f"expansion: '{b['ord']}' → {b['huvudterm']} ({b['antal_termer']} termer)")
    for t in svar["traffar"]:
        platser = ""
        if arg.metod == "hybrid":
            platser = f"  [fts {t['fts_plats'] or '–'}, vektor {t['vektor_plats'] or '–'}]"
        print(f"{t['poang']:.3f}  {t['titel']}  {t['datering'] or 'odaterat'}  {t['passagetyp']}{platser}")
        for b in t["verkbedomningar"]:
            print(f"       ! {b}")
        print(f"       {t['text'][:220]}")


if __name__ == "__main__":
    main()

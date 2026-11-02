"""
Fyller i utgåvornas språkversion och passagernas del i verket.

Utgåvorna får språk, typ (original, översättning eller maskinöversättning),
roll (huvudtext eller skolier), översättare och år. Uppgifterna härleds ur
det som redan finns: passagernas språk och typ, utgåvans id och
referensen, där tryckta översättningar anges som "Namn (övers.), …, Ort år".

Passagerna får den del av verket de hör till: bok, balk, del av en
annalserie eller namngivet avsnitt som en saga i en kungasagesamling.
Delen läses ur passageadressen ("bok I, kap. 1", "ÄVgL Kkb 1 — Kirkiu
bolkær, flock 1", "Liber Septimus, kap. 21"). Böcker numreras med
romerska siffror, så att "Liber Septimus" och "Liber VII" blir samma del.
Verk utan sådan indelning (sagor med bara kapitel, brev, runinskrifter)
får ingen del och hämtas som helhet.

Körningen är idempotent: allt härleds på nytt, men bara rader vars värden
ändras skrivs. Kör den efter varje import och efter ändrade regler här.

Användning:
    python struktur.py
"""

import argparse
import logging
import re
from collections import Counter, defaultdict

import db

log = logging.getLogger("struktur")

# Källsamlingar vars passager aldrig delas in: varje verk är ett brev eller en inskrift
UTAN_DELAR = ("sdhk", "rundata")

LATINSKA_ORDNINGSTAL = {
    "primus": 1, "secundus": 2, "tertius": 3, "quartus": 4, "quintus": 5,
    "sextus": 6, "septimus": 7, "octavus": 8, "nonus": 9, "decimus": 10,
    "undecimus": 11, "duodecimus": 12,
}

ROMERSKA = (("M", 1000), ("CM", 900), ("D", 500), ("CD", 400), ("C", 100), ("XC", 90),
            ("L", 50), ("XL", 40), ("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1))

# Suffix som importen lägger till i adressen och som inte hör till indelningen
SUFFIX = re.compile(r"\s*\((?:maskinöversättning|[^()]*\d{4}[^()]*)\)\s*$")

BOK = re.compile(r"^(?:bok|liber)\s+([IVXLC]+|\d+|[a-z]+)\b", re.IGNORECASE)
SKOLION_BOK = re.compile(r"\(till bok ([IVXLC]+|\d+)\b")
ANNALDEL = re.compile(r"^del ([IVXLC]+)\b")
LAGBALK = re.compile(r" — (?P<balk>[^,]+), flock \d+")
LAGBALK_STYCKE = re.compile(r"^(?P<balk>[^,—()]+), stycke \d+$")
# "Gylfaginning, kap. 42", "Skáldskaparmál, omskrivningar, kap. 34"
NAMNGIVET_AVSNITT = re.compile(r"^(?P<avsnitt>[^,()]+),(?: [^,()]+,)? (?:kap\.|avsnitt) ")
SAGA = re.compile(r"\b(saga|sǫgu|þáttr|tháttr|þáttur)\b", re.IGNORECASE)

# "Emil Olson (övers.), …" och "Citaten i Ynglinga saga efter Emil Olson (övers.), …"
OVERSATTARE = re.compile(r"^(?:.* efter )?(?P<namn>[^()]+?)\s*\(övers\.\)")
# Utgivningsår; ett datum som "2016-11-28" är filens tidsstämpel i openMGH, inte ett utgivningsår
AR = re.compile(r"\b(1[4-9]\d\d|20\d\d)\b(?!-\d\d-\d\d)")


def romersk(tal: int) -> str:
    """Skriver ett heltal med romerska siffror."""
    delar = []
    for symbol, varde in ROMERSKA:
        antal, tal = divmod(tal, varde)
        delar.append(symbol * antal)
    return "".join(delar)


def boknummer(beteckning: str) -> int | None:
    """Boknumret ur en romersk siffra, en arabisk siffra eller ett latinskt ordningstal."""
    if beteckning.isdigit():
        return int(beteckning)
    if beteckning.lower() in LATINSKA_ORDNINGSTAL:
        return LATINSKA_ORDNINGSTAL[beteckning.lower()]
    beteckning = beteckning.upper()
    if not re.fullmatch(r"[IVXLC]+", beteckning):
        return None
    # Olaus Magnus skriver XIIII för 14; summan per tecken klarar både den
    # additiva och den subtraktiva skrivningen
    summa = 0
    varden = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    for nuvarande, nasta in zip(beteckning, beteckning[1:] + " "):
        if nasta != " " and varden[nuvarande] < varden[nasta]:
            summa -= varden[nuvarande]
        else:
            summa += varden[nuvarande]
    return summa


def harled_del(adress: str | None, kallsamling: str) -> tuple[str | None, str | None]:
    """(del, deltyp) för en passage, eller (None, None) när adressen saknar indelning."""
    if not adress or kallsamling in UTAN_DELAR:
        return None, None
    # "bok 2, kap. 9 (Haupt 1863) (maskinöversättning)" har två suffix
    while (kortare := SUFFIX.sub("", adress).strip()) != adress:
        adress = kortare

    # Skolier hör till den bok de kommenterar: "skolion 32 (till bok II, kap. 5)"
    if traff := BOK.match(adress) or SKOLION_BOK.search(adress):
        if nummer := boknummer(traff.group(1)):
            return f"bok {romersk(nummer)}", "bok"

    if traff := ANNALDEL.match(adress):
        return f"del {traff.group(1)}", "del"

    if kallsamling == "fornsvenska_lagar":
        traff = LAGBALK.search(adress) or LAGBALK_STYCKE.match(adress)
        if traff:
            return traff.group("balk").strip(), "balk"
        return None, None

    if traff := NAMNGIVET_AVSNITT.match(adress):
        avsnitt = traff.group("avsnitt").strip()
        # "kung 15", "skolion 32" och liknande är numrerade poster, inte avsnitt
        if not re.search(r"\d", avsnitt):
            return avsnitt, "saga" if SAGA.search(avsnitt) else "avsnitt"

    return None, None


def harled_utgava(utgava_id: str, referens: str, sprak: Counter, typer: Counter) -> dict:
    """Språk, typ, roll, översättare och år för en utgåva."""
    if utgava_id.endswith(":sv_modell") or "översättning gjord av språkmodell" in referens:
        typ = "maskinoversattning"
    elif "av språkmodell" in referens:
        # Originaltext som språkmodellen läst av från sidbilder (Adam av Bremens
        # skolier efter Schmeidler)
        typ = "maskintranskription"
    # En utgåva som också har originaltext (runinskrifterna med translitterering
    # och översättning) är en originalutgåva, även om översättningarna är fler
    elif "(övers.)" in referens or (typer and set(typer) <= {"oversattning", "regest"}
                                     and "oversattning" in typer):
        typ = "oversattning"
    else:
        typ = "original"

    roll = "skolier" if "skolier" in utgava_id or typer.get("skolion") else "huvudtext"

    # Utgåvor med flera språk i samma utgåva (runinskrifterna) får inget eget språk
    utgavesprak = next(iter(sprak)) if len(sprak) == 1 else None

    oversattare = None
    if typ == "oversattning" and (traff := OVERSATTARE.match(referens)):
        oversattare = traff.group("namn").strip()

    ar = None
    if typ in ("original", "oversattning") and (traff := AR.search(referens)):
        ar = int(traff.group(1))

    return {"sprak": utgavesprak, "typ": typ, "roll": roll, "oversattare": oversattare, "ar": ar}


def fyll_utgavor(conn) -> int:
    """Härleder utgåvornas fält. Returnerar antalet ändrade utgåvor."""
    ph = db._ph()
    p = db._prefix()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT u.id, u.referens, u.sprak, u.typ, u.roll, u.oversattare, u.ar,
               pa.sprak, pa.typ, count(*)
        FROM {p}utgava u JOIN {p}passage pa ON pa.utgava_id = u.id
        GROUP BY u.id, u.referens, u.sprak, u.typ, u.roll, u.oversattare, u.ar, pa.sprak, pa.typ
    """)
    nuvarande: dict[str, tuple] = {}
    referenser: dict[str, str] = {}
    sprak: dict[str, Counter] = defaultdict(Counter)
    typer: dict[str, Counter] = defaultdict(Counter)
    for utgava_id, referens, *lagrat, passagesprak, passagetyp, antal in cur.fetchall():
        referenser[utgava_id] = referens
        nuvarande[utgava_id] = tuple(lagrat)
        if passagesprak:
            sprak[utgava_id][passagesprak] += antal
        typer[utgava_id][passagetyp] += antal

    rader = []
    for utgava_id, referens in referenser.items():
        falt = harled_utgava(utgava_id, referens, sprak[utgava_id], typer[utgava_id])
        nytt = (falt["sprak"], falt["typ"], falt["roll"], falt["oversattare"], falt["ar"])
        if nytt != nuvarande[utgava_id]:
            rader.append((*nytt, utgava_id))

    sql = (f"UPDATE {p}utgava SET sprak = {ph}, typ = {ph}, roll = {ph}, "
           f"oversattare = {ph}, ar = {ph} WHERE id = {ph}")
    _kor_i_omgangar(conn, sql, rader)
    return len(rader)


def fyll_delar(conn) -> tuple[int, int]:
    """Härleder passagernas del. Returnerar (ändrade passager, passager med del)."""
    ph = db._ph()
    p = db._prefix()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT pa.id, pa.verk_id, pa.adress, v.kallsamling_id, pa.del, pa.del_typ
        FROM {p}passage pa JOIN {p}verk v ON v.id = pa.verk_id
    """)
    passager = cur.fetchall()
    harledda = {passage_id: harled_del(adress, kallsamling)
                for passage_id, _verk_id, adress, kallsamling, *_ in passager}

    # Ett verk med bara en del har ingen indelning att hämta efter. Det gäller
    # också verk där bara inledningen har en delbeteckning ("bok I, inledning"
    # följt av "kap. 9" i Historia Norwegie).
    delar_per_verk: dict[str, set] = defaultdict(set)
    for passage_id, verk_id, *_ in passager:
        if del_ := harledda[passage_id][0]:
            delar_per_verk[verk_id].add(del_)

    rader = []
    med_del = 0
    for passage_id, verk_id, _adress, _kallsamling, lagrad_del, lagrad_typ in passager:
        nytt = harledda[passage_id]
        if nytt[0] and len(delar_per_verk[verk_id]) < 2:
            nytt = (None, None)
        if nytt[0]:
            med_del += 1
        if nytt != (lagrad_del, lagrad_typ):
            rader.append((*nytt, passage_id))

    sql = f"UPDATE {p}passage SET del = {ph}, del_typ = {ph} WHERE id = {ph}"
    _kor_i_omgangar(conn, sql, rader)
    return len(rader), med_del


def _kor_i_omgangar(conn, sql: str, rader: list[tuple], storlek: int = 2000) -> None:
    """Kör en uppdatering för många rader och committar per omgång."""
    cur = conn.cursor()
    if db._ar_postgres():
        import psycopg2.extras
        for start in range(0, len(rader), storlek):
            psycopg2.extras.execute_batch(cur, sql, rader[start:start + storlek], page_size=500)
            conn.commit()
    else:
        cur.executemany(sql, rader)
        conn.commit()


def main() -> None:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db.initiera_schema()
    conn = db._hamta_db()
    try:
        utgavor = fyll_utgavor(conn)
        log.info("Utgåvor: %d ändrade", utgavor)
        andrade, med_del = fyll_delar(conn)
        log.info("Passager: %d ändrade, %d med del", andrade, med_del)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

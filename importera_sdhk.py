"""
Importerar Riksarkivets SDHK-register (Svenskt Diplomatariums huvudkartotek
över medeltidsbreven) till databasen.

Råposterna läggs oförändrade i sdhk_brev. Ur dem byggs den normaliserade
strukturen: ett verk per brev, vittnen för original och avskrifter, utgåvor
för tryck, och passager för regest och editionstext. Importen är idempotent
och kan köras om när Riksarkivet publicerar en ny ögonblicksbild.

Användning:
    python importera_sdhk.py                 # hämtar SDHK_CSV_URL
    python importera_sdhk.py --fil sdhk.csv  # läser lokal fil
    python importera_sdhk.py --begransa 500  # provimport
"""

import argparse
import csv
import io
import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import db
import sdhk_akthet

log = logging.getLogger("importera_sdhk")

SDHK_CSV_URL = os.environ.get(
    "SDHK_CSV_URL", "https://filer.riksarkivet.se/registerdata/SDHK/csv/sdhk_2411.csv"
)
SDHK_POST_URL = os.environ.get("SDHK_POST_URL", "https://sok.riksarkivet.se/sdhk?SDHK={nr}")
RAADATA_KATALOG = Path(__file__).parent / "data" / "raw" / "sdhk"

# CSV-kolumn → kolumn i sdhk_brev, i källans ordning
KOLUMNER = {
    "Id": "sdhk_nr",
    "Title": "titel",
    "Author": "utfardare",
    "Date": "datum",
    "Place": "ort",
    "Lang": "sprak",
    "Summary": "regest",
    "Comments": "kommentar",
    "Additional": "tillagg",
    "Seals": "sigill",
    "Original": "original",
    "MedievalCopy": "medeltida_avskrift",
    "PostmedievalCopy": "eftermedeltida_avskrift",
    "MedievalReg": "medeltida_registratur",
    "PostmedievalReg": "eftermedeltida_registratur",
    "Photocopy": "fotokopia",
    "Print": "tryck",
    "PrintReg": "tryckt_regest",
    "Facsimile": "faksimil",
    "Translation": "oversattning",
    "Edition": "edition",
}

# Fält i sdhk_brev som beskriver vittnen; kolumnnamnet är också vittnestypen
VITTNESFALT = [
    "original",
    "medeltida_avskrift",
    "eftermedeltida_avskrift",
    "medeltida_registratur",
    "eftermedeltida_registratur",
    "fotokopia",
    "tryckt_regest",
    "faksimil",
    "oversattning",
]

# Ordstammar i SDHK:s språkfält → ISO 639-3. Lågtyska kontrolleras före
# tyska eftersom "tyska" är en delsträng av "lågtyska".
SPRAKKODER = [
    ("lågtysk", "gml"),
    ("tysk", "deu"),
    ("svensk", "swe"),
    ("latin", "lat"),
    ("dansk", "dan"),
    ("norsk", "nor"),
    ("nederländ", "nld"),
    ("fransk", "fra"),
    ("finsk", "fin"),
    ("engelsk", "eng"),
    ("isländ", "isl"),
    ("italiensk", "ita"),
]



def las_csv(sokvag: Path) -> list[dict]:
    """
    Läser SDHK-filen. Filen är kodad i Windows-1252 men innehåller enstaka
    byte som saknar tecken där; de ersätts med U+FFFD i stället för att
    hela importen avbryts.
    """
    text = sokvag.read_bytes().decode("cp1252", errors="replace")
    ersatta = text.count("�")
    if ersatta:
        log.warning("%d byte kunde inte avkodas och ersattes med U+FFFD", ersatta)
    return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=";"))


def hamta_csv(url: str) -> Path:
    """Laddar ner CSV-filen till data/raw/sdhk/ om den inte redan finns där."""
    RAADATA_KATALOG.mkdir(parents=True, exist_ok=True)
    mal = RAADATA_KATALOG / url.rsplit("/", 1)[-1]
    if not mal.exists():
        log.info("Hämtar %s", url)
        urllib.request.urlretrieve(url, mal)
    return mal


def tolka_datum(falt: str) -> tuple[str | None, int | None, int | None, str | None]:
    """
    Tolkar SDHK:s datumfält till (EDTF, från, till, anmärkning).

    Fältet börjar med ÅÅÅÅMMDD där 00 betyder okänd månad eller dag, och
    "0" eller nollor betyder odaterat. Efter semikolon följer fri text
    ("omkring denna dag", "årtalet osäkert") som behålls som anmärkning och
    översätts till EDTF-kvalificerare: ~ för ungefärligt, ? för osäkert.
    """
    delar = [d.strip() for d in falt.split(";", 1)]
    huvud = delar[0]
    anm = delar[1] if len(delar) > 1 and delar[1] else None
    anm_lagre = (anm or "").lower()

    ungefar = "omkr" in anm_lagre
    osaker = "?" in falt or "osäker" in anm_lagre

    if re.fullmatch(r"\d{8}", huvud) and int(huvud[:4]) > 0:
        ar, man, dag = int(huvud[:4]), int(huvud[4:6]), int(huvud[6:8])
        if man == 0:
            edtf, fran, till = f"{ar:04d}", ar * 10000 + 101, ar * 10000 + 1231
        elif dag == 0:
            edtf = f"{ar:04d}-{man:02d}"
            fran, till = ar * 10000 + man * 100 + 1, ar * 10000 + man * 100 + 31
        else:
            edtf = f"{ar:04d}-{man:02d}-{dag:02d}"
            fran = till = int(huvud)
    else:
        # Odaterade brev har ofta ett årsintervall i anmärkningen, t.ex.
        # "odat. (1350-1400)"; det ger åtminstone en grov placering
        artal = sorted({int(a) for a in re.findall(r"\b(1[0-5]\d\d)\b", anm or "")})
        if not artal:
            return None, None, None, anm
        forsta, sista = artal[0], artal[-1]
        edtf = f"{forsta}/{sista}" if forsta != sista else f"{forsta}"
        fran, till = forsta * 10000 + 101, sista * 10000 + 1231
        osaker = True

    if ungefar and osaker:
        edtf += "%"
    elif ungefar:
        edtf += "~"
    elif osaker:
        edtf += "?"
    return edtf, fran, till, anm


def tolka_sprak(falt: str) -> list[str]:
    """Översätter SDHK:s fritextangivelse ("svenska/danska", "latin?") till ISO 639-3-koder."""
    lagre = falt.lower()
    koder = []
    for stam, kod in SPRAKKODER:
        if stam in lagre and kod not in koder:
            if kod == "deu" and "gml" in koder and lagre.count("tysk") == 1:
                continue
            koder.append(kod)
    return koder


def dela_referenser(falt: str) -> list[str]:
    """
    Delar ett fält med flera referenser på semikolon, men inte inuti
    parenteser — "Peringskiöld: E 7 (e. B 9); B 9:64" är två referenser.
    """
    delar, aktuell, djup = [], [], 0
    for tecken in falt:
        if tecken in "([":
            djup += 1
        elif tecken in ")]" and djup:
            djup -= 1
        if tecken == ";" and djup == 0:
            delar.append("".join(aktuell))
            aktuell = []
        else:
            aktuell.append(tecken)
    delar.append("".join(aktuell))
    return [d.strip() for d in delar if d.strip()]


def bygg_rader(poster: list[dict]) -> dict[str, list[tuple]]:
    """Omvandlar CSV-poster till rader per tabell."""
    rader = {t: [] for t in ("sdhk_brev", "verk", "utgava", "vittne", "passage")}

    for post in poster:
        rad = {KOLUMNER[k]: (v.strip() or None) for k, v in post.items()}
        nr = int(rad["sdhk_nr"])
        rad["sdhk_nr"] = nr
        rader["sdhk_brev"].append(tuple(rad[k] for k in KOLUMNER.values()))

        verk_id = f"sdhk:{nr}"
        edtf, fran, till, anm = tolka_datum(rad["datum"] or "")
        sprak = tolka_sprak(rad["sprak"] or "")
        rader["verk"].append((
            verk_id, "sdhk", rad["titel"] or f"SDHK nr {nr}", rad["utfardare"], "diplom",
            db.sprakvarde(sprak), rad["ort"], edtf, fran, till, anm,
            SDHK_POST_URL.format(nr=nr),
            json.dumps({"sigill": rad["sigill"], "tillagg": rad["tillagg"]}, ensure_ascii=False),
        ))

        # Tryckta utgåvor. Editionstexten i SDHK kommer ur Svenskt
        # Diplomatarium, så den knyts till DS- eller SD-referensen om en sådan finns.
        utgava_for_text = None
        for i, ref in enumerate(dela_referenser(rad["tryck"] or "")):
            utgava_id = f"{verk_id}:tryck:{i}"
            rader["utgava"].append((utgava_id, verk_id, ref))
            if utgava_for_text is None and re.match(r"(DS|SD)\b", ref):
                utgava_for_text = utgava_id

        for typ in VITTNESFALT:
            for i, ref in enumerate(dela_referenser(rad[typ] or "")):
                rader["vittne"].append((f"{verk_id}:{typ}:{i}", verk_id, typ, ref))

        if rad["regest"]:
            rader["passage"].append((
                f"{verk_id}:regest", verk_id, None, "regest", f"SDHK {nr}", 0, "swe", rad["regest"],
            ))
        if rad["edition"]:
            rader["passage"].append((
                f"{verk_id}:originaltext", verk_id, utgava_for_text, "originaltext", f"SDHK {nr}", 1,
                sprak[0] if len(sprak) == 1 else None, rad["edition"],
            ))

    return rader


def importera(poster: list[dict], version: str) -> None:
    """Skriver alla tabeller i den ordning som främmande nycklar kräver."""
    rader = bygg_rader(poster)
    conn = db._hamta_db()
    try:
        db.upsert(conn, "kallsamling",
                  ["id", "namn", "utgivare", "url", "licens", "version", "importerad"], ["id"],
                  [("sdhk", "Svenskt Diplomatariums huvudkartotek över medeltidsbreven (SDHK)",
                    "Riksarkivet", SDHK_CSV_URL, "CC BY 4.0", version,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"))])
        db.upsert(conn, "sdhk_brev", list(KOLUMNER.values()), ["sdhk_nr"], rader["sdhk_brev"])
        db.upsert(conn, "verk",
                  ["id", "kallsamling_id", "titel", "upphov", "genre", "sprak", "utfardandeort",
                   "datering_edtf", "datering_fran", "datering_till", "datering_anm",
                   "extern_url", "extra"], ["id"], rader["verk"])
        db.upsert(conn, "utgava", ["id", "verk_id", "referens"], ["id"], rader["utgava"])
        db.upsert(conn, "vittne", ["id", "verk_id", "typ", "beskrivning"], ["id"], rader["vittne"])
        db.upsert(conn, "passage",
                  ["id", "verk_id", "utgava_id", "typ", "adress", "ordning", "sprak", "text"],
                  ["id"], rader["passage"])
    finally:
        conn.close()
    # Äkthetsbedömningarna kommer ur den granskade listan (sdhk_akthet.py),
    # som läses när breven och vittnena finns i databasen
    log.info("Äkthetsbedömningar: %(borttagna)d borttagna, %(inlasta)d inlästa", sdhk_akthet.las_in())

    for tabell, lista in rader.items():
        log.info("%-10s %7d rader", tabell, len(lista))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--fil", type=Path, help="lokal SDHK-CSV i stället för nedladdning")
    tolk.add_argument("--begransa", type=int, help="importera bara de N första posterna")
    arg = tolk.parse_args()

    sokvag = arg.fil or hamta_csv(SDHK_CSV_URL)
    poster = las_csv(sokvag)
    if arg.begransa:
        poster = poster[: arg.begransa]
    log.info("%d poster lästa ur %s", len(poster), sokvag.name)

    db.initiera_schema()
    version = re.sub(r"\D", "", sokvag.stem) or sokvag.stem
    importera(poster, version)


if __name__ == "__main__":
    main()

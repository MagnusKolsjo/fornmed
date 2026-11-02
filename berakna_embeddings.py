"""
Chunkar passager och beräknar embeddings för dem, med två modeller:

- den svenska modellen (EMBEDDING_MODELL) för regester och översättningar
  på modern svenska,
- den flerspråkiga modellen (EMBEDDING_MODELL_FLERSPRAK) för översättningar
  till andra moderna språk (Winkel Horns danska Saxo, engelska översättningar
  av de romerska källorna och av runinskrifterna) och för de latinska
  krönikorna och romerska texterna (Adam av Bremen med skolier, Gregorius,
  Jordanes, Liber historiae Francorum, Vita Anskarii, Germania, Plinius, Mela).

Övriga originaltexter embeddas inte: SDHK-originalen, runtranslitterationer
och normaliseringar, Saxos latin och texterna på fornspråken. I ett index
tillsammans med de latinska krönikorna hamnade det formelartade brevlatinet
och translitterationerna nära nästan alla frågor och trängde undan riktiga
träffar; utan dem hittar modellen rätt kapitel även med en svensk fråga
("danerna under kung Chlochilaicus anfaller Gallien" ger Gregorius 3.3).
Verken hittas i stället via sin regest eller översättning, och originalen
med fulltext.

Varje passage embeddas med en modell. Körningen är inkrementell: passager
vars chunkar är oförändrade rörs inte, och bara chunkar som saknar vektor —
eller har en vektor från en annan modell än den som gäller för passagen —
embeddas. Kör om efter varje import.

Användning:
    python berakna_embeddings.py
    python berakna_embeddings.py --modell flersprak      # bara den flerspråkiga modellen
    python berakna_embeddings.py --begransa 1000         # provkörning
"""

import argparse
import json
import logging
import re
import time

import db
import embeddings

log = logging.getLogger("berakna_embeddings")

# De latinska krönikor och romerska texter som den flerspråkiga modellen embeddar
LATINSKA_VERK = ("adam_av_bremen", "historia_francorum", "jordanes_getica",
                 "liber_historiae_francorum", "vita_anskarii", "germania", "plinius", "mela",
                 "annales_regni_francorum", "annales_bertiniani", "annales_fuldenses", "annales_xantenses",
                 "annales_vedastini", "einhard_vita_karoli", "thegan_gesta_hludowici",
                 "astronomus_vita_hludowici", "widukind", "thietmar", "helmold", "henrik_av_lettland",
                 "paulus_diaconus", "theodoricus", "historia_norwegie", "olaus_magnus")


def urval(roll: str, alias: str = "") -> str:
    """SQL-villkor för rollens passager; alias är tabellprefixet, t.ex. 'pa.'."""
    if roll == "svenska":
        return f"{alias}typ IN ('regest', 'oversattning') AND {alias}sprak = 'swe'"
    latin = " OR ".join(f"{alias}id LIKE '{verk}:%'" for verk in LATINSKA_VERK)
    return (f"({alias}typ = 'oversattning' AND {alias}sprak <> 'swe') "
            f"OR ({alias}sprak = 'lat' AND {alias}typ IN ('originaltext', 'skolion') AND ({latin}))")


def rensa_utanfor(conn) -> None:
    """Tar bort chunkar (och därmed vektorer) för passager som ingen modell längre ska embedda."""
    p = db._prefix()
    villkor = " OR ".join(f"({urval(roll, 'pa.')})" for roll in embeddings.MODELLER)
    with conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {p}chunk WHERE passage_id IN (SELECT pa.id FROM {p}passage pa "
                    f"WHERE NOT ({villkor}))")
        if cur.rowcount:
            log.info("%d chunkar för passager utan embedding borttagna", cur.rowcount)

# Antal chunkar som embeddas och skrivs per transaktion; styr hur mycket
# arbete som går förlorat om körningen avbryts
SKRIVBATCH = 1024

# SDHK har regester som bara är platshållare ("Utgått. = SDHK nr …") eller
# namnfragment ("Kung Kristian"). Deras vektorer hamnar nära nästan alla
# frågor och tränger undan riktiga träffar, så de embeddas inte; de finns
# kvar i fulltextsökningen.
PLATSHALLARE = re.compile(r"^(utgått|dubbelregistrering)\b", re.IGNORECASE)
MIN_ORD = 5
# Rundatas engelska översättningar av fragment ("... was killed ...", "Ragnvaldr") och
# futharkrader ger på samma sätt vektorer som liknar varje fråga; en
# översättning behöver ett visst antal bokstäver för att säga något
RUNOR_MIN_BOKSTAVER = 40


def ar_embeddbar(passage_id: str, text: str) -> bool:
    """True om texten har tillräckligt innehåll för att ge en meningsfull vektor."""
    ord_ = [o for o in re.findall(r"\w+", text)]
    if len(ord_) < MIN_ORD or PLATSHALLARE.match(text.strip()):
        return False
    if passage_id.startswith("runa:") and passage_id.endswith(":en"):
        return sum(t.isalpha() for t in text) >= RUNOR_MIN_BOKSTAVER and "fuþork" not in text.lower()
    return True


def synka_chunkar(conn, roll: str, begransa: int | None) -> None:
    """Bygger om chunkarna för rollens passager vars text gett andra chunkar än de lagrade."""
    p, ph = db._prefix(), db._ph()
    cur = conn.cursor()
    cur.execute(f"SELECT id, text FROM {p}passage WHERE {urval(roll)} ORDER BY id")
    passager = cur.fetchall()
    if begransa:
        passager = passager[:begransa]

    cur.execute(f"SELECT c.passage_id, c.text FROM {p}chunk c JOIN {p}passage pa ON pa.id = c.passage_id "
                f"WHERE {urval(roll, 'pa.')} "
                f"ORDER BY c.passage_id, c.chunk_nr")
    lagrade: dict[str, list[str]] = {}
    for passage_id, text in cur.fetchall():
        lagrade.setdefault(passage_id, []).append(text)

    andrade = []
    for passage_id, text in passager:
        nya = embeddings.chunka_text(text) if ar_embeddbar(passage_id, text) else []
        if lagrade.get(passage_id, []) != nya:
            andrade.append((passage_id, nya))
    log.info("%s: %d passager, %d med nya eller ändrade chunkar", roll, len(passager), len(andrade))

    for i in range(0, len(andrade), SKRIVBATCH):
        del_batch = andrade[i : i + SKRIVBATCH]
        with conn:
            cur = conn.cursor()
            # Radering tar bort vektorerna via ON DELETE CASCADE (Postgres)
            # respektive triggern chunk_embedding_del (SQLite)
            cur.executemany(f"DELETE FROM {p}chunk WHERE passage_id = {ph}",
                            [(pid,) for pid, _ in del_batch])
            cur.executemany(
                f"INSERT INTO {p}chunk (passage_id, chunk_nr, text) VALUES ({ph}, {ph}, {ph})",
                [(pid, nr, t) for pid, chunkar in del_batch for nr, t in enumerate(chunkar)],
            )


def chunkar_att_embedda(conn, roll: str) -> list[tuple[int, str]]:
    """Rollens chunkar utan vektor, eller med vektor från en annan modell än rollens."""
    p = db._prefix()
    modell = embeddings.MODELLER[roll]
    cur = conn.cursor()
    cur.execute(f"SELECT chunk_id, modell FROM {p}embedding")
    klara = {chunk_id for chunk_id, m in cur.fetchall() if m == modell}
    cur.execute(f"SELECT c.id, c.text FROM {p}chunk c JOIN {p}passage pa ON pa.id = c.passage_id "
                f"WHERE {urval(roll, 'pa.')} ORDER BY c.id")
    return [(cid, text) for cid, text in cur.fetchall() if cid not in klara]


def spara_vektorer(conn, rader: list[tuple[int, list[float]]], modell: str) -> None:
    """Skriver vektorer; befintliga vektorer för samma chunk ersätts."""
    p, ph = db._prefix(), db._ph()
    with conn:
        cur = conn.cursor()
        if db._ar_postgres():
            # pgvector tolkar textformen '[0.1, 0.2, …]' som vector
            cur.executemany(
                f"INSERT INTO {p}embedding (chunk_id, modell, vektor) VALUES ({ph}, {ph}, {ph}) "
                "ON CONFLICT (chunk_id) DO UPDATE SET modell = excluded.modell, vektor = excluded.vektor",
                [(cid, modell, json.dumps(v)) for cid, v in rader],
            )
        else:
            # vec0-tabeller stöder inte ON CONFLICT
            cur.executemany("DELETE FROM embedding WHERE chunk_id = ?", [(cid,) for cid, _ in rader])
            cur.executemany(
                "INSERT INTO embedding (chunk_id, vektor, modell) VALUES (?, ?, ?)",
                [(cid, db.sqlite_vec.serialize_float32(v), modell) for cid, v in rader],
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Hugging Face-klienten loggar varje HTTP-anrop på INFO-nivå
    logging.getLogger("httpx").setLevel(logging.WARNING)
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--modell", choices=list(embeddings.MODELLER), help="bara den här modellens passager")
    tolk.add_argument("--begransa", type=int, help="bearbeta bara de N första passagerna per modell")
    arg = tolk.parse_args()

    db.initiera_schema()
    conn = db._hamta_db()
    try:
        rensa_utanfor(conn)
        for roll, modell in embeddings.MODELLER.items():
            if arg.modell and roll != arg.modell:
                continue
            synka_chunkar(conn, roll, arg.begransa)
            att_gora = chunkar_att_embedda(conn, roll)
            log.info("%d chunkar att embedda med %s", len(att_gora), modell)

            start = time.monotonic()
            for i in range(0, len(att_gora), SKRIVBATCH):
                batch = att_gora[i : i + SKRIVBATCH]
                vektorer = embeddings.embedda_texter([t for _, t in batch], modell)
                spara_vektorer(conn, list(zip((cid for cid, _ in batch), vektorer)), modell)
                klara = i + len(batch)
                takt = klara / (time.monotonic() - start)
                log.info("%d/%d chunkar (%.0f/s)", klara, len(att_gora), takt)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

"""
Importerar Söderwalls och Schlyters ordböcker ur Språkbankens LMF-filer.

- Söderwall, Ordbok öfver svenska medeltids-språket (1884–1918)
- Söderwall, Supplement (1925–1973)
- Schlyter, Ordbok till Samlingen af Sweriges gamla lagar (1877)

Filerna hämtas till data/raw/soderwall/ om de saknas. Varje betydelse blir
en rad i ordboksartikel. Importen är idempotent.

Användning:
    python importera_ordbocker.py
"""

import html
import json
import logging
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import db
from normalisering import ordform

log = logging.getLogger("importera_ordbocker")

LMF_BAS_URL = os.environ.get("ORDBOK_LMF_BAS_URL", "https://svn.spraakbanken.gu.se/sb-arkiv/pub/lmf")
RAADATA_KATALOG = Path(__file__).parent / "data" / "raw" / "soderwall"

# (kallsamling_id, filnamn hos Språkbanken, namn)
ORDBOCKER = [
    ("schlyter", "schlyter/schlyter.xml",
     "C. J. Schlyter, Ordbok till Samlingen af Sweriges gamla lagar (1877)"),
    ("soderwall", "soederwall/soederwall.xml",
     "K. F. Söderwall, Ordbok öfver svenska medeltids-språket (1884–1918)"),
    ("soderwall_supp", "soederwall-supp/soederwall-supp.xml",
     "K. F. Söderwall, Ordbok öfver svenska medeltids-språket. Supplement (1925–1973)"),
]

# Ord som ofta står i formfälten utan att vara former av uppslagsordet
FUNKTIONSORD = {"för", "och", "med", "jfr", "som", "till", "eller", "the", "thin", "thet", "sik"}


def hamta_fil(relativ: str) -> Path:
    """Laddar ner en LMF-fil till data/raw/soderwall/ om den inte redan finns."""
    RAADATA_KATALOG.mkdir(parents=True, exist_ok=True)
    mal = RAADATA_KATALOG / relativ.rsplit("/", 1)[-1]
    if not mal.exists():
        url = f"{LMF_BAS_URL}/{relativ}"
        log.info("Hämtar %s", url)
        urllib.request.urlretrieve(url, mal)
    return mal


def rensa(text: str) -> str:
    # Filerna är dubbelt kodade (&amp;quot;), så entiteter avkodas här
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def rensa_lemma(text: str) -> str:
    """Tar bort genusbeteckning ('amandol  m') och överflödiga blanksteg."""
    return re.sub(r"\s+[mfn]\.?$", "", rensa(text))


def extrahera_former(texter: list[str], lemma: str) -> list[str]:
    """
    Plockar stavningsvarianter ur formfälten (WordForm, hwtext).

    Fälten blandar former med ställhänvisningar och förkortningar
    ("äär MB 1:294", "(laiþingr, G. lleþing, Sk.)"). Ur varje led, avgränsat
    av komma, semikolon eller parentes, tas det första ord som börjar med
    gemen, har minst tre bokstäver och inte är en förkortning (följs av punkt).
    """
    former: list[str] = []
    for text in texter:
        for led in re.split(r"[;,()\[\]]", rensa(text)):
            for traff in re.finditer(r"(?<![\w-])\*?([^\W\d_A-ZÅÄÖÆØ][^\W\d_]{2,})(\.?)", led):
                ord_, punkt = traff.group(1), traff.group(2)
                if punkt or ord_ in FUNKTIONSORD:
                    continue
                if ord_ != lemma and ord_ not in former:
                    former.append(ord_)
                break
    return former


def las_ordbok(kallsamling_id: str, sokvag: Path) -> list[tuple]:
    """En rad per betydelse: (id, kallsamling, lemma, lemgram, ordklass, nr, definition, former, sokform)."""
    rader = []
    for _, el in ET.iterparse(sokvag, events=("end",)):
        if el.tag != "LexicalEntry":
            continue
        fr = el.find("Lemma/FormRepresentation")
        falt = {f.get("att"): f.get("val") for f in fr.findall("feat")} if fr is not None else {}
        lemma = rensa_lemma(falt.get("writtenForm", ""))
        if not lemma:
            el.clear()
            continue
        formtexter = [f.get("val") for f in el.findall("WordForm/feat") if f.get("att") == "writtenForm"]
        if falt.get("hwtext"):
            formtexter.append(falt["hwtext"])
        former = json.dumps(extrahera_former(formtexter, lemma), ensure_ascii=False)
        lemgram = falt.get("lemgram")

        for nr, betydelse in enumerate(el.findall("Sense"), start=1):
            # Numreringen ("2)") ligger ibland direkt i Sense och texten i
            # Definition; båda tas med i läsordning
            definition = rensa(" ".join(f.get("val") or "" for f in betydelse.iter("feat")
                                        if f.get("att") == "text"))
            artikel_id = betydelse.get("id") or f"{kallsamling_id}--{lemgram}..{nr}"
            rader.append((artikel_id, kallsamling_id, lemma, lemgram, falt.get("partOfSpeech"),
                          nr, definition, former, ordform(lemma)))
        el.clear()
    return rader


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db.initiera_schema()
    conn = db._hamta_db()
    try:
        for kallsamling_id, relativ, namn in ORDBOCKER:
            sokvag = hamta_fil(relativ)
            db.upsert(conn, "kallsamling", ["id", "namn", "utgivare", "url", "licens", "version"],
                      ["id"], [(kallsamling_id, namn, "Språkbanken Text, Göteborgs universitet",
                                f"{LMF_BAS_URL}/{relativ}", "CC BY 4.0", "LMF 2017-09-19")])
            rader = las_ordbok(kallsamling_id, sokvag)
            db.upsert(conn, "ordboksartikel",
                      ["id", "kallsamling_id", "lemma", "lemgram", "ordklass", "betydelse_nr",
                       "definition", "former", "sokform"], ["id"], rader)
            log.info("%-15s %6d betydelser", kallsamling_id, len(rader))
    finally:
        conn.close()


if __name__ == "__main__":
    main()

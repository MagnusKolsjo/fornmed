"""
Chunkning och embeddings.

Två modeller används, var och en för sin del av passagerna:
- EMBEDDING_MODELL (svenska) för regester och översättningar på modern svenska,
- EMBEDDING_MODELL_FLERSPRAK för översättningar till andra moderna språk
  (danska, engelska); se berakna_embeddings för varför latin och fornspråk
  inte embeddas.
Vektorer från olika modeller går inte att jämföra, så varje modell har ett
eget index och söks för sig (se sok.vektorsok). Modellerna laddas först när
de behövs, så att program som bara läser databasen inte betalar för det.
"""

import logging
import os
import threading

log = logging.getLogger(__name__)

EMBEDDING_MODELL = os.environ.get("EMBEDDING_MODELL", "KBLab/sentence-bert-swedish-cased")
EMBEDDING_MODELL_FLERSPRAK = os.environ.get("EMBEDDING_MODELL_FLERSPRAK", "intfloat/multilingual-e5-base")
# Modellernas roller; nyckeln används i koden, värdet är modellens namn i databasen
MODELLER = {"svenska": EMBEDDING_MODELL, "flersprak": EMBEDDING_MODELL_FLERSPRAK}
EMBEDDING_BATCH_STORLEK = int(os.environ.get("EMBEDDING_BATCH_STORLEK", "32"))
CHUNK_MAX_TECKEN = int(os.environ.get("CHUNK_MAX_TECKEN", "800"))
CHUNK_MIN_TECKEN = int(os.environ.get("CHUNK_MIN_TECKEN", "100"))
CHUNK_OVERLAPP_TECKEN = int(os.environ.get("CHUNK_OVERLAPP_TECKEN", "200"))

_modeller: dict = {}
_modell_lock = threading.Lock()


def _hamta_modell(namn: str = EMBEDDING_MODELL):
    """
    Laddar modellen lat — första anropet tar några sekunder, efterföljande är gratis.

    Synkrona MCP-verktyg körs på var sin arbetstråd. Dubbelkontrollerad
    låsning hindrar att två samtidiga första anrop laddar modellen var för
    sig, utan att senare anrop behöver ta låset.
    """
    if namn not in _modeller:
        with _modell_lock:
            if namn not in _modeller:
                from sentence_transformers import SentenceTransformer

                log.info("Laddar embedding-modell: %s", namn)
                _modeller[namn] = SentenceTransformer(namn)
    return _modeller[namn]


def _prefix(namn: str, roll: str) -> str:
    """
    E5-modellerna är tränade med prefixen "query: " och "passage: " och ger
    märkbart sämre träffar utan dem; vanliga SBERT-modeller har inga prefix.
    """
    if "e5" in namn.lower():
        return "query: " if roll == "fraga" else "passage: "
    return ""


def embedda_texter(texter: list[str], namn: str = EMBEDDING_MODELL) -> list[list[float]]:
    """Normaliserade vektorer för en lista passagetexter, i batch."""
    prefix = _prefix(namn, "passage")
    vektorer = _hamta_modell(namn).encode(
        [prefix + t for t in texter],
        batch_size=EMBEDDING_BATCH_STORLEK,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vektorer.tolist()


def embedda_fraga(fraga: str, namn: str = EMBEDDING_MODELL) -> list[float]:
    """Normaliserad vektor för en sökfråga."""
    return _hamta_modell(namn).encode(
        _prefix(namn, "fraga") + fraga, normalize_embeddings=True, show_progress_bar=False
    ).tolist()


def chunka_text(
    text: str,
    max_tecken: int = CHUNK_MAX_TECKEN,
    min_tecken: int = CHUNK_MIN_TECKEN,
    overlapp_tecken: int = CHUNK_OVERLAPP_TECKEN,
) -> list[str]:
    """
    Delar text i överlappande chunks och bryter helst vid meningsslut.

    En text som ryms i en chunk returneras hel oavsett längd — korta regester
    är vanliga och får inte försvinna. Gränsen min_tecken gäller bara
    restbiten i slutet, som slås ihop med föregående chunk om den är för kort.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_tecken:
        return [text]

    chunks: list[str] = []
    start, n = 0, len(text)
    while True:
        slut = min(start + max_tecken, n)
        if n - slut < min_tecken:
            # En kort restbit tas med i den här chunken i stället för att
            # bli en egen stump; chunken blir då högst max + min tecken
            slut = n
        else:
            for tecken in (". ", "? ", "! ", ".\n", "?\n", "!\n"):
                pos = text.rfind(tecken, start + min_tecken, slut)
                if pos != -1:
                    slut = pos + len(tecken)
                    break
        chunks.append(text[start:slut].strip())
        if slut >= n:
            break
        # Nästa chunk börjar overlapp_tecken före slutet; är chunken kortare än
        # överlappet börjar nästa vid slutet, annars hittar sökningen efter
        # meningsslut samma ställe igen och chunkarna krymper ett tecken i taget
        nasta = slut - overlapp_tecken
        start = nasta if nasta > start else slut
    return chunks

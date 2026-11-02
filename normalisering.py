"""
Normalisering av fornsvenska och moderna ordformer för uppslag.

Medeltida stavning varierar kraftigt: härad skrivs hæraþ, häradh och
häraþ, lagman skrivs laghman. Den lösa normaliseringen i ordform() för
dessa till en gemensam form så att ett modernt sökord kan matchas mot
ordböckernas uppslagsord och mot begreppsregistrets termer.
"""

import re
import unicodedata

# Bokstäver som behålls som egna; övriga diakritiska tecken tas bort
_SKYDDADE = {"å": "\x01", "ä": "\x02", "ö": "\x03"}


def _utan_diakritiska(text: str) -> str:
    for tecken, ersattning in _SKYDDADE.items():
        text = text.replace(tecken, ersattning)
    text = "".join(t for t in unicodedata.normalize("NFKD", text) if not unicodedata.combining(t))
    for tecken, ersattning in _SKYDDADE.items():
        text = text.replace(ersattning, tecken)
    return text


def ordform(text: str) -> str:
    """
    Lös normalisering av ett ord eller en fras.

    - gemener; æ → ä, ø → ö, w → v, ð → d
    - þ i början av ett ord → t (þing → ting), annars → d (hæraþ → härad)
    - dh → d, gh → g, th → t (häradh → härad, laghman → lagman)
    - dubbelteckning förenklas (ætt → ät)
    - övriga diakritiska tecken tas bort, utom å, ä och ö

    Normaliseringen är medvetet grov: den ska få fram kandidater, och den
    kan slå ihop ord som är olika. Träffarna i ordboken visas därför alltid
    med sin ursprungliga stavning.
    """
    t = text.casefold().strip()
    t = t.replace("æ", "ä").replace("ø", "ö").replace("w", "v").replace("ð", "d")
    t = re.sub(r"\bþ", "t", t).replace("þ", "d")
    t = re.sub(r"(?<=[dgt])h", "", t)
    t = _utan_diakritiska(t)
    t = re.sub(r"(\w)\1+", r"\1", t)
    return re.sub(r"\s+", " ", t)

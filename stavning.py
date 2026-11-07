"""
Felstavningstolerant uppslag av namn och termer.

Den som söker kan inte alltid stavningen: Anskar ska hitta Ansgar och
Anskarius, Magnus Erikson ska hitta Magnus Eriksson. Här finns ett index
över namnformer och termer där ett ord slås upp på liknande stavning.

Kandidaterna tas fram med trigram (bokstavstripplar) och prövas sedan med
redigeringsavstånd. En form godtas om den skiljer sig med högst en bokstav
per fyra (Anskar och Ansgar skiljer en) eller om den börjar med det sökta
och det sökta har minst fem bokstäver (Anskar och Anskarius).

Indexen byggs första gången de används och ligger kvar i processen. De
läser databasen, som bara ändras vid leveranser, då tjänsten startas om.
"""

import threading
from array import array
from collections import Counter
from collections.abc import Callable

import db
from fragor import _rader, _sokform
from normalisering import ordform

# Kortare ord än så slås inte upp på liknande stavning; de ger för många
# nästan-träffar (by, ö, kung)
MIN_TECKEN = 4

# Så här många bokstäver får det skilja per påbörjat fyratal i ordet
TECKEN_PER_FEL = 4

# Kandidater som prövas med redigeringsavstånd, de med flest gemensamma trigram
KANDIDATER = 200


def _trigram(form: str) -> set[str]:
    utfylld = f"  {form} "
    return {utfylld[i:i + 3] for i in range(len(utfylld) - 2)}


def avstand(a: str, b: str, tak: int) -> int:
    """Levenshteinavstånd, avbrutet när det överstiger tak (då returneras tak + 1)."""
    if abs(len(a) - len(b)) > tak:
        return tak + 1
    foregaende = list(range(len(b) + 1))
    for i, ta in enumerate(a, 1):
        rad = [i]
        for j, tb in enumerate(b, 1):
            rad.append(min(foregaende[j] + 1, rad[j - 1] + 1, foregaende[j - 1] + (ta != tb)))
        if min(rad) > tak:
            return tak + 1
        foregaende = rad
    return foregaende[-1]


def tillatet_avstand(form: str) -> int:
    return max(1, len(form) // TECKEN_PER_FEL)


class Index:
    """Namnformer eller termer med de id de hör till, sökbara på liknande stavning."""

    def __init__(self, former: dict[str, set[str]], normalisera: Callable[[str], str]) -> None:
        self.normalisera = normalisera
        self.former = list(former)
        self.ids = [sorted(former[f]) for f in self.former]
        self.trigram: dict[str, array] = {}
        for nr, form in enumerate(self.former):
            for tri in _trigram(form):
                self.trigram.setdefault(tri, array("I")).append(nr)

    def finns(self, text: str) -> bool:
        """Om texten finns som form i indexet, exakt efter normalisering."""
        if not hasattr(self, "_mangd"):
            self._mangd = set(self.former)
        return self.normalisera(text.strip()) in self._mangd

    def liknande(self, text: str, antal: int = 10) -> list[tuple[str, list[str], int]]:
        """
        Former som liknar text, som (form, id, avstånd), närmast först. Den
        exakta formen räknas inte; den hittar den vanliga sökningen själv.
        """
        sokt = self.normalisera(text.strip())
        if len(sokt) < MIN_TECKEN:
            return []
        traffar = Counter()
        for tri in _trigram(sokt):
            for nr in self.trigram.get(tri, ()):
                traffar[nr] += 1
        tak = tillatet_avstand(sokt)
        ut = []
        for nr, _ in traffar.most_common(KANDIDATER):
            form = self.former[nr]
            if form == sokt:
                continue
            d = avstand(sokt, form, tak)
            if d <= tak:
                ut.append((form, self.ids[nr], d))
            elif len(sokt) >= 5 and form.startswith(sokt):
                ut.append((form, self.ids[nr], tak + 1))
        ut.sort(key=lambda r: (r[2], len(r[0]), r[0]))
        return ut[:antal]


_las = threading.Lock()
_index: dict[str, Index] = {}


def termindex() -> Index:
    """Begreppsregistrets termer och namnformer för begrepp, platser, folk och personer."""
    with _las:
        if "termer" not in _index:
            p = db._prefix()
            former: dict[str, set[str]] = {}
            for r in _rader(f"""SELECT t.sokform, t.entitet_id FROM {p}term t JOIN {p}entitet e ON e.id = t.entitet_id
                                WHERE e.typ IN ('begrepp', 'plats', 'grupp', 'person')"""):
                former.setdefault(r["sokform"], set()).add(r["entitet_id"])
            _index["termer"] = Index(former, ordform)
        return _index["termer"]


def namnindex() -> Index:
    """Sökindexets rubriker och namnformer (sokpost.soknamn), för namnsökningen."""
    with _las:
        if "namn" not in _index:
            p = db._prefix()
            former: dict[str, set[str]] = {}
            for r in _rader(f"SELECT id, soknamn FROM {p}sokpost"):
                for form in r["soknamn"].split(" | "):
                    if form:
                        former.setdefault(form, set()).add(r["id"])
            _index["namn"] = Index(former, _sokform)
        return _index["namn"]

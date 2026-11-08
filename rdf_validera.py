"""
Kontrollerar dumpfilerna från rdf_export.py mot SHACL-formerna i
lankade_data/former.ttl, och gör de kontroller som sträcker sig över flera
poster eller grafer och därför inte går att uttrycka som en form.

Formerna körs på en post i taget: varje fil läses i bitar som aldrig delar
en post (en post är dess URI med alla delnoder under #), så att också den
största källsamlingen går att kontrollera utan att hela filen ligger i
minnet. Kontrollerna över posterna:

- att varje klass och egenskap i Fornmeds namnrum finns i vokabulärgrafen
- att ett ersatt id hänvisar till ett id som inte självt är ersatt
- hur många hänvisningar som går till ersatta id
- vilka Wikidata-objekt som delas av flera entiteter som inte är ersatta
- att passagerna i en maskinöversättning är märkta som maskinöversatta
- att antalet tripler i varje fil stämmer med VoID-beskrivningen
- att ingen URI har ett kodat snedstreck eller frågetecken före #: w3id.org
  vidarebefordrar inte sådana sökvägar (%2F ger 404 och %3F 403)
- att varje EDTF-uttryck följer EDTF och anger datum som finns, och att ett
  intervall inte slutar före det börjar

Skriptet avslutar med felkod om någon form bryts eller en kontroll som
gäller fel (inte varning) slår till.

    python rdf_validera.py rdf/
    python rdf_validera.py rdf/ --urval 0.1 --rapport validering.md
"""

import argparse
import gzip
import logging
import re
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, URIRef

import rdf_uri

log = logging.getLogger("rdf_validera")

FORMER = Path(__file__).parent / "lankade_data" / "former.ttl"
SH = Namespace("http://www.w3.org/ns/shacl#")
ID = rdf_uri.ID
DEF = rdf_uri.DEF

# Så många tripler kontrolleras åt gången. pySHACL:s tid växer med grafens
# storlek, så små bitar är snabbare totalt än en stor graf.
BIT = 20_000

_TERM = re.compile(r'<[^>]*>|"(?:[^"\\]|\\.)*"(?:@[A-Za-z0-9-]+|\^\^<[^>]*>)?|_:\S+')
_DEF_TERM = re.compile(r"<" + re.escape(DEF) + r"([^>#/]+)>")
_WIKIDATA = "<http://www.wikidata.org/entity/"
# Hänvisningar som ska gå till det ersatta id:t: identifieringen som ersatte
# det, och länkar ut som beskriver id:t självt
_EGNA_HANVISNINGAR = {f"<{DEF}entitet>", f"<{DEF}identifieradMed>",
                      "<http://www.w3.org/2004/02/skos/core#exactMatch>"}


# EDTF nivå 0–1 som Fornmed använder: år med fyra siffror, eventuellt med okända
# siffror (153X, 15XX), månad och dag, och osäkerhet (?), ungefärlighet (~) eller
# båda (%). Ett intervall har två sådana datum, där ett får vara okänt (tomt) eller
# öppet (..).
_EDTF_DATUM = re.compile(r"(?P<ar>\d{4}|\d{3}X|\d{2}XX)(?:-(?P<man>\d{2})(?:-(?P<dag>\d{2}))?)?[?~%]?")
_MANADSDAGAR = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _edtf_grans(text: str, slut: bool) -> tuple[int, int, int] | None:
    """(år, månad, dag) för datumets tidigaste eller senaste dag, eller None om det inte är EDTF."""
    m = _EDTF_DATUM.fullmatch(text)
    if not m:
        return None
    ar = int(m["ar"].replace("X", "9" if slut else "0"))
    man = int(m["man"]) if m["man"] else (12 if slut else 1)
    if not 1 <= man <= 12:
        return None
    # Den 29 februari godtas alltid: medeltidens datum följer den julianska kalendern
    dag = int(m["dag"]) if m["dag"] else (_MANADSDAGAR[man - 1] if slut else 1)
    if not 1 <= dag <= _MANADSDAGAR[man - 1]:
        return None
    return ar, man, dag


def edtf_fel(text: str) -> str | None:
    """Varför ett EDTF-uttryck inte duger, eller None om det är giltigt."""
    if "/" not in text:
        return None if _edtf_grans(text, False) else "inte ett EDTF-datum"
    fore, _, efter = text.partition("/")
    if fore in ("", "..") and efter in ("", ".."):
        return "intervall utan gränser"
    borjan = None if fore in ("", "..") else _edtf_grans(fore, False)
    slutet = None if efter in ("", "..") else _edtf_grans(efter, True)
    if (fore not in ("", "..") and borjan is None) or (efter not in ("", "..") and slutet is None):
        return "intervall med en gräns som inte är ett EDTF-datum"
    if borjan and slutet and borjan > slutet:
        return "intervall som slutar före det börjar"
    return None


def _delar(rad: str) -> list[str]:
    """Subjekt, predikat, objekt och graf ur en N-Quads-rad."""
    return _TERM.findall(rad)


def _postens_bas(subjekt: str) -> str:
    """<…/verk/sdhk:1> och <…/verk/sdhk:1#tid> hör till samma post."""
    return subjekt.rstrip(">").split("#", 1)[0]


class Tvarkontroll:
    """Det som samlas in rad för rad och prövas när alla filer är lästa."""

    def __init__(self) -> None:
        self.def_termer: Counter[str] = Counter()
        self.definierade: set[str] = set()
        self.ersatt: dict[str, str] = {}
        self.hanvisningar: Counter[str] = Counter()
        self.wikidata: dict[str, set[str]] = defaultdict(set)
        self.maskinutgavor: set[str] = set()
        self.passage_utgava: dict[str, str] = {}
        self.maskinmarkta: set[str] = set()
        self.void: dict[str, int] = {}
        self.dumpfil: dict[str, str] = {}
        self.antal: Counter[str] = Counter()
        self.edtf: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.oframkomliga: list[str] = []

    def las(self, fil: str, s: str, p: str, o: str) -> None:
        self.antal[fil] += 1
        for term in (p, o):
            m = _DEF_TERM.fullmatch(term)
            if m:
                self.def_termer[m.group(1)] += 1
        if fil == "vokabular.nq.gz":
            m = _DEF_TERM.fullmatch(s)
            if m:
                self.definierade.add(m.group(1))
        if p == "<http://purl.org/dc/terms/isReplacedBy>":
            self.ersatt[s] = o
        elif o.startswith(f"<{ID}entitet/") and p not in _EGNA_HANVISNINGAR:
            self.hanvisningar[o] += 1
        # Bara entiteterna: flera runinskrifter på samma sten har stenens objekt
        if p == "<http://www.w3.org/2004/02/skos/core#exactMatch>" and o.startswith(_WIKIDATA) \
                and s.startswith(f"<{ID}entitet/"):
            self.wikidata[o].add(s)
        if p == f"<{DEF}utgavetyp>" and o.endswith("/utgavetyp/maskinoversattning>"):
            self.maskinutgavor.add(s)
        if p == "<http://www.cidoc-crm.org/cidoc-crm/P106i_forms_part_of>" and o.startswith(f"<{ID}utgava/"):
            self.passage_utgava[s] = o
        if p == f"<{DEF}maskinoversatt>":
            self.maskinmarkta.add(s)
        if p == "<http://rdfs.org/ns/void#triples>" and s.startswith(f"<{rdf_uri.GRAF}"):
            self.void[s] = int(o.split('"')[1])
        for term in (s, o):
            if term.startswith(f"<{ID}"):
                sokvag = term[1:-1].split("#", 1)[0].upper()
                if ("%2F" in sokvag or "%3F" in sokvag) and len(self.oframkomliga) < 100:
                    self.oframkomliga.append(term)
        if p == f"<{DEF}edtf>":
            varde = o[1:].rsplit('"', 1)[0]
            orsak = edtf_fel(varde)
            if orsak and len(self.edtf[orsak]) < 1000:
                self.edtf[orsak].append((s, varde))
        if p == "<http://rdfs.org/ns/void#dataDump>":
            self.dumpfil[s] = o[1:-1].rsplit("/", 1)[1]

    def resultat(self) -> tuple[list[str], list[str]]:
        fel, varningar = [], []

        odefinierade = sorted(t for t in self.def_termer if t not in self.definierade)
        if odefinierade:
            fel.append("Klasser och egenskaper som saknas i vokabulärgrafen: "
                       + ", ".join(f"fm:{t} ({self.def_termer[t]})" for t in odefinierade))

        kedjor = [(a, b) for a, b in self.ersatt.items() if b in self.ersatt]
        egna = [a for a, b in self.ersatt.items() if a == b]
        if kedjor:
            fel.append(f"{len(kedjor)} ersatta id hänvisar till id som självt är ersatt, t.ex. "
                       + "; ".join(f"{a} → {b} → {self.ersatt[b]}" for a, b in kedjor[:5]))
        if egna:
            fel.append(f"{len(egna)} id är ersatta av sig själva, t.ex. {egna[0]}")
        till_ersatta = {u: n for u, n in self.hanvisningar.items() if u in self.ersatt}
        if till_ersatta:
            varningar.append(f"{sum(till_ersatta.values())} hänvisningar går till {len(till_ersatta)} ersatta id, "
                             "t.ex. " + ", ".join(f"{u} ({n})" for u, n in Counter(till_ersatta).most_common(5)))

        delade = {q: sorted(e for e in ent if e not in self.ersatt)
                  for q, ent in self.wikidata.items()}
        delade = {q: e for q, e in delade.items() if len(e) > 1}
        if delade:
            varningar.append(f"{len(delade)} Wikidata-objekt delas av flera entiteter som inte är ersatta, t.ex. "
                             + "; ".join(f"{q[1:-1].rsplit('/', 1)[1]}: {', '.join(e)}"
                                         for q, e in list(delade.items())[:8]))

        omarkta = [p for p, u in self.passage_utgava.items() if u in self.maskinutgavor and p not in self.maskinmarkta]
        if omarkta:
            fel.append(f"{len(omarkta)} passager i maskinöversättningar saknar fm:maskinoversatt, t.ex. {omarkta[0]}")

        if self.oframkomliga:
            fel.append(f"{len(self.oframkomliga)} URI:er har / eller ? i sökvägen och går inte att nå genom "
                       f"w3id.org, t.ex. {self.oframkomliga[0]}")
        for orsak, fall in sorted(self.edtf.items()):
            fel.append(f"EDTF: {len(fall)}{'+' if len(fall) >= 1000 else ''} {orsak}, t.ex. "
                       + "; ".join(f"{s} \"{v}\"" for s, v in fall[:5]))

        for graf, vantat in sorted(self.void.items()):
            fil = self.dumpfil.get(graf)
            if fil and self.antal.get(fil, 0) and self.antal[fil] != vantat:
                fel.append(f"{fil}: {self.antal[fil]} tripler, men VoID anger {vantat}")
        return fel, varningar


def _bitar(fil: Path, kontroll: Tvarkontroll):
    """Bitar av N-Triples-rader ur en N-Quads-fil, delade mellan poster."""
    bit: list[str] = []
    bas = None
    with gzip.open(fil, "rt", encoding="utf-8") as f:
        for rad in f:
            delar = _delar(rad)
            if len(delar) != 4:
                raise ValueError(f"{fil.name}: raden kunde inte läsas: {rad[:200]}")
            s, p, o, _ = delar
            kontroll.las(fil.name, s, p, o)
            ny_bas = _postens_bas(s)
            if len(bit) >= BIT and ny_bas != bas:
                yield bit
                bit = []
            bas = ny_bas
            bit.append(f"{s} {p} {o} .")
    if bit:
        yield bit


def _med(urval: float, bit: list[str]) -> bool:
    """Ett urval som blir detsamma vid varje körning."""
    return urval >= 1 or zlib.crc32(bit[0].encode()) / 2**32 < urval


def kontrollera(katalog: Path, urval: float, hela: set[str]) -> tuple[dict, list[str], list[str], dict]:
    former = Graph().parse(FORMER, format="turtle")
    brott: dict[tuple, dict] = {}
    kontroll = Tvarkontroll()
    statistik: dict[str, tuple[int, int]] = {}
    filer = sorted(katalog.glob("*.nq.gz"))
    if not filer:
        raise SystemExit(f"Inga .nq.gz-filer i {katalog}")
    for fil in filer:
        start, kontrollerade, bitar = time.time(), 0, 0
        # Små filer och filer där formerna jämför poster med varandra prövas hela
        if fil.name in hela:
            delar = [[r for b in _bitar(fil, kontroll) for r in b]]
        else:
            delar = _bitar(fil, kontroll)
        for bit in delar:
            bitar += 1
            if not (fil.name in hela or _med(urval, bit)):
                continue
            kontrollerade += len(bit)
            data = Graph().parse(data="\n".join(bit), format="nt")
            ok, resultat, _ = validate(data, shacl_graph=former, inference="none", allow_warnings=True)
            if ok:
                continue
            for r in resultat.subjects(SH.resultSeverity, None):
                form = resultat.value(r, SH.sourceShape)
                villkor = str(resultat.value(r, SH.sourceConstraintComponent)).rsplit("#", 1)[1]
                nyckel = (fil.name, str(resultat.value(r, SH.resultSeverity)).rsplit("#", 1)[1],
                          _namn(former, form), str(resultat.value(r, SH.resultPath) or ""), villkor)
                post = brott.setdefault(nyckel, {"antal": 0, "exempel": []})
                post["antal"] += 1
                if len(post["exempel"]) < 3:
                    post["exempel"].append((str(resultat.value(r, SH.focusNode)), str(resultat.value(r, SH.value) or ""),
                                            str(resultat.value(r, SH.resultMessage) or "")))
        statistik[fil.name] = (kontroll.antal[fil.name], kontrollerade)
        log.info("%s: %d av %d tripler kontrollerade, %.0f s", fil.name, kontrollerade,
                 kontroll.antal[fil.name], time.time() - start)
    fel, varningar = kontroll.resultat()
    return brott, fel, varningar, statistik


def _namn(former: Graph, form) -> str:
    """Formens namn, eller namnet på den form som en anonym egenskapsform hör till."""
    if isinstance(form, URIRef):
        return str(form).rsplit("/", 1)[1]
    agare = former.value(None, SH.property, form)
    return _namn(former, agare) if agare is not None else "(anonym form)"


def rapport(brott: dict, fel: list[str], varningar: list[str], statistik: dict, urval: float) -> str:
    rader = ["# Validering av Fornmeds länkade data", ""]
    totalt = sum(n for n, _ in statistik.values())
    kontrollerade = sum(k for _, k in statistik.values())
    rader.append(f"{kontrollerade} av {totalt} tripler kontrollerade mot formerna"
                 + (f" (urval {urval:.0%} av bitarna)" if urval < 1 else "") + ".")
    rader += ["", "## Brott mot formerna", ""]
    if not brott:
        rader.append("Inga.")
    for (fil, grad, form, vag, villkor), post in sorted(brott.items(), key=lambda x: (x[0][1] != "Violation", -x[1]["antal"])):
        rader.append(f"- **{grad}** `{fil}` {form} {('`' + vag + '`') if vag else ''} {villkor}: {post['antal']}")
        for nod, varde, meddelande in post["exempel"]:
            rader.append(f"  - {nod}" + (f" → {varde[:120]}" if varde and varde != nod else "") + f" ({meddelande[:160]})")
    rader += ["", "## Kontroller över posterna", ""]
    rader += [f"- **Fel** {t}" for t in fel] + [f"- **Varning** {t}" for t in varningar]
    if not fel and not varningar:
        rader.append("Inga anmärkningar.")
    return "\n".join(rader) + "\n"


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("katalog", type=Path, help="katalogen med dumpfilerna")
    tolk.add_argument("--urval", type=float, default=1.0,
                      help="andel av bitarna i de stora filerna som prövas mot formerna (0–1)")
    tolk.add_argument("--rapport", type=Path, help="skriv rapporten till en fil")
    args = tolk.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Länkarna prövas hela, eftersom formen jämför en entitets alla länkar,
    # och de kommer från flera tabeller i olika ordning
    hela = {"lankar.nq.gz", "metadata.nq.gz", "vokabular.nq.gz"}
    brott, fel, varningar, statistik = kontrollera(args.katalog, args.urval, hela)
    text = rapport(brott, fel, varningar, statistik, args.urval)
    if args.rapport:
        args.rapport.write_text(text, encoding="utf-8")
    print(text)
    if fel or any(k[1] == "Violation" for k in brott):
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Källpaket: det gemensamma formatet mellan källspecifika tolkar och databasen.

En tolk läser en källas eget format (TEI, ren text, HTML) och lämnar ett
Kallpaket med verket, dess utgåvor och passager. ladda() skriver paketet
till databasen idempotent. Paket kan också sparas som JSON och läsas in
igen, så att tolkning och laddning kan köras var för sig.

Passagernas adresser ska vara stabila och citerbara i källans egen
indelning: rad 1–52 i Beowulf, kap. 29 i Ynglinga saga, Kgb 7:1 i en lag.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import db

log = logging.getLogger(__name__)


@dataclass
class Kallsamling:
    id: str
    namn: str
    utgivare: str | None = None
    url: str | None = None
    licens: str | None = None
    version: str | None = None


@dataclass
class Utgava:
    id: str
    referens: str
    licens: str | None = None


@dataclass
class Vittne:
    id: str
    typ: str
    beskrivning: str
    signum: str | None = None
    datering_edtf: str | None = None
    datering_fran: int | None = None
    datering_till: int | None = None


@dataclass
class Passage:
    id: str
    typ: str            # vokabular 'passagetyp': originaltext, oversattning …
    adress: str
    sprak: str          # ISO 639-3; 'fsv' för fornsvenska
    text: str
    ordning: int = 0
    utgava_id: str | None = None
    url: str | None = None          # sidbild eller sida i den digitala utgåvan


@dataclass
class Verk:
    id: str
    titel: str
    genre: str
    sprak: list[str]
    upphov: str | None = None
    datering_edtf: str | None = None
    datering_fran: int | None = None
    datering_till: int | None = None
    beskrivning: str | None = None
    extern_url: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class Kallpaket:
    kallsamling: Kallsamling
    verk: list[Verk]
    utgavor: list[tuple[str, Utgava]] = field(default_factory=list)      # (verk_id, utgåva)
    vittnen: list[tuple[str, Vittne]] = field(default_factory=list)      # (verk_id, vittne)
    passager: list[tuple[str, Passage]] = field(default_factory=list)    # (verk_id, passage)
    # Verk som redan finns i databasen och som paketet bara lägger utgåvor
    # och passager till; de skrivs inte om och byter inte källsamling
    befintliga_verk: list[str] = field(default_factory=list)

    def kontrollera(self) -> None:
        """Fångar fel som annars blir svårtolkade databasfel: dubbletter och lösa referenser."""
        verk_ids = {v.id for v in self.verk} | set(self.befintliga_verk)
        utgava_ids = {u.id for _, u in self.utgavor}
        sett: set[str] = set()
        for verk_id, p in self.passager:
            if verk_id not in verk_ids:
                raise ValueError(f"Passagen {p.id} hör till okänt verk {verk_id}")
            if p.utgava_id and p.utgava_id not in utgava_ids:
                raise ValueError(f"Passagen {p.id} pekar på okänd utgåva {p.utgava_id}")
            if p.id in sett:
                raise ValueError(f"Passagen {p.id} förekommer två gånger")
            if not p.text.strip():
                raise ValueError(f"Passagen {p.id} är tom")
            sett.add(p.id)

    def lagg_till_maskinoversattningar(self, fil: Path, fran_sprak: str) -> int:
        """
        Lägger till svenska översättningar gjorda av språkmodell ur en
        JSON-fil {originalpassagens id: översättning} (se
        data/oversattningar/RIKTLINJER.md). Varje översättning blir en passage
        '<id>:sv' av typen oversattning i en egen utgåva per originalutgåva,
        '<utgåva>:sv_modell', så att den aldrig förväxlas med en tryckt
        översättning. Returnerar antalet tillagda översättningar.
        """
        if not fil.exists():
            return 0
        oversattning = json.loads(fil.read_text(encoding="utf-8"))
        licens = {u.id: u.licens for _, u in self.utgavor}
        nya_utgavor: dict[str, tuple[str, Utgava]] = {}
        nya: list[tuple[str, Passage]] = []
        for verk_id, p in self.passager:
            if p.id not in oversattning:
                continue
            utgava_id = f"{p.utgava_id}:sv_modell"
            nya_utgavor.setdefault(utgava_id, (verk_id, Utgava(
                utgava_id, f"Svensk översättning gjord av språkmodell (Claude) från {fran_sprak}. "
                           "Ogranskad; citera originalet eller en tryckt översättning.",
                licens.get(p.utgava_id))))
            nya.append((verk_id, Passage(
                id=f"{p.id}:sv", typ="oversattning", adress=f"{p.adress} (maskinöversättning)", sprak="swe",
                text=oversattning[p.id], ordning=100000 + p.ordning, utgava_id=utgava_id, url=p.url)))
        saknas = set(oversattning) - {p.id for _, p in self.passager}
        if saknas:
            log.warning("%s: %d översättningar hör inte till någon passage: %s", fil.name, len(saknas),
                        ", ".join(sorted(saknas)[:5]))
        self.utgavor.extend(nya_utgavor.values())
        self.passager.extend(nya)
        return len(nya)

    def spara(self, sokvag: Path) -> None:
        sokvag.parent.mkdir(parents=True, exist_ok=True)
        sokvag.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def las(cls, sokvag: Path) -> "Kallpaket":
        d = json.loads(sokvag.read_text(encoding="utf-8"))
        return cls(
            kallsamling=Kallsamling(**d["kallsamling"]),
            verk=[Verk(**v) for v in d["verk"]],
            utgavor=[(vid, Utgava(**u)) for vid, u in d["utgavor"]],
            vittnen=[(vid, Vittne(**v)) for vid, v in d["vittnen"]],
            passager=[(vid, Passage(**p)) for vid, p in d["passager"]],
            befintliga_verk=d.get("befintliga_verk", []),
        )


def inaktuella_passager(conn, paket: Kallpaket) -> tuple[list[str], list[str]]:
    """
    Passager i paketets utgåvor som paketet inte längre innehåller, uppdelade
    i (kan tas bort, skyddade). En tolk äger sina utgåvor, så det som en ny
    version av tolken inte skapar är inaktuellt. Passager som påståenden
    bygger på skyddas: påståendet skulle annars försvinna med passagen
    (ON DELETE CASCADE) utan att någon märker det.
    """
    utgavor = [u.id for _, u in paket.utgavor]
    if not utgavor:
        return [], []
    p, ph = db._prefix(), db._ph()
    cur = conn.cursor()
    cur.execute(f"SELECT id, EXISTS (SELECT 1 FROM {p}pastaende s WHERE s.passage_id = passage.id) "
                f"FROM {p}passage WHERE utgava_id IN ({', '.join([ph] * len(utgavor))})", utgavor)
    aktuella = {x.id for _, x in paket.passager}
    inaktuella = [(r[0], bool(r[1])) for r in cur.fetchall() if r[0] not in aktuella]
    return (sorted(i for i, skyddad in inaktuella if not skyddad),
            sorted(i for i, skyddad in inaktuella if skyddad))


def ladda(paket: Kallpaket) -> None:
    """
    Skriver ett källpaket till databasen. Idempotent; befintliga rader
    uppdateras och passager som paketets utgåvor inte längre innehåller tas
    bort (se inaktuella_passager).
    """
    paket.kontrollera()
    k = paket.kallsamling
    conn = db._hamta_db()
    try:
        if paket.befintliga_verk:
            cur = conn.cursor()
            ph = db._ph()
            cur.execute(f"SELECT id FROM {db._prefix()}verk WHERE id IN "
                        f"({', '.join([ph] * len(paket.befintliga_verk))})", paket.befintliga_verk)
            saknas = set(paket.befintliga_verk) - {r[0] for r in cur.fetchall()}
            if saknas:
                raise ValueError(f"Verken {', '.join(sorted(saknas))} måste laddas först")
        db.upsert(conn, "kallsamling", ["id", "namn", "utgivare", "url", "licens", "version", "importerad"],
                  ["id"], [(k.id, k.namn, k.utgivare, k.url, k.licens, k.version,
                            datetime.now(timezone.utc).isoformat(timespec="seconds"))])
        db.upsert(conn, "verk",
                  ["id", "kallsamling_id", "titel", "upphov", "genre", "sprak", "datering_edtf",
                   "datering_fran", "datering_till", "beskrivning", "extern_url", "extra"], ["id"],
                  [(v.id, k.id, v.titel, v.upphov, v.genre, db.sprakvarde(v.sprak), v.datering_edtf,
                    v.datering_fran, v.datering_till, v.beskrivning, v.extern_url,
                    json.dumps(v.extra, ensure_ascii=False)) for v in paket.verk])
        db.upsert(conn, "utgava", ["id", "verk_id", "referens", "licens"], ["id"],
                  [(u.id, vid, u.referens, u.licens) for vid, u in paket.utgavor])
        db.upsert(conn, "vittne",
                  ["id", "verk_id", "typ", "beskrivning", "signum", "datering_edtf", "datering_fran",
                   "datering_till"], ["id"],
                  [(w.id, vid, w.typ, w.beskrivning, w.signum, w.datering_edtf, w.datering_fran,
                    w.datering_till) for vid, w in paket.vittnen])
        db.upsert(conn, "passage",
                  ["id", "verk_id", "utgava_id", "typ", "adress", "ordning", "sprak", "text", "url"], ["id"],
                  [(p.id, vid, p.utgava_id, p.typ, p.adress, p.ordning, p.sprak, p.text, p.url)
                   for vid, p in paket.passager])
        bort, skyddade = inaktuella_passager(conn, paket)
        if bort:
            with conn:
                conn.cursor().executemany(f"DELETE FROM {db._prefix()}passage WHERE id = {db._ph()}",
                                          [(i,) for i in bort])
            log.info("%s: %d inaktuella passager borttagna: %s", k.id, len(bort), _urval(bort))
        if skyddade:
            log.warning("%s: %d inaktuella passager har påståenden och ligger kvar: %s",
                        k.id, len(skyddade), _urval(skyddade))
    finally:
        conn.close()
    log.info("%s: %d verk, %d utgåvor, %d passager", k.id, len(paket.verk), len(paket.utgavor),
             len(paket.passager))


def _urval(idn: list[str], antal: int = 10) -> str:
    return ", ".join(idn[:antal]) + (f" … (+{len(idn) - antal})" if len(idn) > antal else "")

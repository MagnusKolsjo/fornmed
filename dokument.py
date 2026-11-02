"""
Hela dokument, delar och språkversioner.

En språkversion är en utgåva av verket. Passager utan utgåva, som SDHK:s
regester, bildar en egen version per passagetyp. Versionen väljs med
utgåvans id, med språk i prioritetsordning eller, utan något av dem, som
originalspråkets huvudtext.

Ett dokument hämtas som en helhet: alla passager i versionen i ordning, eller
alla passager i en del (bok, balk, saga), eller ett avsnitt mellan två
passager. En utgåva som är större än MAX_TECKEN_HELT skickas inte hel; den
som anropar får då verkets delar att hämta i stället.

Funktionerna returnerar vanliga dict och kastar DokumentFel med en kod som
API:et översätter till HTTP-status.
"""

import re

import db
from fragor import _en, _rader, _sprak

# Över den här storleken skickas en utgåva inte i ett svar. Den största i
# databasen (Olaus Magnus) är 2,1 miljoner tecken.
MAX_TECKEN_HELT = 10_000_000

# Ordningen när flera versioner finns på samma språk
TYPORDNING = {"original": 0, "oversattning": 1, "maskintranskription": 2,
              "maskinoversattning": 3, "regest": 4}

OGRANSKAD = {
    "maskinoversattning": ("Översättningen är gjord av en språkmodell och är ogranskad. "
                           "Den får inte citeras som översättning; hänvisa till originalet."),
    "maskintranskription": ("Texten är avläst från sidbilder av en språkmodell och är ogranskad. "
                            "Kontrollera mot sidbilden innan den citeras."),
}


class DokumentFel(Exception):
    """Fel som API:et visar för den som anropar. `kod` är HTTP-statusen (400, 404, 406, 413)."""

    def __init__(self, kod: int, meddelande: str, **detaljer) -> None:
        super().__init__(meddelande)
        self.kod = kod
        self.meddelande = meddelande
        self.detaljer = detaljer


def _verk(verk_id: str) -> dict:
    p, ph = db._prefix(), db._ph()
    verk = _en(
        f"""
        SELECT v.id, v.titel, v.upphov, v.genre, v.datering_edtf, v.extern_url AS url,
               k.id AS kallsamling_id, k.namn AS kallsamling, k.licens AS kallsamling_licens
        FROM {p}verk v LEFT JOIN {p}kallsamling k ON k.id = v.kallsamling_id
        WHERE v.id = {ph}
        """,
        (verk_id,),
    )
    if verk is None:
        raise DokumentFel(404, f"Verket '{verk_id}' finns inte.")
    return verk


def versioner(verk_id: str) -> list[dict]:
    """Verkets språkversioner med språk, typ, roll, licens och omfång."""
    verk = _verk(verk_id)
    p, ph = db._prefix(), db._ph()
    rader = _rader(
        f"""
        SELECT u.id AS utgava_id, u.referens, u.sprak AS utgavesprak, u.typ, u.roll,
               u.oversattare, u.ar, u.licens, pa.typ AS passagetyp, pa.sprak,
               count(*) AS antal_passager, sum(length(pa.text)) AS tecken
        FROM {p}passage pa LEFT JOIN {p}utgava u ON u.id = pa.utgava_id
        WHERE pa.verk_id = {ph}
        GROUP BY u.id, u.referens, u.sprak, u.typ, u.roll, u.oversattare, u.ar, u.licens,
                 pa.typ, pa.sprak
        """,
        (verk_id,),
    )
    samlade: dict[str, dict] = {}
    for r in rader:
        # Passager utan utgåva (SDHK:s regester) blir en version per passagetyp
        nyckel = r["utgava_id"] or r["passagetyp"]
        v = samlade.setdefault(nyckel, {
            "utgava": nyckel,
            "utgava_id": r["utgava_id"],
            "referens": r["referens"],
            "typ": r["typ"] or ("regest" if r["passagetyp"] == "regest" else "original"),
            "roll": r["roll"] or "huvudtext",
            "oversattare": r["oversattare"],
            "ar": r["ar"],
            "licens": r["licens"] or verk["kallsamling_licens"],
            "sprak": r["utgavesprak"],
            "passagesprak": set(),
            "antal_passager": 0,
            "tecken": 0,
        })
        if r["sprak"]:
            v["passagesprak"].add(r["sprak"])
        v["antal_passager"] += r["antal_passager"]
        v["tecken"] += r["tecken"] or 0
    svar = []
    for v in samlade.values():
        v["passagesprak"] = sorted(v["passagesprak"])
        if v["sprak"] is None and len(v["passagesprak"]) == 1:
            v["sprak"] = v["passagesprak"][0]
        v["ogranskad"] = v["typ"] in OGRANSKAD
        svar.append(v)
    svar.sort(key=lambda v: (v["roll"] != "huvudtext", TYPORDNING.get(v["typ"], 9),
                             -v["antal_passager"], v["utgava"]))
    return svar


def valj_version(verk_id: str, sprak: list[str] | None = None, utgava: str | None = None,
                 roll: str | None = None) -> tuple[dict, str | None]:
    """(version, språkfilter) för en hämtning.

    Språkfiltret är satt när versionen har flera språk (runinskrifterna) och
    bara passagerna på det begärda språket ska med.
    """
    alla = versioner(verk_id)
    if utgava:
        for v in alla:
            if v["utgava"] == utgava:
                return v, None
        raise DokumentFel(404, f"Utgåvan '{utgava}' finns inte för verket.",
                          versioner=_kortlista(alla))

    kandidater = [v for v in alla if roll is None or v["roll"] == roll]
    if not kandidater:
        raise DokumentFel(404, f"Verket har ingen version med rollen '{roll}'.",
                          versioner=_kortlista(alla))

    if not sprak:
        # Originalspråket: första versionen efter sorteringen, där originalet
        # går före översättningar
        return kandidater[0], None

    for kod in sprak:
        for v in kandidater:
            if v["sprak"] == kod:
                return v, None
        for v in kandidater:
            if v["sprak"] is None and kod in v["passagesprak"]:
                return v, kod
    finns = sorted({s for v in kandidater for s in ([v["sprak"]] if v["sprak"] else v["passagesprak"])})
    raise DokumentFel(404, f"Verket finns inte på {', '.join(sprak)}.", sprak=finns,
                      versioner=_kortlista(alla))


def _kortlista(alla: list[dict]) -> list[dict]:
    return [{"utgava": v["utgava"], "sprak": v["sprak"] or v["passagesprak"], "typ": v["typ"],
             "roll": v["roll"]} for v in alla]


def _passager(verk_id: str, version: dict, sprakfilter: str | None, del_: str | None,
              fran: str | None, till: str | None) -> list[dict]:
    p, ph = db._prefix(), db._ph()
    villkor = [f"pa.verk_id = {ph}"]
    param: list = [verk_id]
    if version["utgava_id"]:
        villkor.append(f"pa.utgava_id = {ph}")
        param.append(version["utgava_id"])
    else:
        villkor.append(f"pa.utgava_id IS NULL AND pa.typ = {ph}")
        param.append(version["utgava"])
    if sprakfilter:
        villkor.append(f"pa.sprak = {ph}")
        param.append(sprakfilter)
    if del_:
        villkor.append(f"pa.del = {ph}")
        param.append(del_)
    for passage_id, jamforelse in ((fran, ">="), (till, "<=")):
        if passage_id:
            ordning = _en(f"SELECT ordning FROM {p}passage WHERE id = {ph}", (passage_id,))
            if ordning is None:
                raise DokumentFel(404, f"Passagen '{passage_id}' finns inte.")
            villkor.append(f"pa.ordning {jamforelse} {ph}")
            param.append(ordning["ordning"])
    return _rader(
        f"""
        SELECT pa.id, pa.adress, pa.del, pa.del_typ, pa.typ, pa.sprak, pa.text,
               pa.url AS underlag_url
        FROM {p}passage pa
        WHERE {' AND '.join(villkor)}
        ORDER BY pa.ordning, pa.id
        """,
        param,
    )


def hamta_text(verk_id: str, sprak: list[str] | None = None, utgava: str | None = None,
               roll: str | None = None, del_: str | None = None, fran: str | None = None,
               till: str | None = None) -> dict:
    """Ett verk, en del av det eller ett avsnitt i den valda språkversionen."""
    verk = _verk(verk_id)
    version, sprakfilter = valj_version(verk_id, sprak, utgava, roll)
    if not (del_ or fran or till) and version["tecken"] > MAX_TECKEN_HELT:
        raise DokumentFel(413, "Utgåvan är för stor för ett svar. Hämta den del för del.",
                          delar=hamta_delar(verk_id, sprak, utgava, roll)["delar"])
    passager = _passager(verk_id, version, sprakfilter, del_, fran, till)
    if del_ and not passager:
        raise DokumentFel(404, f"Delen '{del_}' finns inte i versionen.",
                          delar=[d["del"] for d in hamta_delar(verk_id, sprak, utgava, roll)["delar"]])
    return {
        "verk": _verkuppgifter(verk),
        "version": _versionsuppgifter(version, sprakfilter),
        "del": del_,
        "antal_passager": len(passager),
        "tecken": sum(len(pa["text"]) for pa in passager),
        "passager": passager,
    }


def hamta_delar(verk_id: str, sprak: list[str] | None = None, utgava: str | None = None,
                roll: str | None = None) -> dict:
    """Verkets delar i den valda versionen, i den ordning de börjar."""
    verk = _verk(verk_id)
    version, sprakfilter = valj_version(verk_id, sprak, utgava, roll)
    p, ph = db._prefix(), db._ph()
    villkor = [f"verk_id = {ph}", "del IS NOT NULL"]
    param: list = [verk_id]
    if version["utgava_id"]:
        villkor.append(f"utgava_id = {ph}")
        param.append(version["utgava_id"])
    if sprakfilter:
        villkor.append(f"sprak = {ph}")
        param.append(sprakfilter)
    delar = _rader(
        f"""
        SELECT del, del_typ, count(*) AS antal_passager, sum(length(text)) AS tecken,
               min(ordning) AS forsta
        FROM {p}passage WHERE {' AND '.join(villkor)}
        GROUP BY del, del_typ ORDER BY min(ordning)
        """,
        param,
    )
    for d in delar:
        d.pop("forsta")
    return {"verk": _verkuppgifter(verk), "version": _versionsuppgifter(version, sprakfilter),
            "delar": delar}


def hamta_parallellt(verk_id: str, sprak: list[str], del_: str | None = None,
                     fran: str | None = None, till: str | None = None) -> dict:
    """Samma passager på flera språk, ihopparade per passage.

    Översättningarnas passager har originalets id med ett språksuffix
    (`…:sv`), och paras ihop på det. Saknar en version sådana id paras
    passagerna i ordning, när versionerna har lika många passager.
    """
    if len(sprak) < 2:
        raise DokumentFel(406, "Parallell text kräver minst två språk, t.ex. sprak=fsv,swe.")
    verk = _verk(verk_id)
    texter = []
    for kod in sprak:
        version, sprakfilter = valj_version(verk_id, [kod])
        texter.append((kod, version, sprakfilter,
                       _passager(verk_id, version, sprakfilter, del_, None, None)))

    def nyckel(passage_id: str) -> str:
        return re.sub(r":(sv|en|da|de)$", "", passage_id)

    bas = texter[0][3]
    per_nyckel = [{nyckel(pa["id"]): pa for pa in passager} for *_, passager in texter]
    par_pa_id = any(all(k in d for d in per_nyckel[1:]) for k in per_nyckel[0])
    if not par_pa_id and len({len(passager) for *_, passager in texter}) != 1:
        raise DokumentFel(406, "Versionerna går inte att para ihop passage för passage. "
                               "Hämta dem var för sig.")

    rader = []
    for i, pa in enumerate(bas):
        rad = {"adress": pa["adress"], "del": pa["del"]}
        for (kod, _version, _filter, passager), d in zip(texter, per_nyckel):
            motsvarande = d.get(nyckel(pa["id"])) if par_pa_id else passager[i]
            rad[kod] = {"id": motsvarande["id"], "text": motsvarande["text"]} if motsvarande else None
        rader.append(rad)

    if fran or till:
        ids = [pa["id"] for pa in bas]
        start = ids.index(fran) if fran in ids else 0
        slut = ids.index(till) + 1 if till in ids else len(ids)
        rader = rader[start:slut]

    return {
        "verk": _verkuppgifter(verk),
        "versioner": {kod: _versionsuppgifter(v, f) for kod, v, f, _ in texter},
        "del": del_,
        "sprak": sprak,
        "antal_passager": len(rader),
        "passager": rader,
    }


def hamta_passage(passage_id: str) -> dict:
    """En passage med hela texten, dess språkversion och påståendena ur den.

    Versionen följer med så att en maskinöversatt passage alltid bär sin
    anmärkning, också när den hämtas direkt med sitt id.
    """
    p, ph = db._prefix(), db._ph()
    rad = _en(f"SELECT verk_id, utgava_id, typ FROM {p}passage WHERE id = {ph}", (passage_id,))
    if rad is None:
        raise DokumentFel(404, f"Passagen '{passage_id}' finns inte.")
    nyckel = rad["utgava_id"] or rad["typ"]
    version = next(v for v in versioner(rad["verk_id"]) if v["utgava"] == nyckel)
    passage = _en(
        f"""
        SELECT id, adress, del, del_typ, typ, sprak, text, url AS underlag_url
        FROM {p}passage WHERE id = {ph}
        """,
        (passage_id,),
    )
    passage["pastaenden"] = _rader(
        f"SELECT id, subjekt_id, predikat, objekt_id, objekt_varde, tid_edtf "
        f"FROM {p}pastaende WHERE passage_id = {ph} ORDER BY id",
        (passage_id,),
    )
    sprakfilter = passage["sprak"] if version["sprak"] is None else None
    return {"verk": _verkuppgifter(_verk(rad["verk_id"])),
            "version": _versionsuppgifter(version, sprakfilter), "passage": passage}


def hamta_passage_pa_sprak(passage_id: str, sprak: list[str]) -> dict:
    """Samma passage i den första språkversion som finns av de begärda."""
    p, ph = db._prefix(), db._ph()
    passage = _en(f"SELECT verk_id FROM {p}passage WHERE id = {ph}", (passage_id,))
    if passage is None:
        raise DokumentFel(404, f"Passagen '{passage_id}' finns inte.")
    verk_id = passage["verk_id"]
    bas = re.sub(r":(sv|en|da|de)$", "", passage_id)
    for kod in sprak:
        version, sprakfilter = valj_version(verk_id, [kod])
        for pa in _passager(verk_id, version, sprakfilter, None, None, None):
            if re.sub(r":(sv|en|da|de)$", "", pa["id"]) == bas:
                return {"verk": _verkuppgifter(_verk(verk_id)),
                        "version": _versionsuppgifter(version, sprakfilter), "passage": pa}
    raise DokumentFel(404, f"Passagen finns inte på {', '.join(sprak)}.",
                      versioner=_kortlista(versioner(verk_id)))


def _verkuppgifter(verk: dict) -> dict:
    return {k: verk[k] for k in ("id", "titel", "upphov", "genre", "datering_edtf", "url",
                                 "kallsamling_id", "kallsamling")}


def _versionsuppgifter(version: dict, sprakfilter: str | None) -> dict:
    uppgifter = {k: version[k] for k in ("utgava", "referens", "typ", "roll", "oversattare",
                                         "ar", "licens", "ogranskad")}
    uppgifter["sprak"] = sprakfilter or version["sprak"] or version["passagesprak"]
    if version["typ"] in OGRANSKAD:
        uppgifter["anmarkning"] = OGRANSKAD[version["typ"]]
    return uppgifter


def lista_verk(kallsamling: str | None = None, genre: str | None = None, sprak: str | None = None,
               ar_fran: int | None = None, ar_till: int | None = None, titel: str | None = None,
               sida: int = 1, per_sida: int = 100) -> tuple[list[dict], int]:
    """(verk på sidan, totalt antal) med filter på källsamling, genre, språk, datering och titel.

    Dateringen filtreras på överlappande intervall, som i sökningen:
    odaterade verk faller bort när ar_fran eller ar_till anges.
    """
    p, ph = db._prefix(), db._ph()
    villkor, param = [], []
    if kallsamling:
        villkor.append(f"v.kallsamling_id = {ph}")
        param.append(kallsamling)
    if genre:
        villkor.append(f"v.genre = {ph}")
        param.append(genre)
    if sprak:
        # TEXT[] i Postgres, JSON-text i SQLite
        villkor.append(f"{ph} = ANY(v.sprak)" if db._ar_postgres() else f"v.sprak LIKE {ph}")
        param.append(sprak if db._ar_postgres() else f'%"{sprak}"%')
    if ar_fran is not None:
        villkor.append(f"v.datering_till >= {ph}")
        param.append(ar_fran * 10000)
    if ar_till is not None:
        villkor.append(f"v.datering_fran <= {ph}")
        param.append(ar_till * 10000 + 1231)
    if titel:
        villkor.append(f"lower(v.titel) LIKE {ph}")
        param.append(f"%{titel.lower()}%")
    where = f"WHERE {' AND '.join(villkor)}" if villkor else ""
    total = _en(f"SELECT count(*) AS n FROM {p}verk v {where}", param)["n"]
    rader = _rader(
        f"""
        SELECT v.id, v.titel, v.upphov, v.genre, v.sprak, v.datering_edtf, v.kallsamling_id
        FROM {p}verk v {where}
        ORDER BY v.kallsamling_id, v.datering_fran NULLS LAST, v.id
        LIMIT {ph} OFFSET {ph}
        """,
        [*param, per_sida, (sida - 1) * per_sida],
    )
    for r in rader:
        r["sprak"] = _sprak(r["sprak"])
    return rader, total

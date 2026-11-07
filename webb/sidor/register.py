"""
Registrets sidor: en sida per person, plats, institution, ämbete, folk och begrepp.

Uppgifterna hämtas från API:et: entiteten med namnformer, identifieringar och
påståenden (/v1/entiteter/{id}) och sökindexets tider och platser
(/v1/sok/objekt/{id}). Påståendena visas med länkar till källan och till de
andra entiteterna, så att man kan gå från en person till ett brev, därifrån
till en plats och vidare.
"""

import re
import urllib.parse

from django.conf import settings

from . import kallor, klartext, lankar, sokning, texter

PASTAENDEN_PER_SIDA = 50

# Så många platser, identifieringar och namnar visas innan resten fälls ihop
FORSTA = 3

# Ett objektvärde som är ett verks id, t.ex. sdhk:41606 för det brev en person utfärdar
VERK_ID = re.compile(r"^(sdhk|df|dn):\d[\d:]*$|^verk:[\w:]+$")


def _verknamn(verk_id: str) -> str:
    """sdhk:41606 som SDHK nr 41606 och dn:1:2 som DN 1 nr 2, som verkens titlar skrivs."""
    delar = verk_id.split(":")
    if delar[0] in ("sdhk", "df", "dn"):
        return f"{delar[0].upper()} {' '.join(delar[1:-1])} nr {delar[-1]}".replace("  ", " ")
    return verk_id


def _etiketter(schema: str) -> dict[str, str]:
    try:
        return {r["kod"]: r["etikett"] for r in texter._hamta(f"/v1/vokabularer/{schema}")}
    except texter.TextFel:
        return {}


def _vag(entitet_id: str) -> str:
    return "/v1/entiteter/" + urllib.parse.quote(entitet_id, safe=":")


def entitetens_sida(entitet_id: str, fran: int) -> dict:
    """Allt som mallen för en entitet behöver. TextFel med kod 404 om entiteten inte finns."""
    adresser = lankar.sidor()
    entitet = texter._hamta(_vag(entitet_id), antal=PASTAENDEN_PER_SIDA, fran=fran)
    try:
        post = texter._hamta("/v1/sok/objekt/" + urllib.parse.quote(entitet_id, safe=":"))
    except texter.TextFel:
        post = None
    predikat = _etiketter("predikat")
    entitetstyper = _etiketter("entitetstyp")

    def entitetslank(id_: str | None, namn: str | None) -> dict | None:
        if not id_:
            return None
        return {"namn": namn or id_, "url": lankar.entitet_url(id_, adresser), "denna": id_ == entitet_id}

    pastaenden = []
    for p in entitet["pastaenden"]:
        objekt = entitetslank(p["objekt_id"], p.get("objekt"))
        if objekt is None and p["objekt_varde"]:
            if VERK_ID.match(p["objekt_varde"]):
                objekt = {"namn": _verknamn(p["objekt_varde"]), "url": lankar.verk_url(p["objekt_varde"], adresser),
                          "denna": False}
            else:
                objekt = {"namn": p["objekt_varde"], "url": None, "denna": False}
        pastaenden.append({
            "subjekt": entitetslank(p["subjekt_id"], p.get("subjekt")),
            "predikat": predikat.get(p["predikat"], p["predikat"].replace("_", " ")),
            "objekt": objekt,
            "plats": entitetslank(p.get("plats_id"), p.get("plats")),
            "tid": kallor.datering(p.get("tid_edtf")) or "",
            "kalla": {"titel": p["verk_titel"], "url": lankar.verk_url(p["verk_id"], adresser) if p.get("verk_id") else None},
            "tidsavstand": p.get("tidsavstand_ar"),
            "omstridd": p.get("omstridd"),
            "antal_bedomningar": p.get("antal_bedomningar"),
            "titulatur": klartext.etikett("titulatur", p.get("titulatur")),
        })

    sammanfattning = [{
        "predikat": predikat.get(s["predikat"], s["predikat"]), "roll": s["roll"], "antal": s["antal"],
        "ar": sokning._arspann(s.get("fran_ar"), s.get("till_ar")),
    } for s in entitet.get("sammanfattning", [])]

    namnformer = [{**n, "url": lankar.verk_url(n["verk_id"], adresser) if n.get("verk_id") else None,
                   "verk_namn": _verknamn(n["verk_id"]) if n.get("verk_id") else None}
                  for n in entitet.get("namnformer", [])]

    identifieringar = [{
        "annan": entitetslank(i["annan_entitet_id"], i.get("annan_entitet")),
        "kommentar": klartext.etikett("titulatur", i.get("kommentar")),
        "bedomningar": [{**b, "text": klartext.bedomning(b["aspekt"], b["varde"], b.get("bedomare"))}
                        for b in i.get("bedomningar", [])],
    } for i in entitet.get("identifieringar", [])]

    # Andra entiteter med exakt samma namn: ofta samma person i olika källor,
    # som ännu inte identifierats med varandra
    try:
        namne = texter._hamta("/v1/sok/objekt", q=entitet["namn"], objekttyp="entitet", undertyp=entitet["typ"],
                              per_sida=50, fasetter="false")["poster"]
    except texter.TextFel:
        namne = []
    namne = [{"namn": n["rubrik"], "url": lankar.entitet_url(n["id"], adresser), "beskrivning": n["sammanfattning"],
              "tid": sokning._arspann((n["tid"].get("visas") or {}).get("fran"), (n["tid"].get("visas") or {}).get("till"))}
             for n in namne if n["rubrik"] == entitet["namn"] and n["id"] != entitet_id]

    plats = entitet.get("plats_uppgift")
    hierarki = []
    if plats:
        for nyckel, rubrik in (("ingar_i", "Ingår i"), ("socken", "Socken"), ("kommun", "Kommun"),
                               ("lan", "Län"), ("landskap", "Landskap"), ("land", "Land")):
            if plats.get(nyckel + "_id"):
                hierarki.append((rubrik, entitetslank(plats[nyckel + "_id"], plats.get(nyckel))))

    platser, kartpunkter = [], []
    if post:
        for p in post["platser"]:
            platser.append({**p, "url": lankar.entitet_url(p["plats_id"], adresser),
                            "roll_text": sokning.PLATSROLLER.get(p["roll"], p["roll"])})
            if p["latitud"] is not None:
                kartpunkter.append({"plats_id": p["plats_id"], "namn": p["namn"], "latitud": p["latitud"],
                                    "longitud": p["longitud"], "antal": p["antal"],
                                    "url": lankar.entitet_url(p["plats_id"], adresser)})

    soksida = sokning.soksidans_url()
    primara = [p for p in platser if p["primar"] and p["roll"] != "lage"]
    visas = (post or {}).get("tid", {}).get("visas") or {}
    return {
        "entitet": entitet,
        "typ": entitetstyper.get(entitet["typ"], sokning.TYPNAMN.get(entitet["typ"], entitet["typ"])),
        "tid": sokning._arspann(visas.get("fran"), visas.get("till")),
        "platser": platser,
        "kartpunkter": kartpunkter,
        "plats": plats,
        "hierarki": hierarki,
        "namnformer": namnformer,
        "identifieringar": identifieringar,
        "namne": namne[:FORSTA],
        "antal_namne": len(namne),
        "namne_url": (f"{soksida}?{urllib.parse.urlencode({'q': entitet['namn'], 'objekttyp': 'entitet', 'undertyp': entitet['typ']})}"
                      if soksida else None),
        "primara_platser": primara[:FORSTA],
        "ovriga_platser": primara[FORSTA:],
        "antal_primara_platser": len(primara),
        "sammanfattning": sammanfattning,
        "pastaenden": pastaenden,
        "pastaenden_totalt": entitet["pastaenden_totalt"],
        "fran": fran,
        "foregaende": max(0, fran - PASTAENDEN_PER_SIDA) if fran > 0 else None,
        "nasta": entitet.get("fortsatt_fran"),
        "sok_namn": f"{soksida}?{urllib.parse.urlencode({'q': entitet['namn']})}" if soksida else None,
        "sok_plats": (f"{soksida}?{urllib.parse.urlencode({'plats': entitet_id, 'platsroll': 'primar'})}"
                      if soksida and entitet["typ"] in ("plats", "indelning") else None),
        "entitet_api_url": f"{settings.API_URL}{_vag(entitet_id)}",
    }

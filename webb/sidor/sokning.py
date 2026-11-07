"""
Söksidan: fråga, filter, fasetter, karta och tidslinje.

Sökningen görs av API:ets /v1/sok/objekt, som läser söktjänstens sökindex.
Här översätts formulärets fält till API:ets parametrar och svaret till det
som mallen ritar: träffkort med typ, tid och plats, fasetter som länkar,
staplar för tidslinjen och punkter för kartan.

Det som visas först är när och var påståendena säger att något hände.
Tillkomst, förlaga och förvaring finns med i varje träffkort och visas när
läsaren slår på de textkritiska uppgifterna.
"""

import math
import urllib.parse

from . import klartext, lankar, texter

PER_SIDA = 20

# Formulärets fält som går vidare till API:et
FALT = ("q", "objekttyp", "undertyp", "kallsamling", "ar_fran", "ar_till", "tidsaxel", "plats", "platsroll")

TYPNAMN = {
    "diplom": "Brev", "runinskrift": "Runinskrift", "saga": "Saga", "eddadikt": "Eddadikt", "lag": "Lag",
    "kronika": "Krönika", "geografi": "Geografi", "annal": "Annal", "hjaltedikt": "Hjältedikt",
    "legend": "Legend", "furstespegel": "Furstespegel", "skaldedikt": "Skaldedikt", "undersamling": "Samling",
    "person": "Person", "plats": "Plats", "indelning": "Indelning", "institution": "Institution",
    "ambete": "Ämbete", "begrepp": "Begrepp", "grupp": "Folk eller grupp",
    "verk": "Dokument", "entitet": "Person, plats eller begrepp",
}

TIDSAXLAR = {
    "primar": "Händelse, annars tillkomst",
    "handelse": "När det hände",
    "tillkomst": "När källan skrevs",
    "forlaga": "Äldsta bevarade vittne",
}

PLATSROLLER = {
    "handelse": "händelse", "tillkomst": "skrevs", "forvaring": "förvaras", "lage": "läge",
}

VITTNESTYPER = {
    "original": "original", "handskrift": "handskrift", "medeltida_avskrift": "medeltida avskrift",
    "medeltida_registratur": "medeltida registratur", "eftermedeltida_avskrift": "eftermedeltida avskrift",
    "eftermedeltida_registratur": "eftermedeltida registratur", "tryck": "tryck",
}

# Passagernas språk (ISO 639-3) som språkkoder för lang-attributet (BCP 47).
# Svenska behöver inget, eftersom sidan är på svenska. Fornsvenska saknar egen
# registrerad kod och märks som svenska, som ger rätt uttal i skärmläsare.
SPRAKKODER = {
    "lat": "la", "dan": "da", "eng": "en", "deu": "de", "nor": "no", "isl": "is", "fin": "fi",
    "fra": "fr", "ita": "it", "nld": "nl", "ara": "ar", "non": "non", "ang": "ang", "gml": "gml",
    "grc": "grc", "fsv": "sv",
}

FASETTRUBRIKER = (("objekttyp", "Typ"), ("undertyp", "Slag"), ("kallsamling", "Källsamling"),
                  ("landskap", "Landskap"), ("land", "Land"))


def _arspann(fran: int | None, till: int | None) -> str:
    if fran is None:
        return ""
    if till is None or till == fran:
        return str(fran)
    return f"{fran}–{till}"


def _lank(param: dict, **andrat) -> str:
    """
    Söksidans adress med de nuvarande parametrarna, ändrade; None tar bort
    en parameter. Sidnumret följer bara med när det anges, så att ett nytt
    filter börjar på första sidan.
    """
    ny = {**param, **andrat}
    return "?" + urllib.parse.urlencode({k: v for k, v in ny.items() if v not in (None, "")})


def _traff(t: dict, adresser: dict, param: dict) -> dict:
    """Ett träffkort: rubrik, länk, etiketter för typ, tid och plats och de textkritiska uppgifterna."""
    tid = t["tid"]
    visas = tid.get("visas") or {}
    primara = [p for p in t["platser"] if p["primar"]]
    # Samma plats i en annan roll (en orts eget läge och händelser där) visas en gång
    ovriga = [p for p in t["platser"] if not p["primar"] and p["plats_id"] not in {q["plats_id"] for q in primara}]

    url = lankar.objekt_url(t["id"], t["objekttyp"], adresser) or ""

    def plats_text(p: dict) -> str:
        delar = [p["namn"]]
        if p.get("landskap") and p["landskap"] != p["namn"]:
            delar.append(p["landskap"])
        elif p.get("land") and p["land"] != p["namn"]:
            delar.append(p["land"])
        return ", ".join(delar)

    textkritik = []
    if tid.get("tillkomst"):
        textkritik.append(("Skriven", _arspann(tid["tillkomst"]["fran"], tid["tillkomst"]["till"])))
    if tid.get("forlaga"):
        f = tid["forlaga"]
        textkritik.append(("Äldsta vittne", f"{_arspann(f['fran'], f['till'])} "
                                            f"({VITTNESTYPER.get(f.get('vittnestyp'), f.get('vittnestyp') or '')})"))
    if tid.get("handelse"):
        textkritik.append(("Händelser", f"{_arspann(tid['handelse']['fran'], tid['handelse']['till'])}, "
                                        f"{t['antal_pastaenden']} påståenden"))
    for roll, rubrik in (("tillkomst", "Skrevs i"), ("forvaring", "Förvaras i"), ("handelse", "Andra platser")):
        namn = [plats_text(p) for p in ovriga if p["roll"] == roll]
        if namn:
            textkritik.append((rubrik, "; ".join(namn)))
    for b in t.get("bedomningar", []):
        ruta = klartext.bedomningsruta(b)
        text = ruta["etikett"].split(": ", 1)[-1].capitalize()
        if ruta["kalla"]:
            text += f" enligt {ruta['kalla']}"
        if ruta["motivering"]:
            text += f". {ruta['motivering']}"
        if ruta["vittne"]:
            text = f"{ruta['etikett']} ({ruta['vittne']}) enligt {ruta['kalla']}" + (
                f". {ruta['motivering']}" if ruta["motivering"] else "")
        textkritik.append((ruta["aspekt"], text + ("" if ruta["granskad"] else " (ogranskad bedömning)")))
    if t["antal_platser"] > len(t["platser"]):
        textkritik.append(("Fler platser", f"{t['antal_platser'] - len(t['platser'])} till"))

    utdrag = t.get("utdrag")
    return {
        "id": t["id"],
        "rubrik": t["rubrik"],
        "url": url,
        "typ": TYPNAMN.get(t["undertyp"], t["undertyp"] or TYPNAMN.get(t["objekttyp"], "")),
        "kallsamling": t.get("kallsamling"),
        "tid": _arspann(visas.get("fran"), visas.get("till")),
        "tid_kalla": {"handelse": "händelse", "tillkomst": "skriven"}.get(visas.get("kalla")),
        "platser": [{"text": plats_text(p), "url": _lank(param, plats=p["plats_id"], platsroll="primar"),
                     "roll": PLATSROLLER.get(p["roll"], p["roll"]), "osaker": p["osaker"]} for p in primara[:3]],
        "text": (utdrag or {}).get("text") or t.get("sammanfattning"),
        "utdrag_typ": (utdrag or {}).get("passagetyp"),
        # Språkmodellens svenska översättningar har passage-id som slutar på :sv
        "ogranskad": bool(utdrag and utdrag["passage_id"].endswith(":sv")),
        "lang": SPRAKKODER.get((utdrag or {}).get("sprak")) if utdrag else None,
        "objekttyp": t["objekttyp"],
        "bedomningar": [klartext.bedomningsruta(b) for b in t.get("bedomningar", [])],
        "textkritik": textkritik,
    }


def _tidslinje(decennier: list[dict], param: dict) -> list[dict]:
    """Staplar per decennium från det första till det sista, med tomma decennier utfyllda."""
    antal = {d["varde"]: d["antal"] for d in decennier}
    if not antal:
        return []
    storst = max(antal.values())
    staplar = []
    for decennium in range(min(antal), max(antal) + 10, 10):
        n = antal.get(decennium, 0)
        staplar.append({
            "decennium": decennium, "till": decennium + 9, "antal": n,
            # Roten ur jämnar ut skillnaden mellan breven på 1400-talet och allt annat
            "hojd": round(100 * math.sqrt(n / storst)) if n else 0,
            "url": _lank(param, ar_fran=decennium, ar_till=decennium + 9),
            "sekel": decennium % 100 == 0,
        })
    return staplar


def _fasetter(fasetter: dict, param: dict) -> list[dict]:
    grupper = []
    for nyckel, rubrik in FASETTRUBRIKER:
        filtrering = "plats" if nyckel in ("landskap", "land") else nyckel
        # Land- och landskapsfasetterna räknar de platser som visas först,
        # så filtret måste gälla samma platser
        extra = {"platsroll": "primar"} if filtrering == "plats" else {}
        varden = []
        for f in fasetter.get(nyckel, []):
            namn = f.get("namn") or TYPNAMN.get(f["varde"], f["varde"])
            varden.append({"namn": namn, "antal": f["antal"], "vald": param.get(filtrering) == f["varde"],
                           "url": _lank(param, **{filtrering: f["varde"]}, **extra)})
        if varden:
            grupper.append({"rubrik": rubrik, "varden": varden[:12]})
    return grupper


def soksidans_url() -> str | None:
    from .models import SokSida

    sida = SokSida.objects.live().first()
    return sida.url if sida else None


def sok(get) -> dict:
    """Allt som söksidans mall behöver, ur formulärets GET-parametrar."""
    param = {k: get.get(k, "").strip() for k in FALT if get.get(k, "").strip()}
    sida = max(1, int(get.get("sida", "1"))) if get.get("sida", "1").isdigit() else 1
    kontext = {"param": param, "tidsaxlar": TIDSAXLAR, "textkritik": get.get("textkritik") == "1",
               "sokt": bool(param), "traffar": [], "fasetter": [], "tidslinje": [], "kartpunkter": [],
               "aktiva": []}
    if not param:
        return kontext

    try:
        svar = texter._hamta("/v1/sok/objekt", **param, sida=sida, per_sida=PER_SIDA, karta="true")
    except texter.TextFel as fel:
        kontext["fel"] = str(fel) if fel.kod < 500 else "Sökningen svarar inte just nu. Försök igen om en stund."
        return kontext

    namn_pa = {f["varde"]: f.get("namn") for grupp in svar["fasetter"].values() for f in grupp}
    for nyckel in ("objekttyp", "undertyp", "kallsamling", "plats", "platsroll"):
        if nyckel in param:
            varde = param[nyckel]
            if nyckel == "platsroll":
                namn = "plats: " + ({"primar": "där det hände"} | PLATSROLLER).get(varde, varde)
            else:
                namn = namn_pa.get(varde) or TYPNAMN.get(varde) or varde
            kontext["aktiva"].append({"namn": namn,
                                      "url": _lank(param, **{nyckel: None})})
    if "ar_fran" in param or "ar_till" in param:
        kontext["aktiva"].append({"namn": f"{param.get('ar_fran', '…')}–{param.get('ar_till', '…')}",
                                  "url": _lank(param, ar_fran=None, ar_till=None)})

    # Källkritisk hjälp följer med i alla länkar på sidan, men skickas inte till API:et
    if kontext["textkritik"]:
        param["textkritik"] = "1"
    kontext["textkritik_vaxla_url"] = _lank(param, textkritik=None if kontext["textkritik"] else "1")
    sidor = math.ceil(svar["total"] / PER_SIDA)
    adresser = lankar.sidor()
    kontext.update({
        "total": svar["total"],
        "sida": sida,
        "sidor": sidor,
        "foregaende": _lank(param, sida=sida - 1) if sida > 1 else None,
        "nasta": _lank(param, sida=sida + 1) if sida < sidor else None,
        "traffar": [_traff(t, adresser, param) for t in svar["poster"]],
        "fasetter": _fasetter(svar["fasetter"], param),
        "tidslinje": _tidslinje(svar["fasetter"].get("decennium", []), param),
        "kartpunkter": [{**p, "url": _lank(param, plats=p["plats_id"], platsroll="primar")}
                        for p in svar.get("karta", [])],
        "kapad": svar.get("kapad", False),
        "expansion": [e["huvudterm"] for e in svar.get("expansion", [])
                      if e["huvudterm"].casefold() != param.get("q", "").casefold() and not e.get("stavning")],
        "stavning": svar.get("stavning", []),
    })
    return kontext

"""
Kontrollerade värden i klartext: akthet: misstankt blir Äkthet: misstänkt förfalskning.

Etiketterna hämtas från API:ets vokabulär (/v1/vokabularer), som är samma
som databasen använder, så att webbplatsen aldrig visar en kod.
"""

import re

from . import kallor, texter


def _vokabular() -> dict[tuple[str, str], str]:
    try:
        return {(r["schema"], r["kod"]): r["etikett"] for r in texter._hamta("/v1/vokabularer")}
    except texter.TextFel:
        return {}


def etikett(schema: str, kod: str | None) -> str:
    """Kodens etikett i vokabuläret, eller koden med mellanslag om den saknas."""
    if not kod:
        return ""
    return _vokabular().get((schema, kod)) or kod.replace("_", " ")


def bedomning(aspekt: str, varde: str, bedomare: str | None = None) -> str:
    """En bedömning i klartext: Äkthet: misstänkt förfalskning (SDHK)."""
    rubrik = etikett("bedomningsaspekt", aspekt).capitalize()
    if aspekt == "datering":
        text = kallor.datering(varde) or varde
    else:
        text = etikett(aspekt, varde).lower()
    return f"{rubrik}: {text}" + (f" ({bedomare})" if bedomare else "")


def bedomningsruta(b: dict) -> dict:
    """
    En bedömning för träffkortet och verksidan: etiketten i klartext och,
    för den källkritiska hjälpen, vem som gjort den, var och varför.
    """
    kalla = b.get("bedomare") or ""
    if b.get("publikation") and b["publikation"] != kalla:
        kalla += f", {b['publikation']}" if kalla else b["publikation"]
    if b.get("sidor"):
        kalla += f", s. {b['sidor']}"
    etikett_ = bedomning(b["aspekt"], b["varde"])
    if b.get("vittnestyp"):
        # En bedömning av ett vittne: "Medeltida avskrift: förfalskning"
        etikett_ = f"{etikett('vittnestyp', b['vittnestyp']).capitalize()}: {etikett_.split(': ', 1)[-1]}"
    return {
        "etikett": etikett_,
        "vittne": b.get("vittne"),
        "aspekt": etikett("bedomningsaspekt", b["aspekt"]).capitalize(),
        "kalla": kalla,
        "motivering": b.get("motivering"),
        "sakerhet": etikett("sakerhet", b.get("sakerhet")).lower() if b.get("sakerhet") else None,
        "granskad": b.get("granskad", False),
    }


# Hänvisningen till Diplomatarium Danicum i ett SDHK-brevs tryckuppgift, t.ex. "DD III:9, nr 87"
_DD_REF = re.compile(r"\bDD\s*(?:[IVX]+|\d+)?\s*:\s*\d+\s*,?\s*nr\s*\d+\b")


def tryck(uppgifter: dict) -> list[dict]:
    """
    Verkets tryck och tryckta regester (SDHK:s fält Tryck och Tryckt regest)
    som rader för sidan. Hänvisningen till Diplomatarium Danicum blir länk till
    brevet i DSL:s utgåva när verket har en sådan länk (lankar.py), så att
    läsaren kan gå vidare till utgåvan.
    """
    dd = [l["uri"] for l in uppgifter.get("externa_lankar", []) if l["kalla"] == "diplomatarium_danicum"]

    def delar(ref: str) -> dict:
        m = _DD_REF.search(ref) if len(dd) == 1 else None
        return ({"fore": ref[:m.start()], "dd": m.group(0), "efter": ref[m.end():], "url": dd[0]}
                if m else {"fore": ref})

    grupper = [
        ("Tryck", [u["referens"] for u in uppgifter.get("utgavor", []) if ":tryck:" in u["id"] and u.get("referens")]),
        ("Tryckt regest", [v["beskrivning"] for v in uppgifter.get("vittnen", [])
                           if v["typ"] == "tryckt_regest" and v.get("beskrivning")]),
    ]
    return [{"etikett": etikett, "rader": [delar(r) for r in refs]} for etikett, refs in grupper if refs]

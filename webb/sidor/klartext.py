"""
Kontrollerade värden i klartext: akthet: misstankt blir Äkthet: misstänkt förfalskning.

Etiketterna hämtas från API:ets vokabulär (/v1/vokabularer), som är samma
som databasen använder, så att webbplatsen aldrig visar en kod.
"""

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

"""Mallfilter för källtexterna: språknamn, versionstyper och dateringar."""

import json

from django import template
from django.utils.safestring import mark_safe

from sidor import kallor, texter

register = template.Library()


@register.filter
def sprakord(kod) -> str:
    """ISO 639-3-kod eller lista av koder som svenska språknamn."""
    if isinstance(kod, (list, tuple)):
        return ", ".join(kallor.SPRAK.get(k, k) for k in kod)
    return kallor.SPRAK.get(kod or "", kod or "okänt språk")


@register.filter
def versionsnamn(version: dict) -> str:
    """'svenska, översättning av Emil Olson 1919' och liknande."""
    typ = kallor.TYPER.get(version.get("typ"), version.get("typ") or "")
    if version.get("typ") == "oversattning" and version.get("oversattare"):
        typ += f" av {version['oversattare']}" + (f" {version['ar']}" if version.get("ar") else "")
    elif version.get("typ") == "original" and version.get("ar"):
        typ += f", {version['ar']}"
    if version.get("roll") == "skolier":
        typ += ", skolier"
    sprak = version.get("sprak") or version.get("passagesprak")
    return f"{sprakord(sprak).capitalize()}, {typ}"


@register.filter
def datering(edtf) -> str:
    return kallor.datering(edtf) or ""


@register.filter
def get_item(ordbok: dict, nyckel: str):
    """Ett värde ur en dict med en nyckel som inte går att skriva med punkt, t.ex. 'fsv'."""
    return ordbok.get(nyckel) if isinstance(ordbok, dict) else None


@register.filter
def verkadress(verk_id: str) -> str:
    """Verkets id som del av en webbadress (se texter.adress)."""
    return texter.adress(verk_id)


@register.filter
def jsonld(data: dict) -> str:
    """
    JSON-LD att lägga i <script type="application/ld+json">. Tecknen < > &
    skrivs som \\u-koder, så att en text som innehåller </script> inte kan
    avsluta elementet.
    """
    text = json.dumps(data, ensure_ascii=False)
    return mark_safe(text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))

"""
Webbadresser till verk och entiteter.

Varje sökträff, påstående och namn på webbplatsen leder till en sida: ett
verk till sin sida under källförteckningen, en person, plats, institution
eller ett begrepp till sin sida under registret.
"""

import urllib.parse

from . import texter


def sidor() -> dict[str, str | None]:
    """Adresserna till källförteckningen och registret, eller None om sidan saknas."""
    from .models import KallforteckningSida, RegisterSida

    forteckning = KallforteckningSida.objects.live().first()
    register = RegisterSida.objects.live().first()
    return {"kallor": forteckning.url if forteckning else None,
            "register": register.url if register else None}


def verk_url(verk_id: str, adresser: dict) -> str | None:
    if not adresser.get("kallor"):
        return None
    return f"{adresser['kallor']}verk/{texter.adress(verk_id)}/"


def entitetsadress(entitet_id: str) -> str:
    """
    Entitetens id som del av en webbadress: person:sdhk:ansgar:146 blir
    person--sdhk--ansgar--146. Wagtail släpper bara igenom bokstäver,
    siffror, understreck och bindestreck i adressens delar. Några id har
    bindestreck (person:sdhk:l:682-2), men inget har två i rad eller ett
    bindestreck intill ett kolon, så kolon kan skrivas som två bindestreck.
    """
    return entitet_id.replace(":", "--")


def entitet_id(adress: str) -> str:
    """Motsatsen till entitetsadress()."""
    return adress.replace("--", ":")


def entitet_url(entitet_id_: str, adresser: dict) -> str | None:
    if not adresser.get("register"):
        return None
    return f"{adresser['register']}{urllib.parse.quote(entitetsadress(entitet_id_))}/"


def objekt_url(objekt_id: str, objekttyp: str, adresser: dict) -> str | None:
    return verk_url(objekt_id, adresser) if objekttyp == "verk" else entitet_url(objekt_id, adresser)

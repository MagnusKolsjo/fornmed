"""
Svaren från API:et som JSON, Markdown, text och CSV.

Alla format är vyer av samma svar. JSON är den fullständiga formen; övriga
format återger det som behövs för att läsa och citera:

- Ett dokument eller en passage inleds med en källhänvisning (verk, utgåva,
  språk, licens och, för maskinöversättningar, att texten är ogranskad) och
  följs av texten med passageadresserna som rubriker.
- En lista blir en tabell i Markdown och en rad per post i CSV.
- Övriga svar blir rubriker och fält i Markdown och fält per rad i text.

Vilka format en resurs har bestäms av dess slag (`SLAG`). CSV finns bara
för listor, eftersom en enskild post med nästlade fält inte blir en tabell.
"""

import csv
import io
import json

FORMAT = {
    "json": "application/json",
    "md": "text/markdown; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
}

# Formaten per slag av svar
SLAG = {
    "dokument": ("json", "md", "txt"),
    "parallell": ("json", "md", "txt"),
    "passage": ("json", "md", "txt"),
    "lista": ("json", "md", "txt", "csv"),
    "objekt": ("json", "md", "txt"),
}


def valj_format(begart: str | None, accept: str | None, tillatna: tuple[str, ...]) -> str | None:
    """Formatet för svaret, eller None när inget tillåtet format passar.

    `format=` i adressen gäller före Accept-huvudet. Utan någon av dem blir
    det JSON.
    """
    if begart:
        return begart if begart in tillatna else None
    if not accept:
        return "json"
    for del_ in accept.split(","):
        typ = del_.split(";")[0].strip().lower()
        # Webbläsare skickar text/html före */*; då blir det JSON
        if typ in ("", "*/*", "application/*"):
            return "json"
        if typ == "text/*":
            return next((k for k in ("md", "txt") if k in tillatna), None)
        for kod in tillatna:
            if FORMAT[kod].split(";")[0] == typ:
                return kod
    return None


# -----------------------------------------------------------------------------
# Källhänvisning
# -----------------------------------------------------------------------------

def _sprak(varde) -> str:
    return ", ".join(varde) if isinstance(varde, list) else (varde or "")


def _hanvisning(verk: dict, version: dict) -> list[tuple[str, str]]:
    """Fälten i källhänvisningen, i läsordning."""
    falt = [
        ("Verk", f"{verk['titel']} ({verk['id']})"),
        ("Upphov", verk.get("upphov") or ""),
        ("Datering", verk.get("datering_edtf") or ""),
        ("Källsamling", verk.get("kallsamling") or ""),
    ]
    return [(namn, varde) for namn, varde in falt if varde] + _versionsfalt(version)


def _versionsfalt(version: dict) -> list[tuple[str, str]]:
    """Källhänvisningens fält för språkversionen."""
    falt = [
        ("Utgåva", version.get("referens") or version.get("utgava") or ""),
        ("Språk", _sprak(version.get("sprak"))),
        ("Typ", version.get("typ") or ""),
        ("Översättare", version.get("oversattare") or ""),
        ("Licens", version.get("licens") or ""),
    ]
    return [(namn, varde) for namn, varde in falt if varde]


def _anmarkning(version: dict) -> str | None:
    return version.get("anmarkning")


# -----------------------------------------------------------------------------
# Dokument, parallell text och passage
# -----------------------------------------------------------------------------

def _dokument_md(d: dict) -> str:
    rader = [f"# {d['verk']['titel']}" + (f" – {d['del']}" if d.get("del") else ""), ""]
    if anm := _anmarkning(d["version"]):
        rader += [f"> **Ogranskad:** {anm}", ""]
    rader += [f"- **{namn}:** {varde}" for namn, varde in _hanvisning(d["verk"], d["version"])]
    rader.append("")
    for pa in d["passager"]:
        rader += [f"## {pa['adress'] or pa['id']}", "", f"<!-- passage: {pa['id']} -->", "",
                  pa["text"].strip(), ""]
    return "\n".join(rader)


def _dokument_txt(d: dict) -> str:
    rubrik = d["verk"]["titel"] + (f" – {d['del']}" if d.get("del") else "")
    rader = [rubrik, "=" * len(rubrik)]
    if anm := _anmarkning(d["version"]):
        rader.append(f"OGRANSKAD: {anm}")
    rader += [f"{namn}: {varde}" for namn, varde in _hanvisning(d["verk"], d["version"])]
    rader.append("")
    for pa in d["passager"]:
        rader += [f"[{pa['adress'] or pa['id']}]", pa["text"].strip(), ""]
    return "\n".join(rader)


def _parallell_md(d: dict) -> str:
    rader = [f"# {d['verk']['titel']}" + (f" – {d['del']}" if d.get("del") else ""), ""]
    for kod, version in d["versioner"].items():
        hanvisning = "; ".join(f"{n}: {v}" for n, v in _versionsfalt(version))
        rader.append(f"- **{kod}:** {hanvisning}")
        if anm := _anmarkning(version):
            rader.append(f"  - *Ogranskad:* {anm}")
    rader.append("")
    for rad in d["passager"]:
        rader += [f"## {rad['adress']}", ""]
        for kod in d["sprak"]:
            text = (rad.get(kod) or {}).get("text", "—")
            rader += [f"**{kod}**", "", text.strip(), ""]
    return "\n".join(rader)


def _parallell_txt(d: dict) -> str:
    rader = [d["verk"]["titel"] + (f" – {d['del']}" if d.get("del") else ""), ""]
    for kod, version in d["versioner"].items():
        rader.append(f"{kod}: " + "; ".join(f"{n}: {v}" for n, v in _versionsfalt(version)))
        if anm := _anmarkning(version):
            rader.append(f"  OGRANSKAD: {anm}")
    rader.append("")
    for rad in d["passager"]:
        rader.append(f"[{rad['adress']}]")
        for kod in d["sprak"]:
            rader += [f"{kod}:", ((rad.get(kod) or {}).get("text") or "—").strip()]
        rader.append("")
    return "\n".join(rader)


def _passage_som_dokument(d: dict) -> dict:
    """En passage i samma form som ett dokument, så att samma återgivning används."""
    return {"verk": d["verk"], "version": d["version"], "del": None, "passager": [d["passage"]]}


# -----------------------------------------------------------------------------
# Listor och övriga svar
# -----------------------------------------------------------------------------

def _cell(varde) -> str:
    if varde is None:
        return ""
    if isinstance(varde, bool):
        return "ja" if varde else "nej"
    if isinstance(varde, (list, tuple)):
        return ", ".join(_cell(v) for v in varde)
    if isinstance(varde, dict):
        return json.dumps(varde, ensure_ascii=False)
    return str(varde)


def _kolumner(rader: list[dict]) -> list[str]:
    """Kolumnerna i den ordning de först förekommer; nästlade listor utesluts."""
    kolumner: list[str] = []
    for rad in rader:
        for nyckel, varde in rad.items():
            if nyckel not in kolumner and not (isinstance(varde, list) and varde
                                               and isinstance(varde[0], dict)):
                kolumner.append(nyckel)
    return kolumner


def _md_tabell(rader: list[dict]) -> list[str]:
    if not rader:
        return ["*Inga poster.*"]
    kolumner = _kolumner(rader)
    ut = ["| " + " | ".join(kolumner) + " |", "|" + "---|" * len(kolumner)]
    for rad in rader:
        ut.append("| " + " | ".join(_cell(rad.get(k)).replace("|", "\\|").replace("\n", " ")
                                    for k in kolumner) + " |")
    return ut


def _lista_csv(rader: list[dict]) -> str:
    fil = io.StringIO()
    kolumner = _kolumner(rader)
    skrivare = csv.writer(fil, lineterminator="\n")
    skrivare.writerow(kolumner)
    for rad in rader:
        skrivare.writerow([_cell(rad.get(k)) for k in kolumner])
    return fil.getvalue()


def _lista_txt(rader: list[dict]) -> str:
    ut = []
    for rad in rader:
        ut += [f"{k}: {_cell(v)}" for k, v in rad.items() if not isinstance(v, (list, dict)) or v]
        ut.append("")
    return "\n".join(ut)


def _objekt_md(d: dict, niva: int = 1, titel: str | None = None) -> list[str]:
    ut: list[str] = []
    rubrik = titel or d.get("titel") or d.get("namn") or d.get("id")
    if rubrik:
        ut += [f"{'#' * niva} {rubrik}", ""]
    for nyckel, varde in d.items():
        if isinstance(varde, dict):
            continue
        if isinstance(varde, list) and varde and isinstance(varde[0], dict):
            continue
        if varde not in (None, "", []):
            ut.append(f"- **{nyckel}:** {_cell(varde)}")
    ut.append("")
    for nyckel, varde in d.items():
        if isinstance(varde, dict) and varde:
            ut += _objekt_md(varde, niva + 1, nyckel)
        elif isinstance(varde, list) and varde and isinstance(varde[0], dict):
            ut += [f"{'#' * (niva + 1)} {nyckel}", ""] + _md_tabell(varde) + [""]
    return ut


def _objekt_txt(d: dict, indrag: str = "") -> list[str]:
    ut: list[str] = []
    for nyckel, varde in d.items():
        if isinstance(varde, dict):
            ut.append(f"{indrag}{nyckel}:")
            ut += _objekt_txt(varde, indrag + "  ")
        elif isinstance(varde, list) and varde and isinstance(varde[0], dict):
            ut.append(f"{indrag}{nyckel}:")
            for post in varde:
                ut += _objekt_txt(post, indrag + "  ")
                ut.append("")
        elif varde not in (None, "", []):
            ut.append(f"{indrag}{nyckel}: {_cell(varde)}")
    return ut


def aterge(data, slag: str, fmt: str, titel: str | None = None) -> str:
    """Svaret som text i formatet `fmt`. JSON hanteras av API:et självt."""
    if slag == "dokument":
        return _dokument_md(data) if fmt == "md" else _dokument_txt(data)
    if slag == "parallell":
        return _parallell_md(data) if fmt == "md" else _parallell_txt(data)
    if slag == "passage":
        d = _passage_som_dokument(data)
        return _dokument_md(d) if fmt == "md" else _dokument_txt(d)
    if slag == "lista":
        rader = data
        if fmt == "csv":
            return _lista_csv(rader)
        if fmt == "md":
            return "\n".join(([f"# {titel}", ""] if titel else []) + _md_tabell(rader)) + "\n"
        return _lista_txt(rader)
    if fmt == "md":
        return "\n".join(_objekt_md(data, titel=titel))
    return "\n".join(_objekt_txt(data)) + "\n"

"""
Tolk för runinskrifter ur Rundata.info, Stockholms universitets uppdaterade
version av Samnordisk runtextdatabas.

Rundata.info lämnar hela databasen som en SQLite-fil. Varje inskrift blir
ett verk med fyndort, datering, ristare, stil och material, och upp till
fem passager: translitterering, normalisering till fornvästnordiska och
till runsvenska (eller motsvarande östnordiska), och översättning till
svenska och engelska. Bara den svenska översättningen finns på modern
svenska och embeddas; omkring hälften av inskrifterna har en.

Licens: Open Database License 1.0, innehållet Database Contents License
1.0. Uppsala runforum kräver dessutom att databasen anges med namn och
länk varje gång uppgifter ur den visas, att en ändrad version inte kallas
Samnordisk runtextdatabas, och att Uppsala runforum meddelas när databasen
används i en annan tillämpning. Hänvisningen står därför i varje
inskrifts utgåva.

Användning:
    python -m tolkar.runor
    python -m tolkar.runor --torr
"""

import argparse
import logging
import re
import sqlite3
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, Vittne, ladda

log = logging.getLogger("tolkar.runor")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "runor"
STARTSIDA = "https://www.rundata.info/"
# Villkoren föreskriver just den här adressen vid citering och länkning, fast
# den numera vidarebefordras till uu.se
SAMNORDISK = "http://www.nordiska.uu.se/forskn/samnord.htm"
HANVISNING = ("Rundata.info (Stockholms universitet), som bygger på Samnordisk runtextdatabas, "
              "Uppsala universitet: " + SAMNORDISK)

# Signumets prefix anger land eller landskap; de vanligaste får klartext i beskrivningen
OMRADEN = {"U": "Uppland", "Sö": "Södermanland", "Ög": "Östergötland", "Vg": "Västergötland",
           "Sm": "Småland", "Öl": "Öland", "G": "Gotland", "Vs": "Västmanland", "Nä": "Närke",
           "Gs": "Gästrikland", "Hs": "Hälsingland", "M": "Medelpad", "J": "Jämtland", "Vr": "Värmland",
           "D": "Dalarna", "Bo": "Bohuslän", "Hr": "Härjedalen", "Ån": "Ångermanland", "Lp": "Lappland",
           "Dr": "Danmark", "DR": "Danmark", "N": "Norge", "IS": "Island", "GR": "Grönland",
           "Or": "Orkney", "Sh": "Shetland", "IM": "Isle of Man", "E": "England", "IR": "Irland",
           "Sc": "Skottland", "FR": "Frankrike", "DE": "Tyskland", "RU": "Ryssland", "FI": "Finland"}


def hamta() -> Path:
    """Databasfilen; adressen tas ur startsidan, eftersom filnamnet byts vid varje uppdatering."""
    fil = KATALOG / "runes.sqlite3"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(STARTSIDA, headers={"User-Agent": "fornmed-forskningsdatabas/0.1"})
        sida = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        sokvag = re.search(r'"(/static/runes/runes\.[^"]+\.sqlite3[^"]*)"', sida).group(1)
        log.info("Hämtar %s", sokvag)
        urllib.request.urlretrieve(STARTSIDA.rstrip("/") + sokvag, fil)
    return fil


def _slug(signum: str) -> str:
    t = signum.lower()
    for a, b in (("å", "a"), ("ä", "a"), ("ö", "o"), ("æ", "ae"), ("ø", "o"), ("þ", "th"), ("ð", "d")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _permalank(referenser: str | None) -> str | None:
    m = re.search(r"Permanent link for citation:::(\S+)", referenser or "")
    return m.group(1) if m else None


def _beskrivning(r: sqlite3.Row) -> str:
    plats = ", ".join(x for x in (r["found_location"], r["parish"], r["district"]) if x)
    delar = [f"Runinskrift {r['signature_text']}" + (f", {plats}" if plats else "") + "."]
    if r["dating"]:
        delar.append(f"Datering enligt Rundata: {r['dating']}.")
    fakta = [x for x in (r["material"] and f"material {r['material']}", r["rune_type"] and f"runtyp {r['rune_type']}",
                         r["style"] and f"stil {r['style']}", r["carver"] and f"ristare {r['carver']}") if x]
    if fakta:
        delar.append(", ".join(fakta).capitalize() + ".")
    if r["lost"]:
        delar.append("Inskriften är förkommen; texten bygger på äldre avbildningar eller läsningar.")
    if r["current_location"]:
        delar.append(f"Nuvarande plats: {r['current_location']}")
    return " ".join(delar)


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="rundata", namn="Runinskrifter ur Rundata.info (bygger på Samnordisk runtextdatabas)",
            utgivare="Stockholms universitet; Uppsala runforum, Uppsala universitet",
            url=STARTSIDA, licens="ODbL 1.0, innehåll DbCL 1.0, med Uppsala runforums tilläggsvillkor",
            version="rundata.info 2026-10"),
        verk=[])
    con = sqlite3.connect(hamta())
    con.row_factory = sqlite3.Row
    # Länkar till fotografier och dokumentation hos museer och Riksantikvarieämbetet,
    # för kontroll av läsningen; bilderna har respektive förvaltares villkor
    bilder: dict[int, list[str]] = {}
    for sig, lank in con.execute(
            "SELECT m.signature_id, i.link_url FROM runes_imagelink i "
            "JOIN meta_information m ON m.id = i.meta_id ORDER BY i.id"):
        if lank and lank not in bilder.setdefault(sig, []):
            bilder[sig].append(lank)
    for r in con.execute("SELECT * FROM all_data ORDER BY id"):
        signum = r["signature_text"].strip()
        slug = _slug(signum)
        verk_id, utg = f"verk:runa:{slug}", f"utgava:runa:{slug}"
        fran = r["year_from"] or None
        till = r["year_to"] or None
        prefix = signum.split(" ")[0]
        extra = {k: r[k] for k in ("found_location", "parish", "district", "municipality", "current_location",
                                   "latitude", "longitude", "rune_type", "dating", "style", "carver",
                                   "material", "material_type", "lost") if r[k] not in (None, "")}
        if prefix in OMRADEN:
            extra["omrade"] = OMRADEN[prefix]
        if bilder.get(r["signature_id"]):
            extra["bilder"] = bilder[r["signature_id"]][:25]
        paket.verk.append(Verk(
            id=verk_id, titel=f"{signum} {r['found_location'] or ''}".strip(), genre="runinskrift",
            sprak=["non"], datering_edtf=f"{fran:04d}/{till:04d}" if fran and till else None,
            datering_fran=fran * 10000 + 101 if fran else None,
            datering_till=till * 10000 + 1231 if till else None,
            beskrivning=_beskrivning(r), extern_url=_permalank(r["references_combined"]), extra=extra))
        paket.utgavor.append((verk_id, Utgava(
            utg, f"{signum} i {HANVISNING}. Referenser: {r['references_combined'] or '–'}",
            "ODbL 1.0 / DbCL 1.0")))
        paket.vittnen.append((verk_id, Vittne(
            f"vittne:runa:{slug}", "original",
            f"{r['material'] or 'Föremål'}{', förkommet' if r['lost'] else ''}"
            + (f"; {r['current_location']}" if r["current_location"] else ""),
            signum=signum, datering_edtf=f"{fran:04d}/{till:04d}" if fran and till else None,
            datering_fran=fran * 10000 + 101 if fran else None,
            datering_till=till * 10000 + 1231 if till else None)))
        for nr, (kolumn, suffix, typ, sprak, namn) in enumerate((
                ("transliteration", "translitt", "originaltext", "non", "translitterering"),
                ("normalisation_norse", "norm_fvn", "normaliserad", "non", "normalisering till fornvästnordiska"),
                ("normalisation_scandinavian", "norm_run", "normaliserad", "fsv",
                 "normalisering till runsvenska/östnordiska"),
                ("swedish_translation", "sv", "oversattning", "swe", "svensk översättning"),
                ("english_translation", "en", "oversattning", "eng", "engelsk översättning")), start=1):
            text = (r[kolumn] or "").strip()
            if not text:
                continue
            paket.passager.append((verk_id, Passage(
                id=f"runa:{slug}:{suffix}",
                typ=typ, adress=f"{signum}, {namn}", sprak=sprak, text=text, ordning=nr, utgava_id=utg,
                url=_permalank(r["references_combined"]))))
    con.close()
    log.info("%d inskrifter, %d passager", len(paket.verk), len(paket.passager))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    if arg.torr:
        for _, p in paket.passager[:10]:
            log.info("%s | %s | %s", p.id, p.adress, p.text[:80])
        return
    db.initiera_schema()
    ladda(paket)


if __name__ == "__main__":
    main()

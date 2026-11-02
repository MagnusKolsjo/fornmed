"""
Tolk för enstaka källor ur svenska Wikisource: Gutasagan, Västgötalagens
lagmans-, konungs- och biskopslängd och Hednalagen.

Sidorna hämtas renderade via MediaWiki-API:t, eftersom texten på
Wikisource ofta ligger på inskannade sidor som sidan bara hänvisar till.
Sidnummer i utgåvan ("[ 32 ]"), notmarkeringar ("[3]") och noterna under
texten tas bort.

- Gutasagan efter Carl Säve, Gutniska urkunder (1859), per kapitel.
- Längderna efter Collin & Schlyter, Samling af Sweriges gamla lagar I
  (1827), "Åtskilliga antekningar af okänd författare", kap. 14–16: en
  passage per lagman, kung och biskop. Längderna står i samma handskrift
  som Äldre Västgötalagen (Holm B 59) och tillskrivs prästen i Vidhem.
- Hednalagen efter Olavus Petris egenhändiga avskrift i Ängsökodexen av
  Upplandslagen, utgiven av Otto von Friesen (Samlaren 23, 1902). Lagen
  finns inte i någon medeltida handskrift; Olavus Petris kommentar läggs
  som egen passage.

Användning:
    python -m tolkar.wikisource
    python -m tolkar.wikisource --torr
"""

import argparse
import html
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, Vittne, ladda

log = logging.getLogger("tolkar.wikisource")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "wikisource"
API = "https://sv.wikisource.org/w/api.php"
USER_AGENT = "fornmed-forskningsdatabas/0.1 (öppen forskningsdatabas över medeltida källor)"
WIKI = "https://sv.wikisource.org/wiki/"

SIDA_GUTASAGAN = "Gutniska urkunder/Guta Saga"
SIDA_LANGDER = "Sveriges Gamla Lagar/Band I/Åtskilliga antekningar af okänd författare"
SIDA_GUTALAGEN = "Gutniska urkunder/Guta Lag"
# Gutalagen finns redan som verk ur Fornsvenska textbanken; Säves utgåva läggs till som ny utgåva
VERK_GUTALAGEN = "verk:lag:gutalagen_enligt_holm_b_64"
OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "gutniska_sv.json"
MASKIN = ("Svensk översättning gjord av språkmodell (Claude) från forngutniskan. Ogranskad; citera "
          "originalet eller en tryckt översättning.")
SIDA_HEDNALAGEN = "Olavus Petris egenhändiga afskrift af den s. k. Hednalagen i Ängsöcodex af Upplandslagen"

# Längdernas ordningstal i handskriftens stavning ("Fyarðhi", "Sexstanði", "Attærtandi");
# de mer specifika mönstren prövas först
ORDNINGSTAL = [(r"[þt]r[æe]n?ttan", 13), (r"f[iy]u?r?tan|fyghurtan", 14), (r"f[æe]mtan", 15),
               (r"sexs?tan", 16), (r"s[iy]utan", 17), (r"at+[æe]r?tan", 18), (r"nitan", 19),
               (r"fyrst", 1), (r"annar", 2), (r"[þt]ri[þðdh]+i", 3), (r"f[iy]ar[þðdh]+i", 4),
               (r"f[æe]mt", 5), (r"s[æe]tt", 6), (r"s[iy]u?n[dð]|synd", 7), (r"at+u?n[dð]", 8),
               (r"niun[dð]", 9), (r"t[iy]i?un[dð]", 10), (r"[æe]l+i[uo]p+t|[æe]l+iuft", 11),
               (r"tol?ft", 12)]


def ordningstal(text: str) -> int | None:
    """Det första ordningstalet i postens början ("Fæmtandi war knutar konongær")."""
    for ord_ in re.findall(r"\w+", text[:400].lower()):
        if nr := next((n for monster, n in ORDNINGSTAL if re.fullmatch(f"(?:{monster})\\w*", ord_)), None):
            return nr
    return None


def _sida(sida: str) -> str:
    """Sidans adress på svenska Wikisource, där sidbilderna går att visa bredvid texten."""
    return WIKI + urllib.parse.quote(sida.replace(" ", "_"))


def _slug(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text.lower()).strip("_")[:80]


def hamta(sida: str) -> str:
    """Sidans renderade text, cachad i data/raw/wikisource/."""
    fil = KATALOG / f"{_slug(sida)}.json"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        url = API + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": sida, "prop": "text", "format": "json", "formatversion": 2})
        log.info("Hämtar %s", sida)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
                                    timeout=60) as svar:
            fil.write_bytes(svar.read())
        time.sleep(3)
    data = json.loads(fil.read_text(encoding="utf-8"))
    if "parse" not in data:
        raise RuntimeError(f"Sidan '{sida}' finns inte på Wikisource")
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", data["parse"]["text"], flags=re.S)
    h = re.sub(r"<br\s*/?>|</p>|</div>|</h\d>|</li>|</tr>", "\n", h)
    return html.unescape(re.sub(r"<[^>]+>", "", h))


def rensa(text: str) -> str:
    """Löptext utan sidnummer, notmarkeringar och avstavningar."""
    # "([5]" markerar var ett ställe som en not gäller börjar; parentesen är utgivarens
    text = re.sub(r"\(\[\d{1,3}\]", "", text)
    text = re.sub(r"\[\s*\d{1,3}\s*\]", " ", text)
    text = re.sub(r"\[\d{1,3}\]", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?m)^\s*\d{2}(?=¶)|(?<=\w)\d{2}$", "", text)   # handskriftens bladnummer i marginalen
    return re.sub(r"\s+", " ", text).strip()


def _utan_noter(text: str) -> str:
    """Noterna står sist på sidan och inleds med ↑."""
    return text.split("\n↑", 1)[0]


def gutalagen() -> list[tuple[int, str]]:
    """Säves Guta Lag per kapitel (1–65); innehållsförteckningen före kap. 1 tas bort."""
    text = _utan_noter(hamta(SIDA_GUTALAGEN))
    # Kapitelrubriken står ibland direkt efter ett sidnummer: "[ 2 ]1 Kap. Hier byrias …"
    delar = re.split(r"(?m)(?:^|(?<=\]))\s*(\d+) Kap\.", text)
    return [(int(nr), rensa(stycke)) for nr, stycke in zip(delar[1::2], delar[2::2])]


def gutasagan() -> list[tuple[int, str]]:
    text = _utan_noter(hamta(SIDA_GUTASAGAN))
    delar = re.split(r"(?m)^(\d+) Kap\.\s*$", text)
    return [(int(nr), rensa(stycke)) for nr, stycke in zip(delar[1::2], delar[2::2])]


def langder() -> dict[int, list[tuple[int | None, str]]]:
    """
    Kapitel 14–16 i Collin & Schlyters utgåva som (ordningstal, text) per
    lagman, kung och biskop. Posterna inleds med ¶, men inte alltid
    ("Sexstanði war swarkir konongær" står utan), så en rad som börjar med
    ett ordningstal och "war" inleder också en post. Ordningstalet tas ur
    texten: konungalängden hoppar över den fjortonde kungen, som bara nämns
    i den trettondes post.
    """
    text = _utan_noter(hamta(SIDA_LANGDER))
    kapitel = {}
    for nr in (14, 15, 16):
        m = re.search(rf"(?m)^\s*(?:\[\s*\d+\s*\])?\s*{nr}\.\[\d+\]\s*$", text)
        slut = re.search(rf"(?m)^\s*(?:\[\s*\d+\s*\])?\s*{nr + 1}\.\[\d+\]\s*$|Sida:Sweriges gamla lagar", text[m.end():])
        stycke = text[m.end():m.end() + slut.start()] if slut else text[m.end():]
        # Handskriftens bladnummer 47–53 står i marginalen och har hamnat i texten
        stycke = re.sub(r"(?m)^\s*(?:4[7-9]|5[0-3])(?=\D)|(?<=\D)(?:4[7-9]|5[0-3])\s*$"
                        r"|(?<=\s)(?:4[7-9]|5[0-3])(?=[a-zæöþð])", "", stycke)
        poster = [rensa(p) for p in re.split(r"¶\.?|\n(?=[A-ZÆÖÞ]\w*(?:an[dð]i)\.? war\b)", stycke)]
        kapitel[nr] = [(ordningstal(p), p) for p in poster if len(p) > 3]
    return kapitel


def hednalagen() -> tuple[str, str]:
    """(lagtexten, Olavus Petris kommentar) ur von Friesens utgåva."""
    text = _utan_noter(hamta(SIDA_HEDNALAGEN))
    borjan = text.index("antiquiſſimis Suecorum legisterijs")
    slut = text.index("Aff thenna laghen")
    rader = text[borjan:slut].split("\n")[1:]
    # Radnummer i utgåvans marginal ("5 hauer giuith/") tas bort
    lag = rensa("\n".join(re.sub(r"^\s*\d{1,2}\s+", "", r) for r in rader))
    kommentar_slut = text.index("Vår text öfverensstämmer")
    kommentar = rensa(text[slut:kommentar_slut])
    return lag, kommentar


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="wikisource", namn="Svenska Wikisource: Gutasagan, Västgötalagens längder, Hednalagen",
            utgivare="Wikisource", url="https://sv.wikisource.org/wiki/Kategori:Landskapslagar",
            licens="Utgåvorna är fria från upphovsrätt; transkriptionerna CC BY-SA 4.0", version="2026-10"),
        verk=[], befintliga_verk=[VERK_GUTALAGEN])
    oversattning = json.loads(OVERSATTNINGAR.read_text(encoding="utf-8")) if OVERSATTNINGAR.exists() else {}

    # Gutasagan
    utg = "utgava:gutasagan:save1859"
    paket.verk.append(Verk(
        id="verk:gutasagan", titel="Gutasagan", genre="kronika", sprak=["fsv"],
        datering_edtf="1200/1350", datering_fran=12000101, datering_till=13501231,
        # Forngutniska; samma språkkod som Gutalagen i Fornsvenska textbanken
        beskrivning="Forngutnisk berättelse om Gotlands bebyggelse, kristnande och förhållande till sveakungen, "
                    "bevarad i samma handskrift som Gutalagen (Holm B 64, omkring 1350). Tillkomsttiden "
                    "är omstridd; intervallet täcker de vanliga förslagen.",
        extern_url=WIKI + urllib.parse.quote(SIDA_GUTASAGAN.replace(" ", "_"))))
    paket.utgavor.append(("verk:gutasagan", Utgava(
        utg, "Carl Säve, Gutniska urkunder: Guta lag, Guta saga och Gotlands runinskrifter, "
             "Stockholm 1859: Guta saga. Transkription på svenska Wikisource.",
        "Public domain; transkription CC BY-SA 4.0")))
    paket.vittnen.append(("verk:gutasagan", Vittne(
        "vittne:gutasagan:holm_b64", "handskrift", "Stockholm, KB, Holm B 64 (Gutalagens handskrift A)",
        signum="Holm B 64", datering_edtf="1325/1375", datering_fran=13250101, datering_till=13751231)))
    for nr, text in gutasagan():
        paket.passager.append(("verk:gutasagan", Passage(
            id=f"gutasagan:{nr}", typ="originaltext", adress=f"kap. {nr} (Säve 1859)", sprak="fsv",
            text=text, ordning=nr, utgava_id=utg, url=_sida(SIDA_GUTASAGAN))))

    # Gutalagen i Säves utgåva, med den vedertagna kapitelindelningen, som ny utgåva av textbankens verk
    utg_gl = "utgava:gutalagen:save1859"
    paket.utgavor.append((VERK_GUTALAGEN, Utgava(
        utg_gl, "Carl Säve, Gutniska urkunder: Guta lag, Guta saga och Gotlands runinskrifter, "
                "Stockholm 1859: Guta lag. Transkription på svenska Wikisource.",
        "Public domain; transkription CC BY-SA 4.0")))
    for nr, text in gutalagen():
        paket.passager.append((VERK_GUTALAGEN, Passage(
            id=f"gutalagen_save:{nr}", typ="originaltext", adress=f"GL kap. {nr} (Säve 1859)", sprak="fsv",
            text=text, ordning=20000 + nr, utgava_id=utg_gl, url=_sida(SIDA_GUTALAGEN))))

    # Svenska översättningar av språkmodell, i egna utgåvor
    for verk_id, prefix, adress in (("verk:gutasagan", "gutasagan", "kap. {nr}"),
                                    (VERK_GUTALAGEN, "gutalagen_save", "GL kap. {nr}")):
        utg_sv = f"utgava:{prefix}:sv_modell"
        poster = sorted(((int(k.split(":")[1]), v) for k, v in oversattning.items() if k.startswith(prefix + ":")))
        if not poster:
            continue
        paket.utgavor.append((verk_id, Utgava(utg_sv, MASKIN, "CC BY-SA 4.0")))
        for nr, text in poster:
            paket.passager.append((verk_id, Passage(
                id=f"{prefix}:{nr}:sv", typ="oversattning",
                adress=adress.format(nr=nr) + " (maskinöversättning)", sprak="swe", text=text,
                ordning=30000 + nr, utgava_id=utg_sv,
                url=_sida(SIDA_GUTASAGAN if prefix == "gutasagan" else SIDA_GUTALAGEN))))

    # Längderna
    utg = "utgava:vastgotalagens_langder:collin_schlyter1827"
    referens = ("H. S. Collin & C. J. Schlyter (utg.), Samling af Sweriges gamla lagar I: Westgöta-Lagen, "
                "Stockholm 1827: Åtskilliga antekningar af okänd författare, kap. {kap}. "
                "Transkription på svenska Wikisource.")
    langd = langder()
    for kap, verk_id, titel, enhet, beskrivning in (
            (14, "verk:vastgotalagens_lagmanslangd", "Västgötalagens lagmanslängd", "lagman",
             "Förteckning över Västergötlands lagmän från Lumber till Folke, med korta omdömen. "
             "Källvärdet är omstritt; längdens källor är okända."),
            (15, "verk:vastgotalagens_konungalangd", "Västgötalagens konungalängd", "kung",
             "Förteckning över kristna kungar i Sverige från Olof skötkonung, med uppgifter om död och "
             "gravplats."),
            (16, "verk:vastgotalagens_biskopslangd", "Västgötalagens biskopslängd", "biskop",
             "Förteckning över biskopar i Västergötland (Skara) från Sigfrid.")):
        paket.verk.append(Verk(
            id=verk_id, titel=titel, upphov="Tillskrivs prästen i Vidhem", genre="kronika", sprak=["fsv"],
            datering_edtf="1320/1335", datering_fran=13200101, datering_till=13351231,
            beskrivning=beskrivning + " Står i Äldre Västgötalagens handskrift Holm B 59.",
            extern_url=WIKI + urllib.parse.quote(SIDA_LANGDER.replace(" ", "_"))))
        u = f"{utg}:{kap}"
        paket.utgavor.append((verk_id, Utgava(u, referens.format(kap=kap),
                                              "Public domain; transkription CC BY-SA 4.0")))
        paket.vittnen.append((verk_id, Vittne(
            f"vittne:{verk_id.split(':')[1]}:holm_b59", "handskrift", "Stockholm, KB, Holm B 59",
            signum="Holm B 59", datering_edtf="1320/1335", datering_fran=13200101, datering_till=13351231)))
        for nr, p in langd[kap]:
            if nr is None:
                # Lagmanslängdens inledning före den första lagmannen
                paket.passager.append((verk_id, Passage(
                    id=f"{verk_id.split(':')[1]}:inledning", typ="originaltext", adress="inledning",
                    sprak="fsv", text=p, ordning=0, utgava_id=u, url=_sida(SIDA_LANGDER))))
                continue
            paket.passager.append((verk_id, Passage(
                id=f"{verk_id.split(':')[1]}:{nr}", typ="originaltext",
                adress=f"{enhet} {nr} (Collin & Schlyter 1827, kap. {kap})", sprak="fsv", text=p,
                ordning=nr, utgava_id=u, url=_sida(SIDA_LANGDER))))

    # Hednalagen
    utg = "utgava:hednalagen:von_friesen1902"
    lag, kommentar = hednalagen()
    paket.verk.append(Verk(
        id="verk:hednalagen", titel="Hednalagen", genre="lag", sprak=["fsv"],
        beskrivning="Fornsvenskt stadgande om tvekamp vid ärekränkning, ur en okänd västgötsk lag. "
                    "Bevarat bara i eftermedeltida avskrifter; Olavus Petris egenhändiga avskrift i "
                    "Ängsökodexen av Upplandslagen är den äldsta. Tillkomsttiden är okänd.",
        extern_url=WIKI + urllib.parse.quote(SIDA_HEDNALAGEN.replace(" ", "_"))))
    paket.utgavor.append(("verk:hednalagen", Utgava(
        utg, "Otto von Friesen, \"Olavus Petris egenhändiga afskrift af den s. k. Hednalagen i "
             "Ängsöcodex af Upplandslagen\", Samlaren 23 (1902), s. 109–112. Transkription på svenska "
             "Wikisource.", "Public domain; transkription CC BY-SA 4.0")))
    paket.vittnen.append(("verk:hednalagen", Vittne(
        "vittne:hednalagen:olavus_petri", "eftermedeltida_avskrift",
        "Olavus Petris egenhändiga avskrift på fol. 42v i Ängsökodexen av Upplandslagen",
        signum="Ängsöhandskriften fol. 42v", datering_edtf="1520/1552",
        datering_fran=15200101, datering_till=15521231)))
    paket.passager.append(("verk:hednalagen", Passage(
        id="hednalagen:text", typ="originaltext", adress="lagtexten (Olavus Petris avskrift, rad 1–19)",
        sprak="fsv", text=lag, ordning=1, utgava_id=utg, url=_sida(SIDA_HEDNALAGEN))))
    paket.passager.append(("verk:hednalagen", Passage(
        id="hednalagen:olavus_petris_kommentar", typ="originaltext",
        adress="Olavus Petris kommentar till avskriften", sprak="swe", text=kommentar, ordning=2,
        utgava_id=utg, url=_sida(SIDA_HEDNALAGEN))))
    paket.lagg_till_maskinoversattningar(OVERSATTNINGAR.with_name("langder_hednalagen_sv.json"), "fornsvenskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa passagerna utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    if arg.torr:
        for _, p in paket.passager:
            log.info("%-45s %s", p.adress[:45], p.text[:90])
        return
    db.initiera_schema()
    ladda(paket)


if __name__ == "__main__":
    main()

"""
Tolk för legender, uppenbarelser, berättande prosa, vers och fackprosa ur
Språkbankens "Fornsvenska textbankens material" (Korp, CC BY 4.0).

Lagarna och krönikorna har egna tolkar (fornsvenska_lagar,
fornsvenska_kronikor). Här finns:

- legender om de nordiska helgonen (Erik den helige, Sigfrid, Olav,
  Magnus jarl, Katarina av Sverige, Birgitta) och Ansgars levnad efter
  Rimbert, Fornsvenska legendariet och Järteckensboken;
- Birgittas uppenbarelser i de fornsvenska handskrifterna, Birgittas
  autografer och Regula Salvatoris;
- Didrikssagan (Didrik av Bern), Eufemiavisorna och Fornsvenska ordspråk;
- Olaus Petris och Peder Swarts krönikor, på äldre nysvenska;
- läkeböckerna och Peder Månssons Bondakonst.

Ett verk kan ha flera utgåvor när textbanken har texten efter flera
handskrifter (Birgittas uppenbarelser, Fornsvenska legendariet); varje
handskrift blir då en egen utgåva med eget vittne.

Passagerna följer utgåvans sidor. Textbanken markerar sidorna på olika
sätt ("# 3", "[# 3]", "[3: Bu]", "‡‡ 1015", i Olaus Petris krönika "[1]"),
ofta mitt i ett stycke; markören tas bort ur texten och blir passagens
adress. Sidor längre än SIDA_MAX tecken delas vid styckegränser. Texter utan
sidmarkörer delas i avsnitt om högst cirka AVSNITT tecken, ordspråken i
grupper om ORDSPRAK_PER_PASSAGE.

Svenska översättningar gjorda av språkmodell läggs i
data/oversattningar/fornsvenska/ (se RIKTLINJER.md där) och laddas som
egna utgåvor märkta som maskinöversättning.

Användning:
    python -m tolkar.fornsvenska_texter
    python -m tolkar.fornsvenska_texter --torr
"""

import argparse
import bz2
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, Vittne, ladda
from tolkar.fornsvenska_lagar import stycketext

log = logging.getLogger("tolkar.fornsvenska_texter")

KATALOG = Path(__file__).parent.parent / "data" / "raw" / "sprakbanken"
OVERSATTNINGAR = Path(__file__).parent.parent / "data" / "oversattningar" / "fornsvenska"
MENINGSMANGDER = "https://spraakbanken.gu.se/resurser/meningsmangder"
KORPUSAR = ["fsv-aldrereligiosprosa", "fsv-yngrereligiosprosa", "fsv-profanprosa", "fsv-verser",
            "fsv-yngretankebocker", "fsv-nysvenskkronikor"]
SIDA_MAX = 8000
AVSNITT = 4000
ORDSPRAK_PER_PASSAGE = 50


@dataclass
class Text:
    """En text i korpusen, som blir en utgåva av ett verk."""
    titel: str                      # textens titel i korpusen, exakt
    kort: str                       # utgåvans kortnamn i passage-id, t.ex. 'a33'
    vittne: str = "handskrift"      # vittnestyp


@dataclass
class Konfig:
    verk_id: str
    titel: str
    genre: str
    datering: tuple[str, int, int]
    beskrivning: str
    texter: list[Text]
    upphov: str | None = None
    sprak: str = "fsv"
    vers: bool = False
    ordsprak: bool = False


def _d(fran: int, till: int | None = None) -> tuple[str, int, int]:
    till = till or fran
    return (str(fran) if fran == till else f"{fran}/{till}"), fran * 10000 + 101, till * 10000 + 1231


def _en(titel: str, kort: str = "", vittne: str = "handskrift") -> list[Text]:
    return [Text(titel, kort, vittne)]


VERK: list[Konfig] = [
    # Legender om de nordiska helgonen
    Konfig("verk:fsv:erikslegenden", "Legenden om Erik den helige", "legend", _d(1400, 1450),
           "Fornsvensk legend om Erik den helige, kung av Sverige, i Codex Bildstenianus.",
           _en("Legenden om Erik den helige, ur Codex Bildstenianus Ups C 528")),
    Konfig("verk:fsv:om_erik_den_helige", "Om Erik den helige", "legend", _d(1350, 1450),
           "Fornsvensk text om Erik den helige, hans martyrium och under, efter en handskrift i "
           "Vatikanbiblioteket.",
           _en("Om Erik den helige, efter Codex Vat Reg Lat 525")),
    Konfig("verk:fsv:ansgarii_leverne", "Sankt Ansgarii leverne", "legend", _d(1400, 1442),
           "Fornsvensk översättning av Rimberts Vita Anskarii om Ansgars mission i Birka, i "
           "Nådendals klosterbok.",
           _en("Sankt Ansgarii leverne av Rimbertus, ur Codex Holm A 49 Nådendals klosterbok"),
           upphov="Rimbert"),
    Konfig("verk:fsv:sigfridslegenden", "Legenden om Sankt Sigfrid", "legend", _d(1400, 1450),
           "Fornsvensk legend om Sigfrid, missionären i Värend och Västergötland, i Codex Bildstenianus.",
           _en("Legenden om Sankt Sigfrid, ur Codex Bilstenianus")),
    Konfig("verk:fsv:olavslegenden", "Legenden om Olav den helige", "legend", _d(1400, 1450),
           "Fornsvensk legend om Olav den helige, kung av Norge, i Codex Bildstenianus.",
           _en("Legenden om Olav den helige, ur Codex Bildstenianus")),
    Konfig("verk:fsv:magnus_jarl", "Legenden om Magnus jarl av Orkneyöarna", "legend", _d(1400, 1500),
           "Fornsvensk legend om Magnus Erlendsson, jarl av Orkneyöarna.",
           _en("Legeneden om Magnus Jarl av Okenöarna")),
    Konfig("verk:fsv:katarina_av_sverige", "Sankta Katarinas leverne", "legend", _d(1480, 1491),
           "Fornsvensk levnadsbeskrivning av Katarina av Vadstena, Birgittas dotter, i Jöns Buddes bok.",
           _en("Katarina av Sverige, ur Codex Holm A 58, Jöns Buddes bok")),
    Konfig("verk:fsv:birgittas_liv", "Den heliga Birgittas liv (Vita abbreviata)", "legend", _d(1400, 1499),
           "Fornsvensk kortversion av Birgittas levnadsbeskrivning.",
           _en("Den heliga Birgittas liv, Vita abbreviata ur Holm A 33")),
    Konfig("verk:fsv:legendariet", "Fornsvenska legendariet", "legend", _d(1276, 1307),
           "Samling helgonlegender i kyrkoårets ordning, översatt och bearbetad i Sverige omkring "
           "1300, främst efter Jacobus de Voragines Legenda aurea; med svenska tillägg om bland andra "
           "Erik den helige och Botvid.",
           [Text("Fornsvenska legendariet enligt Codex Bureanus", "bureanus"),
            Text("Fornsvenska legendariet enligt Codex Bildstenianus", "bildstenianus")]),
    Konfig("verk:fsv:jarteckensboken", "Järteckensboken", "legend", _d(1350, 1385),
           "Samling Mariamirakel och andra under, i Codex Oxenstiernianus.",
           _en("Järteckensboken, ur Codex Oxenstiernianus")),

    # Birgitta
    Konfig("verk:fsv:birgittaautograferna", "Birgittas autografer", "uppenbarelse", _d(1367),
           "Två uppenbarelser i Birgittas egen hand, de enda bevarade texterna skrivna av henne själv.",
           _en("Birgittaautograferna"), upphov="Birgitta Birgersdotter"),
    Konfig("verk:fsv:birgittas_uppenbarelser", "Birgittas uppenbarelser", "uppenbarelse", _d(1344, 1373),
           "Birgittas uppenbarelser (Revelationes) i fornsvenska handskrifter: översättningen tillbaka "
           "till svenska från de latinska Revelationes, i två redaktioner, och andra handskrifter.",
           [Text("Birgittas uppenbarelser Bok 1-3, ur Codex Holm A 33", "a33"),
            Text("Birgittas uppenbarelser, återöversättningen, första redaktionen, Bok 7", "forsta_red"),
            Text("Birgittas uppenbarelser, återöversättingen, andra redaktionen, Bok 4-8", "andra_red"),
            Text("Birgittas uppenbarelser, åttonde boken, ur Cod Holm A 44", "a44"),
            Text("Heliga Birgittas uppenbarelser ur Codex Oxenstiernianus", "oxenstiernianus"),
            Text("Birgittas uppenbarelser, Sju stycken, fordom i Codex Bergmannius, Lund Mh 20", "sju_stycken"),
            Text("Birgittas uppenbarelser, Birgittinernorska efter Skokloster 5 kvart", "birgittinernorska")],
           upphov="Birgitta Birgersdotter"),
    Konfig("verk:fsv:regula_salvatoris", "Regula Salvatoris och Revelationes extravagantes", "uppenbarelse",
           _d(1346, 1373),
           "Birgittinordens regel, som Birgitta tog emot i en uppenbarelse, och de uppenbarelser som "
           "står utanför Revelationes åtta böcker.",
           _en("Regula Salvatoris och Revelationes Extravagantes, ur Berlin KB 3762"),
           upphov="Birgitta Birgersdotter"),

    # Berättande prosa och vers
    Konfig("verk:fsv:didrikssagan", "Didrikssagan (Didrik av Bern)", "saga", _d(1440, 1480),
           "Fornsvensk bearbetning av den norska Þiðreks saga om Didrik av Bern och hans kämpar, med "
           "berättelsen om Sigurd, Gunnar och Högne och nifungarnas undergång.",
           [Text("Didrik av Bern, hand A", "a"), Text("Didrik av Bern, hand B", "b")]),
    Konfig("verk:fsv:herr_ivan", "Herr Ivan lejonriddaren", "riddardikt", _d(1303),
           "Den första av Eufemiavisorna, översatt till svenska på drottning Eufemias uppdrag efter "
           "Chrétien de Troyes Yvain.",
           _en("Ivan Lejonriddaren, ur SFSS Bd 50 Uppsala 1931"), vers=True),
    Konfig("verk:fsv:hertig_fredrik", "Hertig Fredrik av Normandie", "riddardikt", _d(1308),
           "Eufemiavisa om hertig Fredrik av Normandie, översatt efter en förlorad tysk förlaga.",
           _en("Fredrik av Normandie"), vers=True),
    Konfig("verk:fsv:flores_och_blanzeflor", "Flores och Blanzeflor", "riddardikt", _d(1312),
           "Den sista av Eufemiavisorna, om kärleken mellan Flores och Blanzeflor.",
           _en("Flores och Blanzeflor"), vers=True),
    Konfig("verk:fsv:ordsprak", "Fornsvenska ordspråk", "ordsprak", _d(1325, 1525),
           "Samling fornsvenska ordspråk.", _en("Fornsvenska Ordspråk"), ordsprak=True),

    # Krönikor på äldre nysvenska
    Konfig("verk:olaus_petris_kronika", "En swensk cröneka", "kronika", _d(1530, 1540),
           "Olaus Petris svenska krönika från landets äldsta tid till 1520, skriven med en för sin tid "
           "kritisk hållning till de äldre krönikorna.",
           _en("Olaus Petris Krönika"), upphov="Olaus Petri", sprak="swe"),
    Konfig("verk:peder_swarts_kronika", "Peder Swarts krönika", "kronika", _d(1560, 1562),
           "Krönika om Gustav Vasas regering fram till 1533, skriven av biskopen Peder Swart.",
           _en("Peder Swarts krönika"), upphov="Peder Swart", sprak="swe"),

    # Fackprosa
    Konfig("verk:fsv:bondakonst", "Bondakonst", "facktext", _d(1510, 1520),
           "Peder Månssons lärodikt och handbok om jordbruk, bearbetad efter antika och medeltida "
           "lantbruksförfattare.",
           _en("Bondakonst av Peder Månsson"), upphov="Peder Månsson"),
    Konfig("verk:fsv:peder_manssons_lakebok", "Peder Månssons läkebok", "facktext", _d(1500, 1534),
           "Peder Månssons läkebok, översatt efter Johannes de Rupescissa, efter hans egen handskrift i "
           "Linköpings stiftsbibliotek.",
           _en("Läkedom, efter Peder Månssons handskrift i Linköpings Stiftsbibliotek"), upphov="Peder Månsson"),
    *[Konfig(f"verk:fsv:lakebok_{kort}", titel, "facktext", datering, beskrivning, _en(korpustitel), upphov=upphov)
      for kort, titel, datering, beskrivning, korpustitel, upphov in [
        ("1", "Läkebok 1: blandad läkedom", _d(1500, 1600),
         "Läkebok som inleds med Henrik Harpestrengs läkedomar.", "Läkebok 1: blandad läkedom, ur Codex AM",
         None),
        ("2", "Läkebok 2", _d(1400, 1500), "Läkebok i pappershandskriften Ups C 601.",
         "Läkebok 2, ur pappershandskriften Ups C 601", None),
        ("3", "Läkebok 3", _d(1400, 1500), "Läkebok i Codex Huss.", "Läkebok 3, ur codex Huss", None),
        ("4", "Läkebok 4", _d(1400, 1500), "Läkebok i Nådendals klosterbok (Holm A 49).",
         "Läkebok 4, ur Codex Holm A 49", None),
        ("5_6", "Läkebok 5 och 6", _d(1400, 1500), "Läkeböcker i Codex Benz 19.",
         "Läkebok 5 och 6, ur Codex 19 Benz", None),
        ("7", "Läkebok 7", _d(1500, 1600), "Läkebok i Codex Linc M 5.", "Läkebok 7, efter Codex linc M 5", None),
        ("8", "Läkebok 8", _d(1500, 1600), "Läkebok i Codex Grensholmensis i Linköping.",
         "Läkebok, 8 ur codex Grensholmensis i Linköping", None),
        ("10", "Läkebok 10: zodiaken och månaderna", _d(1400, 1500),
         "Om djurkretsen, månaderna och åderlåtning, efter en handskrift i Rålambska samlingen.",
         "Läkebok 10: Zoodiaken, månaderna m m, efter hskr i Rålambska samlingen", None),
        ("11", "Läkebok 11: månaderna", _d(1500, 1600),
         "Om månaderna, efter KB:s handskrift K 45, kompletterad på danska ur Codex Grensholmensis.",
         "Läkebok 11: Månaderna, efter KBs handskrift med gammal signatur K 45, supplerad på Danska ur "
         "codex Grensholmensis", None),
        ("benz_22", "Läkedomar i Codex Benz 22", _d(1400, 1500), "Läkedomar i Codex Ups Benz 22.",
         "Läkedomar, codex Ups Benz 22", None),
    ]],
]

# Sidmarkörer i den ordning de prövas; den första som finns i en text används
MARKORER = [
    re.compile(r"\[?#\s*(\d+[a-z]?)\]?"),            # "# 3", "[# 3]"
    re.compile(r"\[(\d+):\s*[A-Za-zÅÄÖåäö]+\]"),      # "[3: Bu]"
    re.compile(r"‡‡\s*(\d+)"),                       # "‡‡ 1015"
    re.compile(r"\[(\d+)\]"),                         # Olaus Petri "[1]"
]
# Bladnumren i Codex Bildstenianus står bredvid sidnumren och tas bort
BLADNUMMER = re.compile(r"\[?‡‡\s*\d+\]?\s*")
ORDSPRAK = re.compile(r"<(\d+)>\s*")


def hamta(korpus: str) -> Path:
    fil = KATALOG / f"{korpus}.xml.bz2"
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        url = f"{MENINGSMANGDER}/{korpus}.xml.bz2"
        log.info("Hämtar %s", url)
        urllib.request.urlretrieve(url, fil)
    return fil


def _dela_lang(text: str, max_tecken: int) -> list[str]:
    """Delar text vid radbrytningar i delar om högst cirka max_tecken."""
    delar, buf = [], ""
    for rad in text.split("\n"):
        if buf and len(buf) + len(rad) > max_tecken:
            delar.append(buf.strip())
            buf = ""
        buf += rad + "\n"
    if buf.strip():
        delar.append(buf.strip())
    return delar


def segment(stycken: list[str], ordsprak: bool = False) -> list[tuple[str, str]]:
    """(adress, text) per passage; se modulens beskrivning."""
    # Korpusens titelrad ("[Fornsvenska legendariet enligt Codex Bildstenianus]") hör inte till texten
    if stycken and re.fullmatch(r"\[[^\]]*\]", stycken[0]) and not any(m.fullmatch(stycken[0]) for m in MARKORER):
        stycken = stycken[1:]
    text = "\n".join(stycken)
    if ordsprak:
        delar = [d.strip() for d in ORDSPRAK.split(text)]
        par = list(zip(delar[1::2], delar[2::2]))
        ut = []
        for i in range(0, len(par), ORDSPRAK_PER_PASSAGE):
            grupp = par[i:i + ORDSPRAK_PER_PASSAGE]
            ut.append((f"nr {grupp[0][0]}–{grupp[-1][0]}", "\n".join(f"{nr}. {t}" for nr, t in grupp)))
        return ut
    markor = next((m for m in MARKORER if len(m.findall(text)) >= 2), None)
    if markor is None:
        return [(f"avsnitt {i}", t) for i, t in enumerate(_dela_lang(text, AVSNITT), 1)]
    if markor is MARKORER[0]:
        text = BLADNUMMER.sub("", text)
    delar = markor.split(text)
    ut = []
    # Text före första sidmarkören; en ensam rubrik ("Herr Ivan") är ingen passage
    if len(delar[0].strip()) >= 60:
        ut.append(("inledning", delar[0].strip()))
    for sida, innehall in zip(delar[1::2], delar[2::2]):
        innehall = innehall.strip()
        if not innehall:
            continue
        bitar = _dela_lang(innehall, SIDA_MAX // 2) if len(innehall) > SIDA_MAX else [innehall]
        for k, bit in enumerate(bitar, 1):
            ut.append((f"s. {sida}" + (f", del {k}" if len(bitar) > 1 else ""), bit))
    return ut


def _id_del(adress: str) -> str:
    """Adressens form i passage-id: 's. 12, del 2' → 's12_2', 'nr 1–50' → 'nr1-50'."""
    return re.sub(r"[^0-9a-zA-Z_-]", "", adress.replace(", del ", "_").replace("–", "-")
                  .replace("avsnitt ", "a").replace("inledning", "inl"))


def bygg_paket() -> Kallpaket:
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="fornsvenska_texter",
            namn="Fornsvenska textbankens material: legender, uppenbarelser, berättande prosa, vers och fackprosa",
            utgivare="Språkbanken Text, Göteborgs universitet (efter Fornsvenska textbanken, Lunds universitet)",
            url="https://spraakbanken.gu.se/resurser/fsv", licens="CC BY 4.0", version="DOI 10.23695/pyqj-0s75"),
        verk=[])
    efter_titel = {t.titel: (k, t) for k in VERK for t in k.texter}
    hittade: dict[str, tuple[str, list[str], str | None]] = {}
    for korpus in KORPUSAR:
        with bz2.open(hamta(korpus)) as fh:
            for _, el in ET.iterparse(fh, events=("end",)):
                if el.tag != "text":
                    continue
                titel = el.get("title", "").strip()
                if titel in efter_titel:
                    hittade[titel] = (korpus, [stycketext(p) for p in el.findall("paragraph")], el.get("date"))
                el.clear()
    saknas = sorted(set(efter_titel) - set(hittade))
    if saknas:
        raise RuntimeError(f"Texterna finns inte i korpusarna: {', '.join(saknas)}")

    for k in VERK:
        slug = k.verk_id.split(":")[-1]
        korpus = hittade[k.texter[0].titel][0]
        paket.verk.append(Verk(
            id=k.verk_id, titel=k.titel, upphov=k.upphov, genre=k.genre, sprak=[k.sprak],
            datering_edtf=k.datering[0], datering_fran=k.datering[1], datering_till=k.datering[2],
            beskrivning=k.beskrivning,
            extern_url=f"https://spraakbanken.gu.se/korp/?mode=old_swedish#?corpus={korpus}"))
        ordning = 0
        for t in k.texter:
            korpus, stycken, datum = hittade[t.titel]
            del_id = f"{slug}_{t.kort}" if t.kort else slug
            utgava_id = f"utgava:fsv:{del_id}"
            paket.utgavor.append((k.verk_id, Utgava(
                utgava_id, f"Fornsvenska textbanken (Lunds universitet), i Språkbankens korpus {korpus}: {t.titel}.",
                "CC BY 4.0")))
            h = re.findall(r"\d{4}", datum or "")
            # Korpusens datering är för Eufemiavisorna verkets egen, inte handskriftens
            if h and _d(int(h[0]), int(h[-1]))[0] != k.datering[0]:
                edtf, fran, till = _d(int(h[0]), int(h[-1]))
                paket.vittnen.append((k.verk_id, Vittne(
                    f"vittne:fsv:{del_id}", t.vittne, t.titel, datering_edtf=edtf, datering_fran=fran,
                    datering_till=till)))
            sett: dict[str, int] = {}
            n = 0
            for adress, text in segment(stycken, k.ordsprak):
                pid = f"fsv:{del_id}:{_id_del(adress)}"
                # Sidnumreringen kan börja om (flera band i samma text)
                sett[pid] = sett.get(pid, 0) + 1
                if sett[pid] > 1:
                    pid += f"_{sett[pid]}"
                ordning += 1
                n += 1
                paket.passager.append((k.verk_id, Passage(
                    id=pid, typ="originaltext", adress=(f"{t.kort}, " if len(k.texter) > 1 else "") + adress,
                    sprak=k.sprak, text=text, ordning=ordning, utgava_id=utgava_id)))
            log.info("%-48s %-18s %5d passager, %8d tecken", k.titel[:48], t.kort or "-", n,
                     sum(map(len, stycken)))
    if OVERSATTNINGAR.exists():
        for fil in sorted(OVERSATTNINGAR.glob("*.json")):
            # Olaus Petris och Peder Swarts krönikor är skrivna på 1500-talets svenska
            nysvensk = fil.name.startswith(("olaus_petris_kronika", "peder_swarts_kronika"))
            paket.lagg_till_maskinoversattningar(fil, "äldre nysvenskan" if nysvensk else "fornsvenskan")
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--torr", action="store_true", help="tolka och visa statistik utan att ladda")
    arg = tolk.parse_args()
    paket = bygg_paket()
    paket.kontrollera()
    log.info("%d verk, %d utgåvor, %d passager", len(paket.verk), len(paket.utgavor), len(paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

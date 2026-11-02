"""
Tolk för arabiska källor om rus, slaver och Norden ur OpenITI (CC BY-NC-SA
4.0): Ibn Fadlans reseberättelse i sin helhet och avsnitt ur Ibn
Khurradadhbih, Ibn Rusta, al-Masʿudi, Ibn Hawqal, al-Idrisi och
al-Qazwini (med al-Turtushis berättelse om Hedeby).

OpenITI:s märkning tas bort: sidnummer (PageV01P045), milstolpar (ms24),
radbrytningar (~~) och notnummer («12»). Avsnitten väljs efter OpenITI:s
rubriker eller, i de stora geografiska verken, som stycken.

Svenska översättningar saknas i fri form; de är gjorda av en språkmodell
från arabiskan, ligger i data/oversattningar/arabiska_sv.json och märks som
ogranskade maskinöversättningar i en egen utgåva per verk.

Användning:
    python -m tolkar.arabiska
    python -m tolkar.arabiska --dumpa FIL
"""

import argparse
import json
import logging
import re
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda

log = logging.getLogger("tolkar.arabiska")

ROT = Path(__file__).parent.parent
KATALOG = ROT / "data" / "raw" / "openiti"
OVERSATTNINGAR = ROT / "data" / "oversattningar" / "arabiska_sv.json"
GITHUB = "https://raw.githubusercontent.com/OpenITI"
MASKIN = ("Svensk översättning gjord av språkmodell (Claude) från arabiskan. Ogranskad; citera "
          "originalet eller en tryckt översättning.")

# nyckel: (titel, upphov, datering (edtf, från, till), beskrivning, OpenITI-sökväg,
#          urval: [("rubrik", text, adress)] eller [("stycken", första, sista, adress)])
VERK = {
    "ibn_fadlan": (
        "Risala (reseberättelse till Volgabulgarerna)", "Ahmad ibn Fadlan", ("0922/0923", 9220101, 9231231),
        "Berättelse om den abbasidiska beskickningen 921–922 till Volgabulgarernas kung, med ögonvittnes"
        "skildringen av rus vid Volga och en hövdings skeppsbegravning.",
        "0325AH/master/data/0309IbnFadlan/0309IbnFadlan.Rihla/0309IbnFadlan.Rihla.Shamela0011772-ara1.completed",
        [("rubrik", "", "inledning"), ("rubrik", "العجم والأتراك", "resan genom perser och turkfolk"),
         ("rubrik", "الصقالبة", "hos saqaliba (Volgabulgarerna)"), ("rubrik", "الروسية", "rus vid Volga"),
         ("rubrik", "الخزر", "khazarerna")]),
    "ibn_khurradadhbih": (
        "Kitab al-masalik wa-l-mamalik", "Ibn Khurradadhbih", ("0846/0885", 8460101, 8851231),
        "Geografisk handbok över vägar och provinser; avsnittet om rusköpmännens handelsvägar.",
        "0300AH/master/data/0300IbnKhurdadhbih/0300IbnKhurdadhbih.MasalikWaMamalik/"
        "0300IbnKhurdadhbih.MasalikWaMamalik.Shamela0011800BK1-ara1.mARkdown",
        [("rubrik", "مسلك تجار الروس", "rusköpmännens väg")]),
    "ibn_rusta": (
        "Kitab al-aʿlaq al-nafisa", "Ibn Rusta", ("0903/0913", 9030101, 9131231),
        "Geografiskt uppslagsverk; avsnitten om rus och om slaverna.",
        "0300AH/master/data/0300IbnRusta/0300IbnRusta.AclaqNafisa/0300IbnRusta.AclaqNafisa.Masaha004394-ara1",
        [("rubrik", "الروسية", "rus (al-Rusiya)"), ("rubrik", "الصقلبية", "slaverna (al-Saqaliba)")]),
    "masudi": (
        "Muruj al-dhahab", "al-Masʿudi", ("0943/0956", 9430101, 9561231),
        "Världshistoria och geografi; avsnitten om rus, deras färder och seder.",
        "0350AH/master/data/0346Mascudi/0346Mascudi.MurujDhahab/0346Mascudi.MurujDhahab.JK010344-ara1.completed",
        [("rubrik", "ذكر بحر نيطش", "Svarta havet och rus"), ("rubrik", "بنو أمية بالأندلس", "al-Andalus och majus"),
         ("rubrik", "عادة حرق الموتى", "khazarernas huvudstad, rus och likbränning"),
         ("rubrik", "الروس وأجناسهم", "rus och deras folk")]),
    "ibn_hawqal": (
        "Surat al-ard", "Ibn Hawqal", ("0967/0988", 9670101, 9881231),
        "Geografi över den islamiska världen; avsnittet om Kaspiska havet, khazarerna, Itil och rus.",
        "0375AH/master/data/0367IbnHawqal/0367IbnHawqal.SuratArd/0367IbnHawqal.SuratArd.Shamela0011780-ara1.mARkdown",
        [("stycken", 437, 447, "Kaspiska havet, khazarerna, Itil, burtas och rus")]),
    "idrisi": (
        "Nuzhat al-mushtaq", "al-Sharif al-Idrisi", ("1154", 11540101, 11541231),
        "Världsgeografi skriven för Roger II av Sicilien; sjunde klimatets tredje och fjärde del med "
        "Danmark, Norge (Narfagha), Finmark (Sverige), Estland och rus.",
        "0575AH/master/data/0560SharifIdrisi/0560SharifIdrisi.NuzhatMushtaq/"
        "0560SharifIdrisi.NuzhatMushtaq.Shamela0011787-ara1.mARkdown",
        [("stycken", 2743, 2749, "sjunde klimatet, tredje delen"),
         ("stycken", 2751, 2771, "sjunde klimatet, fjärde delen")]),
    "qazwini": (
        "Athar al-bilad wa-akhbar al-ʿibad", "Zakariya al-Qazwini", ("1275/1276", 12750101, 12761231),
        "Kosmografi och geografi; artiklarna om rus, om Shalashwiq (Hedeby, efter al-Turtushi) och om Waranc.",
        "0700AH/master/data/0682ZakariyaQazwini/0682ZakariyaQazwini.AtharBilad/"
        "0682ZakariyaQazwini.AtharBilad.Shamela0009631-ara1.completed",
        [("rubrik", "بلاد الروس", "rus land"), ("rubrik", "شلشويق", "Shalashwiq (Hedeby)"),
         ("rubrik", "ورنك", "Waranc")]),
}


def hamta(sokvag: str) -> str:
    fil = KATALOG / sokvag.rsplit("/", 1)[1]
    if not fil.exists():
        KATALOG.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"{GITHUB}/{sokvag}", fil)
    return fil.read_text(encoding="utf-8").split("#META#Header#End#", 1)[-1]


def rensa(text: str) -> str:
    text = re.sub(r"PageV\d+P\d+|\bms\d+\b|«\d+»|\(\d+\)", " ", text)
    text = text.replace("~~", " ")
    text = re.sub(r"(?m)^#\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def avsnitt() -> list[dict]:
    ut = []
    for nyckel, (_, _, _, _, sokvag, urval) in VERK.items():
        text = hamta(sokvag)
        delar = re.split(r"(?m)^(### \|+ .*)$", text)
        rubriker = [(delar[i].strip(), delar[i + 1]) for i in range(1, len(delar), 2)]
        stycken = re.split(r"\n# ", text)
        for i, val in enumerate(urval, start=1):
            if val[0] == "rubrik":
                _, sok, adress = val
                traffar = [t for r, t in rubriker if (sok in r if sok else r.strip("#| ") == "")]
                if not traffar:
                    raise ValueError(f"{nyckel}: rubriken '{sok}' finns inte")
                original = traffar[0]
            else:
                _, forsta, sista, adress = val
                original = "\n".join(stycken[forsta:sista + 1])
            ut.append(dict(verk=nyckel, id=f"{nyckel}:{i}:ara", adress=adress, ordning=i, text=rensa(original)))
    return ut


def bygg_paket() -> Kallpaket:
    oversattning = json.loads(OVERSATTNINGAR.read_text(encoding="utf-8")) if OVERSATTNINGAR.exists() else {}
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="openiti", namn="Arabiska källor om rus och Norden (OpenITI)", utgivare="OpenITI",
            url="https://openiti.org", licens="CC BY-NC-SA 4.0", version="2026-10"),
        verk=[])
    for nyckel, (titel, upphov, (edtf, fran, till), beskrivning, sokvag, _) in VERK.items():
        verk_id = f"verk:arabisk:{nyckel}"
        paket.verk.append(Verk(id=verk_id, titel=titel, upphov=upphov, genre="geografi", sprak=["ara"],
                               datering_edtf=edtf, datering_fran=fran, datering_till=till, beskrivning=beskrivning,
                               extern_url=f"https://github.com/OpenITI/{sokvag.split('/master/')[0]}"))
        paket.utgavor.append((verk_id, Utgava(f"utgava:arabisk:{nyckel}:openiti",
                                              f"OpenITI: {sokvag.rsplit('/', 1)[1]}", "CC BY-NC-SA 4.0")))
        paket.utgavor.append((verk_id, Utgava(f"utgava:arabisk:{nyckel}:sv_modell", MASKIN, "CC BY-NC-SA 4.0")))
    saknas = []
    for a in avsnitt():
        verk_id = f"verk:arabisk:{a['verk']}"
        paket.passager.append((verk_id, Passage(id=a["id"], typ="originaltext", adress=a["adress"], sprak="ara",
                                                text=a["text"], ordning=a["ordning"],
                                                utgava_id=f"utgava:arabisk:{a['verk']}:openiti")))
        sv_id = a["id"].rsplit(":", 1)[0] + ":sv"
        if sv_id in oversattning:
            paket.passager.append((verk_id, Passage(
                id=sv_id, typ="oversattning", adress=a["adress"] + " (maskinöversättning)", sprak="swe",
                text=oversattning[sv_id], ordning=1000 + a["ordning"],
                utgava_id=f"utgava:arabisk:{a['verk']}:sv_modell")))
        else:
            saknas.append(sv_id)
    if saknas:
        log.warning("%d avsnitt saknar svensk översättning: %s", len(saknas), ", ".join(saknas))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--dumpa", type=Path, help="skriv originaltexterna som JSON och avsluta")
    tolk.add_argument("--torr", action="store_true", help="tolka utan att ladda")
    arg = tolk.parse_args()
    if arg.dumpa:
        texter = avsnitt()
        arg.dumpa.write_text(json.dumps(texter, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("%d avsnitt, %d tecken", len(texter), sum(len(t["text"]) for t in texter))
        return
    paket = bygg_paket()
    paket.kontrollera()
    log.info("%d verk, %d passager", len(paket.verk), len(paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

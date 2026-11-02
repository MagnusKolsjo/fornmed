"""
Tolk för romerska och senantika källor om Norden: Tacitus Germania, Plinius
den äldres Naturalis historia (avsnitten om Norden), Pomponius Mela och
Prokopios.

Originaltexterna och de engelska översättningarna kommer från Perseus
Digital Library (CC BY-SA 4.0), Pomponius Mela från The Latin Library.
Svenska översättningar saknas i fri form; de är gjorda av en språkmodell
från originalspråket, ligger i data/oversattningar/romerska_sv.json och
märks som ogranskade maskinöversättningar i en egen utgåva.

- Germania: alla 46 kapitel, latin, engelska (Church & Brodribb 1876) och svenska.
- Plinius: de kapitel som handlar om Norden (2.67, 4.13, 4.14, 4.16, 8.15,
  37.3 i Mayhoffs indelning), latin, engelska (Bostock & Riley 1855) och svenska.
- Pomponius Mela, De chorographia 3.25–33 och 3.44–46, latin och svenska.
- Prokopios, Krigen 6.14–15 (herulerna och Thule), grekiska och svenska.

Användning:
    python -m tolkar.romerska
    python -m tolkar.romerska --dumpa FIL   (originaltexterna som JSON, för översättning)
"""

import argparse
import html
import json
import logging
import re
import urllib.request
from pathlib import Path

import db
from kallpaket import Kallpaket, Kallsamling, Passage, Utgava, Verk, ladda
from tolkar import perseus

log = logging.getLogger("tolkar.romerska")

ROT = Path(__file__).parent.parent
OVERSATTNINGAR = ROT / "data" / "oversattningar" / "romerska_sv.json"
MELA_URL = "https://www.thelatinlibrary.com/pomponius3.html"
MELA_FIL = ROT / "data" / "raw" / "latinlibrary" / "pomponius3.html"
MASKIN = ("Svensk översättning gjord av språkmodell (Claude) från originalspråket. Ogranskad; "
          "citera originalet eller en tryckt översättning.")
PERSEUS = "Perseus Digital Library, Tufts University (CC BY-SA 4.0)"

# Plinius: Mayhoffs kapitel och motsvarande kapitel i Bostock & Rileys översättning
PLINIUS = [(("2", "67"), [("2", "67")], "Nordliga oceanen och dess omsegling"),
           (("4", "13"), [("4", "27")], "Kimbrernas udde, Codanus sinus och Scatinavia"),
           (("4", "14"), [("4", "28")], "Germaniens folk"),
           (("4", "16"), [("4", "30")], "Britannien och Thule"),
           (("8", "15"), [("8", "15"), ("8", "16")], "Nordens djur: älg, achlis och uroxe"),
           (("37", "3"), [("37", "11")], "Bärnstenen och öarna i norra oceanen")]
MELA = [("25", "33", "Germanien, Codanus sinus och Sarmatien"), ("44", "46", "Öarna i norr och Scadinavia")]
PROKOPIOS = [("14", "Herulerna"), ("15", "Herulerna i Thule och folken där")]


def _mela() -> dict[str, str]:
    if not MELA_FIL.exists():
        MELA_FIL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MELA_URL, MELA_FIL)
    t = html.unescape(re.sub(r"<[^>]+>", " ", MELA_FIL.read_text(encoding="latin-1")))
    return perseus.paragrafer(re.sub(r"\s+", " ", t))


def _per_kapitel(urn: str) -> dict[str, str]:
    """Textdelar sammanslagna per kapitel (Germanias latinska text är delad i paragrafer)."""
    ut: dict[str, list[str]] = {}
    for vag, text in perseus.las(urn):
        ut.setdefault(vag[0], []).append(text)
    return {kap: " ".join(delar) for kap, delar in ut.items()}


GITHUB_PERSEUS = "https://github.com/PerseusDL/canonical-{repo}/blob/master/data/{urn}.xml"
SCAIFE = "https://scaife.perseus.org/reader/urn:cts:{repo}:{urn}:{ref}/"


def _github(urn: str) -> str:
    forfattare, verk, _ = urn.split(".", 2)
    repo = "greekLit" if forfattare.startswith("tlg") else "latinLit"
    return GITHUB_PERSEUS.format(repo=repo, urn=f"{forfattare}/{verk}/{urn}")


def originaltexter() -> list[dict]:
    """Alla passager före översättning: verk, id, adress, språk och text."""
    ut = []
    ger_lat, ger_eng = _per_kapitel("phi1351.phi002.perseus-lat2"), _per_kapitel("phi1351.phi002.perseus-eng2")
    for kap, text in sorted(ger_lat.items(), key=lambda x: int(x[0])):
        # Scaife visar inte Perseus nyare latinska Germania; länken går till källfilen
        ut.append(dict(verk="germania", id=f"germania:{kap}:lat", adress=f"kap. {kap}", sprak="lat",
                       text=re.sub(r"\s*\[\d+\]\s*", " ", text).strip(), ordning=int(kap),
                       url=_github("phi1351.phi002.perseus-lat2")))
        if kap in ger_eng:
            ut.append(dict(verk="germania", id=f"germania:{kap}:eng", adress=f"kap. {kap}", sprak="eng",
                           text=ger_eng[kap], ordning=1000 + int(kap), utgava="eng",
                           url=_github("phi1351.phi002.perseus-eng2")))
    lat, eng = dict(perseus.las("phi0978.phi001.perseus-lat2")), dict(perseus.las("phi0978.phi001.perseus-eng1"))
    for i, ((bok, kap), engkap, rubrik) in enumerate(PLINIUS, start=1):
        text = lat[(bok, kap)]
        # Paragrafnumren behålls i texten, så att avsnitt kan citeras som 4.96
        paragrafer = re.findall(r"\[(\d+)\]", text)
        omfang = f"{bok}.{paragrafer[0]}–{paragrafer[-1]}" if paragrafer else f"{bok}"
        adress = f"bok {bok}, kap. {kap} (§ {omfang}): {rubrik}"
        ut.append(dict(verk="plinius", id=f"plinius:{bok}.{kap}:lat", adress=adress, sprak="lat", text=text,
                       ordning=i, url=SCAIFE.format(repo="latinLit", urn="phi0978.phi001.perseus-lat2",
                                                    ref=f"{bok}.{kap}")))
        ut.append(dict(verk="plinius", id=f"plinius:{bok}.{kap}:eng", adress=adress, sprak="eng",
                       text=" ".join(eng[k] for k in engkap), ordning=1000 + i, utgava="eng",
                       url=_github("phi0978.phi001.perseus-eng1")))
    mela = _mela()
    for i, (fran, till, rubrik) in enumerate(MELA, start=1):
        text = " ".join(f"[{n}] {mela[str(n)]}" for n in range(int(fran), int(till) + 1) if str(n) in mela)
        ut.append(dict(verk="mela", id=f"mela:3.{fran}-{till}:lat", adress=f"bok 3, § {fran}–{till}: {rubrik}",
                       sprak="lat", text=text, ordning=i, url=MELA_URL))
    grc = dict(perseus.las("tlg4029.tlg001.perseus-grc2"))
    for kap, rubrik in PROKOPIOS:
        delar = [(k, t) for k, t in grc.items() if k[:2] == ("6", kap)]
        text = " ".join(f"[{k[2]}] {t}" if len(k) > 2 else t for k, t in delar)
        ut.append(dict(verk="prokopios", id=f"prokopios:6.{kap}:grc", adress=f"bok 6, kap. {kap}: {rubrik}",
                       sprak="grc", text=text, ordning=int(kap),
                       url=SCAIFE.format(repo="greekLit", urn="tlg4029.tlg001.perseus-grc2", ref=f"6.{kap}")))
    return ut


VERK = {
    "germania": dict(
        url="https://github.com/PerseusDL/canonical-latinLit/tree/master/data/phi1351/phi002",
        id="verk:tacitus_germania", titel="Germania (De origine et situ Germanorum)",
        upphov="Publius Cornelius Tacitus", genre="geografi", sprak=["lat"], edtf="0098",
        fran=980101, till=981231,
        beskrivning="Etnografisk skrift om Germanien och dess folk, skriven 98 e.Kr. Kap. 44–45 "
                    "om suionerna och sitonerna är den äldsta skildringen av folk i nuvarande Sverige.",
        lat=("utgava:tacitus_germania:perseus_lat", "Tacitus, Germania, latinsk text i " + PERSEUS),
        eng=("utgava:tacitus_germania:church_brodribb",
             "A. J. Church & W. J. Brodribb (övers.), The Agricola and Germania of Tacitus, "
             "London 1876, i " + PERSEUS)),
    "plinius": dict(
        url="https://scaife.perseus.org/reader/urn:cts:latinLit:phi0978.phi001.perseus-lat2/",
        id="verk:plinius_naturalis_historia", titel="Naturalis historia (avsnitt om Norden)",
        upphov="Gaius Plinius Secundus (den äldre)", genre="geografi", sprak=["lat"], edtf="0077",
        fran=770101, till=791231,
        beskrivning="Encyklopedi i 37 böcker, avslutad omkring 77 e.Kr. Här bara kapitlen om Norden: "
                    "Codanus sinus, Scatinavia, Nordens djur och bärnstenen.",
        lat=("utgava:plinius:mayhoff", "C. Mayhoff (utg.), Naturalis historia, Leipzig 1892–1909, i "
             + PERSEUS + "; den textkritiska apparaten är borttagen"),
        eng=("utgava:plinius:bostock_riley",
             "J. Bostock & H. T. Riley (övers.), The Natural History of Pliny, London 1855, i "
             + PERSEUS + "; kapitelindelningen avviker från Mayhoffs")),
    "mela": dict(
        url=MELA_URL,
        id="verk:pomponius_mela", titel="De chorographia (avsnitt om Norden)", upphov="Pomponius Mela",
        genre="geografi", sprak=["lat"], edtf="0043/0044", fran=430101, till=441231,
        beskrivning="Den äldsta bevarade latinska geografin, skriven omkring 43–44 e.Kr. Bok 3 "
                    "om Codanus sinus och Scadinavia.",
        lat=("utgava:pomponius_mela:latinlibrary", "Pomponius Mela, De chorographia, latinsk text i "
             "The Latin Library (thelatinlibrary.com); paragrafnumren följer den utgåvan")),
    "prokopios": dict(
        url="https://scaife.perseus.org/reader/urn:cts:greekLit:tlg4029.tlg001.perseus-grc2/",
        id="verk:prokopios_krigen", titel="Krigen (Hyper ton polemon logoi), bok 6 kap. 14–15",
        upphov="Prokopios från Caesarea", genre="kronika", sprak=["grc"], edtf="0550/0553",
        fran=5500101, till=5531231,
        beskrivning="Historia över Justinianus krig, skriven omkring 550–553. Bok 6 kap. 14–15 om "
                    "herulerna, deras vandring till Thule och folken där (skrithifinoi, gautoi).",
        lat=("utgava:prokopios:haury", "J. Haury (utg.), Procopii Caesariensis opera omnia, Leipzig "
             "1905–13, grekisk text i " + PERSEUS)),
}


def bygg_paket() -> Kallpaket:
    oversattning = json.loads(OVERSATTNINGAR.read_text(encoding="utf-8")) if OVERSATTNINGAR.exists() else {}
    paket = Kallpaket(
        kallsamling=Kallsamling(
            id="romerska", namn="Romerska och senantika källor om Norden",
            utgivare="Perseus Digital Library; The Latin Library", url="https://github.com/PerseusDL",
            licens="CC BY-SA 4.0 (Perseus); översättningarna till svenska CC BY-SA 4.0", version="2026-10"),
        verk=[])
    for nyckel, v in VERK.items():
        paket.verk.append(Verk(id=v["id"], titel=v["titel"], upphov=v["upphov"], genre=v["genre"],
                               sprak=v["sprak"], datering_edtf=v["edtf"], datering_fran=v["fran"],
                               datering_till=v["till"], beskrivning=v["beskrivning"], extern_url=v["url"]))
        paket.utgavor.append((v["id"], Utgava(v["lat"][0], v["lat"][1], "CC BY-SA 4.0")))
        if "eng" in v:
            paket.utgavor.append((v["id"], Utgava(v["eng"][0], v["eng"][1], "CC BY-SA 4.0")))
        paket.utgavor.append((v["id"], Utgava(f"{v['id'].replace('verk:', 'utgava:')}:sv_modell", MASKIN,
                                              "CC BY-SA 4.0")))
    saknas = []
    for o in originaltexter():
        v = VERK[o["verk"]]
        typ = "oversattning" if o["sprak"] == "eng" else "originaltext"
        utg = v["eng"][0] if o.get("utgava") == "eng" else v["lat"][0]
        paket.passager.append((v["id"], Passage(id=o["id"], typ=typ, adress=o["adress"], sprak=o["sprak"],
                                                text=o["text"], ordning=o["ordning"], utgava_id=utg,
                                                url=o.get("url"))))
        if o["sprak"] in ("lat", "grc"):
            sv_id = o["id"].rsplit(":", 1)[0] + ":sv"
            if sv_id in oversattning:
                paket.passager.append((v["id"], Passage(
                    id=sv_id, typ="oversattning", adress=o["adress"] + " (maskinöversättning)", sprak="swe",
                    text=oversattning[sv_id], ordning=2000 + o["ordning"],
                    utgava_id=f"{v['id'].replace('verk:', 'utgava:')}:sv_modell",
                    # Underlaget för en maskinöversättning är originalet
                    url=o.get("url"))))
            else:
                saknas.append(sv_id)
    if saknas:
        log.warning("%d passager saknar svensk översättning: %s", len(saknas), ", ".join(saknas[:8]))
    return paket


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--dumpa", type=Path, help="skriv originaltexterna som JSON och avsluta")
    tolk.add_argument("--torr", action="store_true", help="tolka utan att ladda")
    arg = tolk.parse_args()
    if arg.dumpa:
        texter = [o for o in originaltexter() if o["sprak"] in ("lat", "grc")]
        arg.dumpa.write_text(json.dumps(texter, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("%d originaltexter till %s", len(texter), arg.dumpa)
        return
    paket = bygg_paket()
    paket.kontrollera()
    log.info("%d verk, %d passager", len(paket.verk), len(paket.passager))
    if not arg.torr:
        db.initiera_schema()
        ladda(paket)


if __name__ == "__main__":
    main()

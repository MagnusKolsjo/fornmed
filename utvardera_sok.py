"""
Mäter sökningens träffsäkerhet mot frågor med kända svar.

Varje fråga har ett facit: ett reguljärt uttryck som en relevant passage ska
matcha (i passagens id eller text, på valfritt språk) och, där svaret är
givna ställen, de id-prefix passagen ska ha. Facit är kontrollerat mot
databasen. Kör skriptet före och efter en ändring i sökningen eller i
begreppsregistret och jämför.

Måtten gäller de tio första träffarna:
- träff: andelen frågor med minst en relevant passage,
- MRR: medelvärdet av 1/plats för den första relevanta passagen,
- relevanta: antalet relevanta passager sammanlagt.

Frågorna är få och delvis valda efter fall där sökningen tidigare
misslyckats, så små skillnader säger lite.

Användning:
    python utvardera_sok.py
    python utvardera_sok.py --metod fts
"""

import argparse
import re

import db
import sok

# (fråga, texttyper, regex, id-prefix eller None)
FRAGOR: list[tuple[str, str, str, tuple[str, ...] | None]] = [
    # Berättande källor; originaltexterna söks med
    ("danerna under kung Chlochilaicus anfaller Gallien", "alla", r".",
     ("historia_francorum:iii:3", "liber_historiae_francorum:text:19")),
    ("hednatemplet i Uppsala med gudabilder", "alla", r".",
     ("adam_av_bremen:iv:26", "adam_av_bremen:iv:27", "adam_av_bremen:iv:28")),
    ("Ansgar predikar i Birka", "alla", r"Bir[ck]", ("adam_av_bremen:i:", "vita_anskarii:")),
    ("svionerna är mäktiga genom sina flottor", "alla", r".", ("germania:44:",)),
    ("Ragnar Lodbrok dödas i en ormgrop", "alla",
     r"(Ragnar|Regner|Ragner|Regnerus).{0,4000}(orm|slange|snog|serpent|anguis)", None),
    ("Ingvars färd mot Serkland", "alla", r"Serkland|Särkland", None),
    ("han dog i Grekland", "alla", r"Greece|Grekland|Grikkland|Grikk", ("runa:",)),
    ("Hygelac dödas i Frisland", "alla", r"historia_francorum|liber_historiae|Fris|Fres",
     ("historia_francorum:iii:3", "liber_historiae_francorum:text:19", "beowulf:")),
    ("Harald Blåtand gör danerna kristna", "alla",
     r"(Bl[aåá]t[ao]nd|Gormsson|Gormssonr|Blaatand).{0,3000}(krist|christ)"
     r"|(krist|christ).{0,3000}(Bl[aåá]t[ao]nd|Gormsson|Blaatand)", None),
    ("Rolf Krake strör guld på Fyrisvallarna", "alla",
     r"Fyris.{0,1500}(gull|guld|gold)|(gull|guld|gold).{0,1500}Fyris", None),
    ("slaget vid Bråvalla", "alla",
     r"Bråvall|Brávell|Bravall|Brawel|Braavold|Braavalla|Brovold|Brávalla|Brauell|Bråvold", None),
    ("Ansgar besöker kung Björn", "alla",
     r"(Ansgar|Anskar|Anscar)\w*.{0,2000}(Bern|Björn|Biorn)|(Bern|Björn|Biorn)\w*.{0,2000}(Ansgar|Anskar|Anscar)", None),
    ("Adils och Ale strider på isen", "alla",
     r"(Adil|Aðil|Athisl|Adils|Aðils).{0,2000}(Ale|Áli|Ali)\b|(Ale|Áli)\b.{0,2000}(Adil|Aðil)", None),
    ("Jordanes beskriver ön Scandza och folken där", "alla", r"Scandz|Scanz", ("jordanes_getica:",)),
    ("Plinius om ön Scatinavia", "alla", r".", ("plinius:4.13:", "plinius:8.15:", "mela:3.44-46:")),
    ("Tor fiskar upp Midgårdsormen", "alla",
     r"(Midgårdsorm|Miðgarðsorm|Jǫrmungand|Jörmungand|Midgaards|Midgårds).{0,2000}(fisk|fiska|agn|krok|öngel)"
     r"|(Hymi|Hymer|Hymir).{0,3000}(orm|ormr)", None),
    ("Ibn Fadlan beskriver begravningen av en rusisk hövding med skepp", "alla", r".", ("ibn_fadlan:",)),
    ("Starkad dräper kung Ole", "alla",
     r"(Starka[dt]|Starkather|Starcather|Starkodder|Stærkodder).{0,3000}\b(Ole|Olo|Olonem|Olonis)\b", None),
    ("gutarna ska betala sextio mark i skatt till sveakungen", "alla", r".", ("gutasagan:2:",)),
    ("kung Olof i Sverige låter döpa sig", "alla", r"(Olaph|Olof|Óláf|Olaf)\w*.{0,600}(baptiz|döp|skír|døb)", None),
    ("sändebuden från Rhos visade sig vara svear", "alla", r"Rhos|Sueon", ("annales_bertiniani:",)),
    ("Harald Blåtand döps sedan prästen Poppo burit glödande järn", "alla", r"Poppo", None),
    ("offren i Lejre vart nionde år", "alla", r"Lederun|Lejre|Hleiðr", None),
    ("svenskarna landstiger i Estland och slås vid Lihula", "alla", r"Suec|Swec|Lealensis|Leal", ("henrik_av_lettland:",)),
    ("Hervor hämtar svärdet Tyrfing ur graven", "alla", r"Tyrfing", ("saga_hervarar_saga:",)),
    ("Njål och hans söner bränns inne", "alla", r"Nj[aá]l|Nial|Njal", ("saga_njals_saga:",)),
    ("hertigarna Erik och Valdemar fängslas i Nyköping", "alla", r"nyköping|nyky?ö?pung|nykø", ("erikskronikan:",)),
    # Medeltidsbreven; standardsökningen bland regester och översättningar
    ("kungen befriar ett kloster från skatt", "moderna",
     r"kloster.{0,300}(skatt|fri|befri)|(skatt|befri).{0,300}kloster", None),
    ("brev om gränsen mellan två byar", "moderna", r"\brå|gräns|rågång|skillnad", None),
    ("testamente till kyrkan för själamässor", "moderna",
     r"testament.{0,400}(själ|mässa|kyrka)|(själ|mässa).{0,400}testament", None),
    ("drottning Margareta köper slott", "moderna", r"Margareta.{0,400}(köp|slott)|(köp|slott).{0,400}Margareta", None),
    ("lagman i Uppland", "moderna", r"lagman.{0,200}Uppland|Uppland.{0,200}lagman", None),
    ("bönderna ska betala ledungsskatt", "moderna", r"ledung", None),
    ("påven bekräftar klostrets privilegier", "moderna", r"påve.{0,400}privileg|privileg.{0,400}påve", None),
    ("änka skänker jord för sin mans själ", "moderna", r"(änka|hustru).{0,400}själ|själ.{0,400}(änka|hustru)", None),
    ("biskopen i Linköping inviger en kyrka", "moderna",
     r"Linköping.{0,300}(vig|invig)|(vig|invig).{0,300}Linköping", None),
    ("fogden på Stockholms slott", "moderna", r"fogde.{0,200}Stockholm|Stockholm.{0,200}fogde", None),
]

# Lagarna: relevanta är lagpassager (original eller översättning) som handlar om
# saken. Frågorna ställs både i standardsökningen och med originaltexterna.
LAGFRAGOR = [
    ("vad ska den böta som dräper en präst",
     r"(präst|prest|præst|prästen).{0,500}(dräp|drap|dræp|dræpar|draper)|(dräp|drap|dræp).{0,500}(präst|prest|præst)"),
    ("arv mellan bröder och systrar", r"(arv|arf|ærf).{0,400}(syster|systir|systur|systrar)|(syster|systir|systur).{0,400}(arv|arf|ærf)"),
    ("brott mot kungens edsöre", r"edsöre|eþsöre|eþsøre|eþsörisbrot|edsöresbrott|eþsöris"),
    ("rätt att bygga en kvarn i ån", r"kvarn|qværn|kvärn|quærn|qvarn|kuærn|quarn"),
    ("hur många män ett skeppslag ska ställa till ledungen", r"leþung|ledung|leding|leþang|skiplagh|skeppslag"),
    ("tionde som bönderna ska ge till kyrkan", r"tiond|tiund|tionde"),
    ("hustruns morgongåva", r"morgongåva|morghongæf|morghongaf|morgongiæf|morghon gæf|morghungæf|morgongåvan"),
    ("hemsökn, att anfalla en man i hans hem", r"hemsökn|hemsokn|hemfrid|hemsoknar|hemsøkn|hemsöknar"),
]
FRAGOR += [(f, t, rx, ("lag:",)) for f, rx in LAGFRAGOR for t in ("moderna", "alla")]

ANTAL = 10


def relevant(regex: str, prefix: tuple[str, ...] | None, passage_id: str, text: str) -> bool:
    if prefix and not passage_id.startswith(prefix):
        return False
    return bool(re.search(regex, passage_id + " " + text, re.I | re.S))


def main() -> None:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--metod", default="hybrid", choices=("hybrid", "fts", "vektor"))
    arg = tolk.parse_args()

    p, ph = db._prefix(), db._ph()
    resultat = {}
    for fraga, texttyper, regex, prefix in FRAGOR:
        ids = [t["passage_id"] for t in sok.sok(fraga, arg.metod, ANTAL, texttyper=texttyper)["traffar"]]
        conn = db._hamta_db()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT id, text FROM {p}passage WHERE id IN ({', '.join([ph] * len(ids))})", ids)
            texter = dict(cur.fetchall())
        finally:
            conn.close()
        platser = [i for i, pid in enumerate(ids, 1) if relevant(regex, prefix, pid, texter.get(pid, ""))]
        resultat[(fraga, texttyper)] = platser

    lag = {f for f, _ in LAGFRAGOR}
    for namn, villkor in (("berättande källor, texttyper=alla", lambda f, t: t == "alla" and f not in lag),
                          ("breven, texttyper=moderna", lambda f, t: t == "moderna" and f not in lag),
                          ("lagarna, texttyper=moderna", lambda f, t: t == "moderna" and f in lag),
                          ("lagarna, texttyper=alla", lambda f, t: t == "alla" and f in lag)):
        rader = [(f, pl) for (f, t), pl in resultat.items() if villkor(f, t)]
        traff = sum(1 for _, pl in rader if pl)
        mrr = sum(1 / pl[0] for _, pl in rader if pl) / len(rader)
        print(f"{namn}: träff {traff}/{len(rader)}, MRR {mrr:.3f}, "
              f"relevanta {sum(len(pl) for _, pl in rader)}")
    print()
    for (fraga, texttyper), platser in resultat.items():
        print(f"  {fraga[:55]:55} {texttyper:8} {platser[0] if platser else '-':>3}  ({len(platser)} relevanta)")


if __name__ == "__main__":
    main()

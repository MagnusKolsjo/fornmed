"""
Bygger begreppsregistret: medeltida samhälls-, rätts- och
förvaltningsbegrepp med termformer från Schlyter och Söderwall.

Varje begrepp blir en entitet av typen 'begrepp' med en kort definition på
modern svenska. Termerna hämtas på tre sätt:
- huvudterm, synonymer och motsvarigheter på latin och fornvästnordiska
  anges här,
- uppslagsformerna i ordböckerna kopplas via angivna lemman,
- stavningsvarianter ur ordböckernas formfält tas med när de liknar lemmat.

Definitionerna och de manuellt angivna termerna är ett utkast och
registreras som ogranskade. Ordböckernas egna definitioner nås via
term.artikel_id.

Användning:
    python begreppsregister.py
    python begreppsregister.py --kandidater 50   # termförslag ur SDHK:s regester
"""

import argparse
import collections
import json
import logging
import re

import db
from normalisering import ordform

log = logging.getLogger("begreppsregister")

REGISTRERAD_AV = "begreppsregister.py (utkast)"

# Ordböckerna i den ordning deras definitioner föredras: Schlyter först,
# eftersom Söderwall för lagspråkets ord bara hänvisar dit ("L.")
ORDBOCKER = ("schlyter", "soderwall", "soderwall_supp")

# (id, huvudterm, definition, [ordbokslemman], [(term, språk, termtyp)])
# Språk: swe modern svenska, fsv fornsvenska, lat latin, non fornvästnordiska.
BEGREPP: list[tuple[str, str, str, list[str], list[tuple[str, str, str]]]] = [
    # Indelning
    ("landskap", "landskap", "Ett av de äldre lagområdena (land) med eget ting och egen lag.",
     ["land"], [("land", "swe", "synonym"), ("provincia", "lat", "oversattning")]),
    ("harad", "härad", "Indelning av ett landskap med eget ting, främst i Götaland; motsvaras i Svealand av hundare.",
     ["hæraþ", "häraþ", "häradh"], [("territorium", "lat", "oversattning")]),
    ("hundare", "hundare", "Indelning i Uppland, Södermanland, Västmanland och på Gotland som motsvarar häradet i andra landskap.",
     ["hundari", "hundare"], []),
    ("fjarding", "fjärding", "Fjärdedel; som indelning en fjärdedel av ett större område, t.ex. ett hundare.",
     ["fiärþunger", "fiärdhunger"], []),
    ("skeppslag", "skeppslag", "Indelning i Svealand för uttaget av skepp och manskap till ledungen.",
     ["skiplagh", "skipalagh"], []),
    ("socken", "socken", "Kyrklig församling och det område som hörde till en sockenkyrka.",
     ["sokn"], [("parochia", "lat", "oversattning")]),
    ("lagsaga", "lagsaga", "En lagmans domsområde.",
     ["laghsagha"], []),
    ("by", "by", "Samling gårdar med gemensam inägo- och utmark.",
     ["by", "byr"], [("villa", "lat", "oversattning")]),
    ("allmanning", "allmänning", "Mark som ägs eller brukas gemensamt av en by, ett härad eller ett land.",
     ["almænninger", "almänninger", "almänninge"], []),
    ("utjord", "utjord", "Jord som ligger utanför byns ägor eller brukas från en annan gård.",
     ["utiorþ", "utiordh"], []),
    ("stad", "stad", "Köpstad med egen rätt (stadslag) och eget styre av borgmästare och råd.",
     ["staþer", "stadher"], [("civitas", "lat", "oversattning")]),
    ("rike", "rike", "Konungariket som politisk enhet.",
     ["rike"], [("regnum", "lat", "oversattning")]),

    # Ting och rättsskipning
    ("ting", "ting", "Sammankomst för en bygd där mål avgjordes och gemensamma angelägenheter behandlades.",
     ["þing"], [("placitum", "lat", "oversattning")]),
    ("landsting", "landsting", "Ting för ett helt landskap, lett av lagmannen.",
     ["landsþing"], []),
    ("haradsting", "häradsting", "Ting för ett härad.",
     ["hæraþsþing"], []),
    ("namnd", "nämnd", "Grupp edsvurna män som inför tinget avgjorde eller intygade sakförhållanden i ett mål.",
     ["næmd", "nämd"], []),
    ("vittne", "vittne", "Person som intygar en rättshandling eller ett sakförhållande.",
     ["vitni", "vitne"], [("testis", "lat", "oversattning")]),
    ("domare", "domare", "Den som dömer i ett mål.",
     ["domari", "domare"], [("iudex", "lat", "oversattning")]),
    ("boter", "böter", "Penningersättning eller straffavgift för brott.",
     ["bot"], [("bot", "swe", "synonym")]),
    ("mansbot", "mansbot", "Böter för dråp, betalda till den dödades släkt.",
     ["mansbot"], []),
    ("vite", "vite", "Straffavgift, ofta förelagd för att tvinga fram en handling.",
     ["viti", "vite"], []),
    ("edsore", "edsöre", "Den av kungen och stormännen edsvurna friden för hem, kyrka, ting och kvinnor; brott mot den straffades särskilt hårt.",
     ["eþsöre"], [("edsöresbrott", "swe", "synonym")]),

    # Brott
    ("drap", "dråp", "Uppsåtligt dödande av en människa.",
     ["drap", "dræpari"], [("mandråp", "swe", "synonym"), ("homicidium", "lat", "oversattning")]),
    ("vadadrap", "vådadråp", "Dödande av en människa av våda, utan uppsåt.",
     ["vaþi", "vaþa"], [("vådaverk", "swe", "synonym")]),
    ("hemsokn", "hemsökn", "Angrepp på någon i hans eget hem; räknades till de grövsta fridsbrotten.",
     ["hemsokn"], []),
    ("valdtakt", "våldtäkt", "Tvångsmässigt samlag eller bortförande av en kvinna; brott mot kvinnofriden.",
     ["valdtäkt"], [("kvinnofridsbrott", "swe", "synonym")]),
    ("ran", "rån", "Öppet tillgrepp av annans egendom med våld.",
     ["ran"], [("rapina", "lat", "oversattning")]),
    ("stold", "stöld", "Hemligt tillgrepp av annans egendom.",
     ["þiufnaþer"], [("tjuvnad", "swe", "synonym"), ("furtum", "lat", "oversattning")]),
    ("mordbrand", "mordbrand", "Uppsåtlig brand i annans hus.",
     ["mordbrander"], []),
    ("sar", "sår", "Kroppsskada genom våld; böterna varierade med skadans art.",
     ["sar"], [("åverkan", "swe", "synonym")]),
    ("arekrankning", "ärekränkning", "Smädelse eller nid som angriper någons heder.",
     ["niþ"], [("okvädinsord", "swe", "synonym"), ("oqvæþinsorþ", "fsv", "historisk_form")]),
    ("nidingsverk", "nidingsverk", "Brott som ansågs så nedrigt att det inte kunde sonas med böter.",
     ["niþingsværk"], []),
    ("trolldom", "trolldom", "Skadlig magi.",
     ["troldomber", "trulldomber"], []),
    ("hor", "hor", "Äktenskapsbrott.",
     ["hor"], [("adulterium", "lat", "oversattning")]),

    # Påföljder
    ("fredloshet", "fredlöshet", "Förlust av lagens skydd; den fredlöse fick dödas ostraffat.",
     ["friþlös", "biltugher"], [("fredlös", "swe", "synonym"), ("biltog", "swe", "synonym")]),
    ("dodsstraff", "dödsstraff", "Straff till livet, t.ex. hängning, halshuggning eller stegling.",
     ["hængia"], []),
    ("landsflykt", "landsflykt", "Skyldighet att lämna landet; förlust av rätten att vistas där.",
     ["landsvist"], [("landsförvisning", "swe", "synonym")]),
    ("attebot", "ättebot", "Den del av mansboten som tillföll den dödades släkt utöver arvingarna.",
     ["ættarbot"], []),
    ("sakore", "saköre", "Böter till målsäganden, kungen eller häradet för ett brott; i lagarna ofta delade i tre lotter.",
     ["saköre"], [("sakören", "swe", "synonym")]),
    ("ogild", "ogild", "Utan rätt till böter: den som dödas ogild har ingen mansbot.",
     ["ogilder"], [("ogilder", "fsv", "historisk_form")]),
    ("manhelgd", "manhelgd", "Människans rättsliga frid och okränkbarhet; manhelgdsbalken reglerade brott mot den.",
     ["manhælghi"], []),

    # Process och rättskipning
    ("malsagande", "målsägande", "Den som har rätt att föra talan om ett brott, oftast den skadade eller den dödades arvinge.",
     ["malsæghandi"], []),
    ("ed", "ed", "Högtidlig försäkran inför Gud; i processen medlet att fria sig eller fälla någon.",
     ["eþer", "eþsorþ"], [("iuramentum", "lat", "oversattning")]),
    ("edgard", "edgärd", "Ed som avläggs av flera edgärdsmän som stöder parten.",
     [], [("edgärdsmän", "swe", "synonym"), ("eþa mæn", "fsv", "historisk_form")]),
    ("tylftered", "tylftered", "Ed av tolv män.",
     ["tylft"], [("tylft", "swe", "synonym")]),
    ("syn", "syn", "Besiktning genom utsedda män av en skada, ett gränsmärke eller en brottsplats.",
     ["syn"], []),
    ("tvekamp", "tvekamp", "Rättslig strid mellan två parter som avgör en tvist om heder.",
     [], [("holmgång", "swe", "synonym")]),
    ("eriksgata", "eriksgata", "Den nyvalde kungens färd genom landskapen för att erkännas och svära att hålla lagen.",
     ["eriksgata"], []),
    ("konungaval", "konungaval", "Valet av kung, i Svealand enligt lagarna vid Mora äng.",
     [], [("kungaval", "swe", "synonym")]),

    # Rättssäkerhet: jäv, oväld och mutor
    ("jav", "jäv", "Omständighet som gör att någon inte får vara domare, nämndeman eller vittne i en sak.",
     ["iäva", "iäf"], []),
    ("ovald", "oväld", "Opartiskhet; att döma eller vittna utan vild, alltså utan att gynna någon part.",
     ["vild", "vilder"], [("opartiskhet", "swe", "synonym"), ("vtan vild", "fsv", "historisk_form")]),
    ("frandskap", "frändskap", "Släktskap genom härstamning; grund för arv, mansbot och jäv.",
     ["skyldskaper", "frændsimi"], [("skyldskap", "swe", "synonym")]),
    ("svagerskap", "svågerskap", "Släktskap genom gifte.",
     ["mägdh"], [("mågskap", "swe", "synonym")]),
    ("muta", "muta", "Gåva för att påverka en dom eller ett vittnesmål.",
     ["muta"], []),

    # Brottsformer och delaktighet
    ("dulgadrap", "dulgadråp", "Dråp där gärningsmannen är okänd eller döljs; ansvaret kunde läggas på bygden eller häradet.",
     ["dulghadrap"], []),
    ("forsat", "försåt", "Bakhåll; dråp eller angrepp ur försåt räknades som särskilt grovt.",
     ["forsat"], []),
    ("radsbane", "rådsbane", "Den som rådde till eller planerade ett dråp utan att själv utföra det.",
     ["raþsbani"], []),
    ("hallbane", "hållbane", "Den som höll fast offret vid ett dråp.",
     [], [("hallbani", "fsv", "historisk_form"), ("haldsbani", "fsv", "historisk_form")]),
    ("asyna_man", "åsyna man", "Den som var närvarande vid ett dråp med ond vilja.",
     [], [("atvistarmaþer", "fsv", "historisk_form")]),
    ("fridsbrott", "fridsbrott", "Brott mot en lagstadgad frid, t.ex. kyrko-, tings-, hem- eller kvinnofrid.",
     ["friþbrut"], []),
    ("orbotamal", "orbotamål", "Brott som inte kan sonas med böter.",
     [], [("orbotæ mal", "fsv", "historisk_form")]),

    # Bötesformer och förverkande
    ("forverkat_gods", "förverkat gods", "Egendom som den dömde förlorar, ofta delad mellan målsäganden, kungen och häradet.",
     [], [("förverkad egendom", "swe", "synonym")]),
    ("tvebot", "tvebot", "Dubbel bot, för grövre fall av ett brott.",
     ["tväböte"], [("tvåböte", "swe", "synonym")]),
    ("trebot", "trebot", "Trefaldig bot.",
     [], [("þrebote", "fsv", "historisk_form")]),
    ("mordgald", "mordgäld", "Böter för mord, det vill säga hemligt dråp.",
     ["morþgæld"], []),
    ("sporgald", "spårgäld", "Böter som tillföll den dödades arvinge när dråparen spårats men inte gripits.",
     ["sporgæld"], []),
    ("tockabot", "tockabot", "Böter som tillföll den dräptes herre eller beskyddare.",
     ["þokke"], [("tack", "swe", "synonym")]),

    # Process
    ("sagnarting", "sägnarting", "Det ting där fredlöshet förkunnades.",
     ["sægnarþing"], []),
    ("kungsnamnd", "kungsnämnd", "Den nämnd av tolv män i varje lagsaga som dömde i brott mot kungens fridslagar.",
     ["kunungs næmd"], []),
    ("rafst", "räfst", "Undersökning och bestraffning av brott, särskilt kungens räfsteting.",
     ["ræfst"], [("räfsteting", "swe", "synonym")]),
    ("jarnbord", "järnbörd", "Gudsdom genom att bära glödgat järn.",
     [], [("iarnbyrdh", "fsv", "historisk_form")]),
    ("trygd", "trygd", "Edlig försäkran om fred mellan parter efter förlikning.",
     ["trygd", "trygþ"], []),
    ("fridsbon", "fridsbön", "Begäran om frid för den som dräpt, för att få bjuda böter.",
     ["friþbön"], []),
    ("borgesman", "borgesman", "Den som går i borgen för en annans betalning eller inställelse.",
     ["taki"], []),

    # Mottagare och grupper
    ("kyrka", "kyrka", "Kyrkan som rättssubjekt, mottagare av böter och gods.",
     ["kirkia", "kyrkia"], []),
    ("hustru", "hustru", "Gift kvinna; i bötes- och godsdelningar mottagare av en egen lott.",
     ["hustru", "husfru"], []),
    ("losker_man", "lösker man", "Person utan fast bostad; behandlades i lagarna strängare som vittne och gärningsman.",
     ["lösker"], []),
    ("fiendskap", "fiendskap", "Ovänskap mellan personer; grund för jäv.",
     ["ovinskaper", "fiandskaper"], [("ovänskap", "swe", "synonym")]),

    # Ämbeten och makt
    ("kung", "kung", "Rikets härskare.",
     ["konunger", "kununger"], [("konung", "swe", "synonym"), ("rex", "lat", "oversattning")]),
    ("jarl", "jarl", "Kungens främste man och ledare för ledungen; ämbetet försvann i Sverige efter Birger jarl.",
     ["iarl"], [("dux", "lat", "oversattning")]),
    ("drots", "drots", "Rikets främste världslige ämbetsman.",
     [], [("drotsete", "fsv", "historisk_form"), ("dapifer", "lat", "oversattning")]),
    ("marsk", "marsk", "Rikets högste militäre ämbetsman.",
     ["marskalker"], [("marskalk", "swe", "synonym"), ("marscalcus", "lat", "oversattning")]),
    ("lagman", "lagman", "Den som ledde landstinget och tolkade lagen inom en lagsaga.",
     ["laghman", "laghmaþer"], [("legifer", "lat", "oversattning")]),
    ("haradshovding", "häradshövding", "Ledare för häradstinget.",
     [], [("häradshöfdhinge", "fsv", "historisk_form")]),
    ("fogde", "fogde", "Förvaltare för kungen eller en annan herre med ansvar för uppbörd, ordning och rättsskipning inom ett område.",
     ["foghati", "foghate"], [("advocatus", "lat", "oversattning")]),
    ("lansman", "länsman", "Kungens ombudsman i ett mindre område.",
     ["lænsmaþer"], []),
    ("bryte", "bryte", "Förvaltare av en gård åt ägaren.",
     ["bryti"], [("villicus", "lat", "oversattning")]),

    # Stånd och samhällsgrupper
    ("bonde", "bonde", "Fri jordbrukare och husbonde; i lagarna den rättsliga huvudpersonen.",
     ["bonde"], [("rusticus", "lat", "oversattning")]),
    ("landbo", "landbo", "Bonde som brukar jord som ägs av någon annan mot årlig avgift (landgille).",
     ["landboe"], [("colonus", "lat", "oversattning")]),
    ("tral", "träl", "Ofri person som ägdes av en annan.",
     ["þræl", "thräl", "þräl"], [("servus", "lat", "oversattning")]),
    ("fralse", "frälse", "Frihet från skatt mot tjänst åt kungen eller kyrkan; även de grupper som hade den friheten.",
     ["fræls", "frælsi", "fräls", "frälse"], [("libertas", "lat", "oversattning")]),
    ("borgare", "borgare", "Stadsbo med burskap och del i stadens rätt.",
     ["borghare"], [("burgensis", "lat", "oversattning")]),
    ("att", "ätt", "Släkt; grupp med gemensam härstamning.",
     ["æt", "ætt", "æth", "ät"], []),

    # Skatter och avgifter
    ("ledung", "ledung", "Skyldighet att delta i eller bekosta kungens sjöburna krigsuppbåd; blev under medeltiden en fast skatt.",
     ["leþunger", "ledhunger"],
     [("leding", "swe", "synonym"), ("laiþingr", "fsv", "historisk_form"),
      ("leiðangr", "non", "oversattning"), ("expeditio", "lat", "oversattning")]),
    ("husaby", "husaby", "Kungsgård där kungens länsman eller en annan tjänsteman bodde.",
     ["husaby"], []),
    ("gastning", "gästning", "Skyldighet att ta emot och underhålla kungen och hans följe; blev senare en avgift.",
     ["gæstning", "gästning"], []),
    ("skatt", "skatt", "Pålaga till kungen eller riket.",
     ["skatter", "skat"], [("tributum", "lat", "oversattning")]),
    ("tionde", "tionde", "Avgift till kyrkan av en tiondel av årets avkastning.",
     ["tiund", "tionde"], [("decima", "lat", "oversattning")]),

    # Kyrkan
    ("biskop", "biskop", "Föreståndare för ett stift.",
     ["biskuper"], [("episcopus", "lat", "oversattning")]),
    ("kanik", "kanik", "Medlem av ett domkapitel.",
     ["kanunker"], [("canonicus", "lat", "oversattning")]),
    ("prast", "präst", "Prästvigd man, särskilt sockenpräst.",
     ["præster", "präster", "prester"], [("sacerdos", "lat", "oversattning"), ("presbiter", "lat", "oversattning")]),
    ("kloster", "kloster", "Gemenskap av munkar eller nunnor och deras byggnader.",
     ["kloster"], [("monasterium", "lat", "oversattning"), ("claustrum", "lat", "oversattning")]),
    ("avlat", "avlat", "Efterskänkning av kyrkligt straff för synd, ofta mot fromt verk eller gåva.",
     ["aflat"], [("indulgentia", "lat", "oversattning")]),

    # Egendom och familjerätt
    ("arv", "arv", "Egendom som går i arv; rätten att ärva.",
     ["arf", "arver"], [("hereditas", "lat", "oversattning")]),
    ("arvinge", "arvinge", "Den som ärver; i lagarna ofta den dödades arvingar som tar emot mansboten.",
     ["arvi", "arfwi", "arvingi"], [("heres", "lat", "oversattning")]),
    ("morgongava", "morgongåva", "Gåva från mannen till hustrun efter bröllopet.",
     ["morghongava", "morghongæf"], []),
    ("skotning", "skötning", "Rättslig överlåtelse av jord genom en symbolisk handling.",
     ["skötning"], []),
    ("pant", "pant", "Egendom som ställs som säkerhet för en skuld.",
     ["pant"], [("pignus", "lat", "oversattning")]),
    ("sigill", "sigill", "Stämpel vars avtryck bestyrker ett brev.",
     ["insighli", "insighle"], [("sigillum", "lat", "oversattning")]),
    ("jord", "jord", "Mark och jordegendom; i breven ofta den jord som överlåts, pantsätts eller testamenteras.",
     ["iorþ", "jorþ", "iordh"], [("terra", "lat", "oversattning")]),
    ("gods", "gods", "Egendom, särskilt jordegendom med gårdar.",
     ["goþs", "gods"], [("bona", "lat", "oversattning")]),
    ("agodel", "ägodel", "Jordstycke eller andel i en ägovidd som hör till en gård.",
     ["æghodel"], []),
    ("losore", "lösöre", "Lös egendom, i motsats till jord.",
     ["lösöre"], []),
    ("hemman", "hemman", "Gård med tillhörande jord.",
     ["heman"], []),
    ("torp", "torp", "Mindre bosättning eller gård, ofta upptagen på en bys utmark.",
     ["þorp"], []),
    ("hemgift", "hemgift", "Det en brud fick med sig från sin släkt vid giftermålet.",
     ["hemgift", "hemgæf"], [("dos", "lat", "oversattning")]),
    ("fastar", "fastar", "Gode män som var närvarande vid köp, byte, gåva eller pantsättning av jord och bekräftade rättshandlingen.",
     ["fastar", "fastir"], [("fasteman", "swe", "synonym")]),
    ("samtycke", "samtycke", "Medgivande, särskilt arvingarnas medgivande till att jord säljs eller ges bort.",
     ["samtycke", "samþykke", "samthykke"], [("consensus", "lat", "oversattning")]),
    ("skuld", "skuld", "Gäld; det någon är skyldig en annan.",
     ["schlyter:fsvm--skyld..nn.1", "soderwall_supp:fsvm--skuld..nn.1"], [("gäld", "swe", "synonym")]),

    # Mynt och värdering. Kvoterna följer Schlyter: 1 mark = 8 öre = 24 örtugar.
    ("mark", "mark", "Vikt- och myntenhet om åtta öre; även grund för jordvärdering (markland).",
     ["schlyter:fsvm--mark..nn.2", "soderwall:fsvm--mark..nn.2", "soderwall_supp:fsvm--mark..nn.2"],
     [("marca", "lat", "oversattning")]),
    ("markland", "markland", "Enhet för jordvärdering, indelad i öresland och örtugland.",
     ["markland"], []),
    ("ore", "öre", "Vikt- och myntenhet, en åttondel av en mark.",
     ["öre"], []),
    ("ortug", "örtug", "Vikt- och myntenhet, en tredjedel av ett öre.",
     ["örtogh", "ortogh"], []),
    ("penning", "penning", "Mynt, den minsta myntenheten; i plural ofta om pengar i allmänhet.",
     ["penninger", "pænninger", "pänninger"], [("denarius", "lat", "oversattning")]),
    ("ranta", "ränta", "Årlig avgift eller avkastning av jord, t.ex. landbons avgift till jordägaren.",
     ["rænta", "ränta"], [("redditus", "lat", "oversattning")]),
    ("gengard", "gengärd", "Avgift i natura eller pengar som ersatte skyldigheten att ta emot kungen och hans följe.",
     ["gengærþ", "gengärdh", "gengärþ"], []),

    # Personer och stånd
    ("vapnare", "väpnare", "Frälseman av lägre rang än riddare.",
     ["væpnare", "väpnare"], [("armiger", "lat", "oversattning")]),
    ("klerk", "klerk", "Person i kyrkans tjänst, ofta med lägre vigning; även skrivkunnig ämbetsman.",
     ["klerker", "klærker", "klärker"], [("clericus", "lat", "oversattning")]),
    ("lekman", "lekman", "Person som inte tillhör prästerskapet.",
     ["lekman"], [("laicus", "lat", "oversattning")]),
    ("allmoge", "allmoge", "Den breda befolkningen i en bygd, särskilt bönderna.",
     ["almoghe"], []),
    ("menighet", "menighet", "Gemenskap av invånare, t.ex. en socken- eller tingsmenighet.",
     ["menighet"], []),

    # Rätt och styre
    ("stadga", "stadga", "Förordning eller beslut med bindande verkan, utfärdad av kung, kyrka eller stad.",
     ["staþga", "stadhga"], [("statutum", "lat", "oversattning")]),
    ("landssyn", "landssyn", "Syn och utredning i ett mål, förrättad av en nämnd på landstingets eller lagmannens uppdrag.",
     ["landssyn"], []),
    ("rannsakan", "rannsakan", "Utredning eller förhör i ett rättsärende.",
     ["ransakan", "ransak"], []),
    ("dagtingan", "dagtingan", "Förhandling om villkor, t.ex. vid förlikning eller kapitulation.",
     ["dagtingan", "daghthingan"], []),
    ("mord", "mord", "Hemligt eller förrädiskt dråp, i lagarna skilt från öppet dråp.",
     ["schlyter:fsvm--morþ..nn.1", "soderwall:fsvm--morþ..nn.2"], [("homicidium", "lat", "oversattning")]),
    ("hagn", "hägn", "Beskydd, särskilt kungens beskydd över en person eller institution ('ta i sitt hägn').",
     ["häghn"], [("protectio", "lat", "oversattning")]),
    ("tempel", "tempel", "Hednisk kultbyggnad, som templet i Uppsala hos Adam av Bremen.",
     [], [("templum", "lat", "oversattning")]),
    ("slott", "slott", "Befäst borg, ofta säte för en fogde eller länsherre.",
     ["slott", "slot", "schlyter:fsvm--borgh..nn.1", "soderwall:fsvm--borgh..nn.1",
      "soderwall_supp:fsvm--borgh..nn.2"],
     [("borg", "swe", "synonym"), ("fäste", "swe", "synonym"), ("castrum", "lat", "oversattning")]),
]

# Orter och folk med sina namnformer i källorna, så att en fråga om Uppsala
# också hittar Adams Ubsola. Bara stavningsvarianter av samma namn tas med;
# identifieringar som forskningen diskuterar (Jordanes suehans = svear,
# gēatas = götar) hör till identifieringstabellen med bedömningar.
# Befintliga entiteter från pastaenden_hygelac.py behåller sina namn och beskrivningar.
#
# Latinska former söks på stammen: de två sista tecknen kapas och resten söks
# som prefix (sok._fts_termer). Formen väljs så att stammen inte blir ett
# vanligt ord: Gallias ger Galli*, medan Gallia skulle ge Gall*; Francos ger
# Franc*, medan Franci skulle ge Fran* och träffa svenskans från.
# (id, typ, namn, beskrivning, [(namnform, språk)])
NAMN: list[tuple[str, str, str, str | None, list[tuple[str, str]]]] = [
    ("plats:uppsala", "plats", "Uppsala", "Gamla Uppsala",
     [("Ubsola", "lat"), ("Ubsala", "lat"), ("Upsala", "swe"), ("Uppsalir", "non")]),
    ("plats:sigtuna", "plats", "Sigtuna", "Stad vid Mälaren, anlagd under senare delen av 900-talet.",
     [("Sictona", "lat"), ("Sigtúnir", "non")]),
    ("plats:birka", "plats", "Birka", "Vikingatida handelsplats på Björkö i Mälaren.",
     [("Birca", "lat")]),
    ("plats:gotland", "plats", "Gotland", None, [("Gutland", "fsv"), ("Gotlandia", "lat")]),
    ("plats:skane", "plats", "Skåne", None, [("Sconia", "lat"), ("Scania", "lat"), ("Skáney", "non")]),
    ("plats:danmark", "plats", "Danmark", None, [("Dania", "lat"), ("Danmǫrk", "non")]),
    ("plats:norge", "plats", "Norge", None,
     [("Nortmannia", "lat"), ("Norvegia", "lat"), ("Norwegia", "lat"), ("Noregr", "non")]),
    ("plats:vanern", "plats", "Vänern", None, [("Vænir", "non")]),
    ("plats:nykoping", "plats", "Nyköping", None, [("Nyköpung", "fsv"), ("Nyköpunge", "fsv"), ("Nycopia", "lat")]),
    ("plats:lejre", "plats", "Lejre", "Kungsgård på Själland, enligt Thietmar platsen för offer vart nionde år.",
     [("Lederun", "lat"), ("Hleiðra", "non"), ("Hleiðargarðr", "non")]),
    ("plats:estland", "plats", "Estland", None, [("Estonia", "lat"), ("Eistland", "non"), ("Ehstland", "deu")]),
    ("plats:lihula", "plats", "Lihula", "Borg i västra Estland där svenskarna besegrades 1220.",
     [("Leal", "lat"), ("Lealensis", "lat")]),
    ("grupp:svear", "grupp", "Svear", "Folket i Mälardalen och Uppland, som gett Sverige dess namn.",
     [("Sueones", "lat"), ("Suiones", "lat"), ("Swēon", "ang"), ("Sweon", "ang"), ("Svíar", "non"),
      ("swea", "fsv")]),
    ("grupp:dani", "grupp", "Dani", "Daner enligt Gregorius av Tours",
     [("daner", "swe"), ("Dene", "ang"), ("Danir", "non")]),
    ("grupp:gotar", "grupp", "Götar", "Folk i Väster- och Östergötland",
     [("Gautar", "non"), ("giötæ", "fsv")]),
    ("grupp:gutar", "grupp", "Gutar", "Gotlands invånare", [("Gutar", "fsv")]),
    ("grupp:franker", "grupp", "Franker", None, [("Francos", "lat"), ("Francorum", "lat")]),
    ("plats:bravalla", "plats", "Bråvalla", "Slätten där slaget vid Bråvalla stod enligt sagotraditionen",
     [("Brávellir", "non"), ("bráavallar", "non"), ("Braavalla", "dan"), ("Brawellinis", "lat")]),
    ("plats:fyrisvallarna", "plats", "Fyrisvallarna", "Slätten vid Fyrisån nedanför Uppsala",
     [("Fyrisvall", "swe"), ("Fýrisvellir", "non"), ("Fýrisvalla", "non"), ("Fyrisvöllu", "non"),
      ("Fýrisvöllu", "non")]),
    ("plats:serkland", "plats", "Serkland", "De muslimska länderna i öster i runinskrifter och sagor",
     [("Särkland", "swe")]),
    ("plats:grekland", "plats", "Grekland", "Det bysantinska riket i runinskrifter och sagor",
     [("Grikkland", "non"), ("Greece", "eng")]),
    ("plats:gallien", "plats", "Gallien", None, [("Gallias", "lat"), ("Galliarum", "lat")]),
    ("plats:scandza", "plats", "Scandza", "Ön i norr där goterna har sitt ursprung enligt Jordanes",
     [("Skandza", "swe"), ("Scandzae", "lat")]),
    ("plats:skandinavien", "plats", "Skandinavien", None,
     [("Scatinavia", "lat"), ("Scadinavia", "lat"), ("Scandinavia", "lat")]),
    ("person:chlochilaicus", "person", "Chlochilaicus", "Danernas kung hos Gregorius av Tours",
     [("Chlochilaicus", "lat")]),
    ("person:adils", "person", "Aðils", "Ynglingakung i Ynglingatal och Ynglinga saga",
     [("Adils", "swe"), ("Athislus", "lat")]),
    ("person:ali", "person", "Áli", "Kung som besegras av Aðils i Ynglinga saga", [("Ale", "swe")]),
    ("person:starkad", "person", "Starkad", "Sagohjälte hos Saxo och i de isländska sagorna",
     [("Starkaðr", "non"), ("Starcatherus", "lat"), ("Stærkodder", "dan")]),
    ("person:ragnar_lodbrok", "person", "Ragnar Lodbrok", "Sagokung och vikingahövding",
     [("Ragnarr loðbrók", "non"), ("Regnerus", "lat"), ("Regner Lodbrog", "dan")]),
    ("person:ottar", "person", "Ottar", "Norrman från Hålogaland som berättade om sina resor för kung Alfred",
     [("Ohthere", "ang"), ("Ohtere", "ang")]),
    ("person:alfred", "person", "Alfred den store", "Kung av Wessex 871–899",
     [("Ælfred", "ang"), ("Ælfrede", "ang"), ("Alfredus", "lat")]),
    ("grupp:bjarmer", "grupp", "Bjarmer", "Folk vid Vita havet, i Bjarmaland",
     [("Beormas", "ang"), ("Bjarmar", "non"), ("Biarmi", "lat"), ("Biarmia", "lat")]),
    ("person:ansgar", "person", "Ansgar", "Missionär i Birka på 800-talet, ärkebiskop av Hamburg-Bremen",
     [("Ansgarius", "lat"), ("Anskarius", "lat"), ("Anscarius", "lat")]),
    ("person:rolf_krake", "person", "Rolf Krake", "Sagokung i Lejre",
     [("Hrólfr kraki", "non"), ("Rolf Krage", "dan"), ("Roluo", "lat")]),
]

# Vanliga moderna ord som också råkar vara uppslagsord hos Schlyter; de
# utesluts ur kandidatlistan eftersom de inte är begrepp
FUNKTIONSORD = set("""
till hans hennes deras sina sitt sin sig alla allt över under utan efter från mellan genom
emot inför innan sedan sidan vara varit blir blev hade haft hava göra gjort komma kommit
kunna kunde skall skulle måste vilja ville veta bland full hela halva vissa denna detta
dessa andra annan annat samma även eller samt också icke inte någon något några varje
""".split())

# (från, till, relation); 'bredare' betyder att till är bredare än från
RELATIONER = [
    ("dulgadrap", "drap", "bredare"),
    ("forsat", "drap", "relaterad"),
    ("radsbane", "drap", "relaterad"),
    ("hallbane", "drap", "relaterad"),
    ("asyna_man", "drap", "relaterad"),
    ("orbotamal", "nidingsverk", "relaterad"),
    ("forverkat_gods", "edsore", "relaterad"),
    ("tvebot", "boter", "bredare"),
    ("trebot", "boter", "bredare"),
    ("mordgald", "mord", "relaterad"),
    ("sporgald", "mansbot", "relaterad"),
    ("tockabot", "boter", "bredare"),
    ("sagnarting", "ting", "bredare"),
    ("kungsnamnd", "namnd", "bredare"),
    ("fiendskap", "jav", "relaterad"),
    ("trygd", "ed", "relaterad"),
    ("drap", "mansbot", "relaterad"),
    ("vadadrap", "drap", "relaterad"),
    ("drap", "manhelgd", "relaterad"),
    ("hemsokn", "edsore", "relaterad"),
    ("valdtakt", "edsore", "relaterad"),
    ("attebot", "mansbot", "bredare"),
    ("sakore", "boter", "bredare"),
    ("ogild", "mansbot", "relaterad"),
    ("fredloshet", "edsore", "relaterad"),
    ("tylftered", "edgard", "bredare"),
    ("edgard", "ed", "bredare"),
    ("tvekamp", "arekrankning", "relaterad"),
    ("jav", "ovald", "relaterad"),
    ("jav", "frandskap", "relaterad"),
    ("jav", "svagerskap", "relaterad"),
    ("jav", "namnd", "relaterad"),
    ("muta", "ovald", "relaterad"),
    ("eriksgata", "konungaval", "relaterad"),
    ("harad", "landskap", "bredare"),
    ("hundare", "landskap", "bredare"),
    ("hundare", "harad", "relaterad"),
    ("fjarding", "hundare", "bredare"),
    ("skeppslag", "hundare", "relaterad"),
    ("skeppslag", "ledung", "relaterad"),
    ("lagsaga", "landskap", "relaterad"),
    ("landsting", "ting", "bredare"),
    ("haradsting", "ting", "bredare"),
    ("haradsting", "harad", "relaterad"),
    ("landsting", "lagman", "relaterad"),
    ("lagman", "lagsaga", "relaterad"),
    ("haradshovding", "haradsting", "relaterad"),
    ("namnd", "ting", "relaterad"),
    ("mansbot", "boter", "bredare"),
    ("vite", "boter", "relaterad"),
    ("edsore", "boter", "relaterad"),
    ("husaby", "ledung", "relaterad"),
    ("husaby", "lansman", "relaterad"),
    ("fogde", "lansman", "relaterad"),
    ("ledung", "skatt", "relaterad"),
    ("gastning", "skatt", "relaterad"),
    ("fralse", "skatt", "relaterad"),
    ("landbo", "bonde", "bredare"),
    ("tionde", "prast", "relaterad"),
    ("kanik", "biskop", "relaterad"),
    ("morgongava", "arv", "relaterad"),
    ("gods", "jord", "relaterad"),
    ("agodel", "by", "relaterad"),
    ("hemman", "by", "relaterad"),
    ("torp", "by", "relaterad"),
    ("losore", "arv", "relaterad"),
    ("hemgift", "morgongava", "relaterad"),
    ("fastar", "skotning", "relaterad"),
    ("samtycke", "arv", "relaterad"),
    ("skuld", "pant", "relaterad"),
    ("ore", "mark", "relaterad"),
    ("ortug", "ore", "relaterad"),
    ("penning", "mark", "relaterad"),
    ("markland", "mark", "relaterad"),
    ("ranta", "landbo", "relaterad"),
    ("gengard", "gastning", "relaterad"),
    ("gengard", "skatt", "relaterad"),
    ("vapnare", "fralse", "relaterad"),
    ("klerk", "prast", "relaterad"),
    ("lekman", "prast", "relaterad"),
    ("allmoge", "bonde", "relaterad"),
    ("menighet", "socken", "relaterad"),
    ("landssyn", "namnd", "relaterad"),
    ("rannsakan", "ting", "relaterad"),
    ("mord", "mansbot", "relaterad"),
    ("hagn", "kung", "relaterad"),
    ("slott", "fogde", "relaterad"),
]


def _liknar(form: str, lemma: str) -> bool:
    """
    True om en variant ur ordbokens formfält sannolikt är samma ord som
    lemmat: samma början (e och ä likvärdiga) och ungefär samma längd.
    Längdgränsen sållar bort sammansättningar (landzby) och för korta ord
    som skulle matcha för brett (lag under laghman); versaler inne i ordet
    är sigler som hängt med (häradzSD).
    """
    if any(t.isupper() for t in form):
        return False
    a, b = ordform(form).replace("ä", "e"), ordform(lemma).replace("ä", "e")
    tillagg = 2 if len(lemma) <= 4 else 3
    # Korta lemman får inga kortare former: skul under skuld är också 'skall'
    minsta = len(lemma) - 2 if len(lemma) > 6 else len(lemma)
    return a[:3] == b[:3] and minsta <= len(form) <= len(lemma) + tillagg


def _artiklar(cur, lemman: list[str]) -> list[tuple]:
    """
    Ordboksartiklar (betydelse 1) för angivna lemman.

    Ett lemma anges antingen som uppslagsord ('hæraþ') eller, när ordet har
    homografer med olika betydelse, som 'ordbok:lemgram'
    ('schlyter:fsvm--mark..nn.2' för viktenheten, inte skogen eller märket).
    Numreringen av homografer skiljer sig mellan ordböckerna, så den exakta
    formen anges per ordbok.
    """
    if not lemman:
        return []
    p, ph = db._prefix(), db._ph()
    exakta = [tuple(l.split(":", 1)) for l in lemman if ":" in l]
    ord_ = [l for l in lemman if ":" not in l]
    rader = []
    if ord_:
        cur.execute(
            f"""
            SELECT id, kallsamling_id, lemma, ordklass, former, lemgram
            FROM {p}ordboksartikel
            WHERE lemma IN ({', '.join([ph] * len(ord_))}) AND betydelse_nr = 1
            """,
            ord_,
        )
        traffar = cur.fetchall()
        # Om lemmat finns som substantiv tas bara substantivet, så att
        # räkneordet 'tionde' inte kopplas till kyrkoavgiften
        substantiv = {(r[1], r[2]) for r in traffar if r[3] == "nn"}
        rader += [r for r in traffar if r[3] == "nn" or (r[1], r[2]) not in substantiv]
    for kalla, lemgram in exakta:
        cur.execute(
            f"""
            SELECT id, kallsamling_id, lemma, ordklass, former, lemgram
            FROM {p}ordboksartikel
            WHERE kallsamling_id = {ph} AND lemgram = {ph} AND betydelse_nr = 1
            """,
            (kalla, lemgram),
        )
        rader += cur.fetchall()
    return rader


def bygg() -> None:
    db.initiera_schema()
    p = db._prefix()
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        entiteter, termer = [], {}

        def lagg_till(begrepp_id, term, sprak, termtyp, artikel_id=None):
            nyckel = (begrepp_id, ordform(term), sprak)
            # Första förekomsten vinner, så att huvudtermen och de angivna
            # termerna inte skrivs över av en ordboksform med samma sökform
            if nyckel not in termer:
                termer[nyckel] = (f"{begrepp_id}:{sprak}:{term}", begrepp_id, term, sprak, termtyp,
                                  ordform(term), artikel_id, REGISTRERAD_AV)

        for slug, huvudterm, definition, lemman, extra in BEGREPP:
            begrepp_id = f"begrepp:{slug}"
            entiteter.append((begrepp_id, "begrepp", huvudterm, definition))
            lagg_till(begrepp_id, huvudterm, "swe", "huvudterm")
            for term, sprak, termtyp in extra:
                lagg_till(begrepp_id, term, sprak, termtyp)
            artiklar = _artiklar(cur, lemman)
            hittade = {a[2] for a in artiklar} | {f"{a[1]}:{a[5]}" for a in artiklar}
            saknas = set(lemman) - hittade
            if saknas:
                log.warning("%s: lemman saknas i ordböckerna: %s", huvudterm, ", ".join(sorted(saknas)))
            for artikel_id, _, lemma, _, former, _ in sorted(artiklar, key=lambda a: ORDBOCKER.index(a[1])):
                lagg_till(begrepp_id, lemma, "fsv", "historisk_form", artikel_id)
                for form in (former if isinstance(former, list) else json.loads(former)):
                    if _liknar(form, lemma):
                        lagg_till(begrepp_id, form, "fsv", "historisk_form", artikel_id)

        for entitet_id, typ, namn, beskrivning, former in NAMN:
            entiteter.append((entitet_id, typ, namn, beskrivning))
            lagg_till(entitet_id, namn, "swe", "huvudterm")
            for form, sprak in former:
                lagg_till(entitet_id, form, sprak, "historisk_form")

        # En ordboksform som hör till flera begrepp (borghar: borgar eller
        # borgare) kan inte avgöras vid sökning och tas bort ur alla; termer
        # som angetts här behålls
        begrepp_per_form: dict[str, set[str]] = {}
        for (begrepp_id, sokform, _), rad in termer.items():
            begrepp_per_form.setdefault(sokform, set()).add(begrepp_id)
        tvetydiga = [nyckel for nyckel, rad in termer.items()
                     if len(begrepp_per_form[nyckel[1]]) > 1 and rad[6] is not None]
        for nyckel in tvetydiga:
            del termer[nyckel]
        if tvetydiga:
            log.info("%d ordboksformer hör till flera begrepp och togs bort: %s", len(tvetydiga),
                     ", ".join(sorted({k[1] for k in tvetydiga})))

        # Termer som en tidigare körning skapat men som filtren nu sållar bort
        # ska försvinna; granskade termer och termer från andra källor rörs inte
        with conn:
            conn.cursor().execute(
                f"DELETE FROM {p}term WHERE registrerad_av = {db._ph()} AND NOT granskad",
                (REGISTRERAD_AV,),
            )

        db.upsert(conn, "entitet", ["id", "typ", "namn", "beskrivning"], ["id"], entiteter)
        db.upsert(conn, "term",
                  ["id", "entitet_id", "term", "sprak", "termtyp", "sokform", "artikel_id",
                   "registrerad_av"], ["id"], list(termer.values()))
        db.upsert(conn, "begreppsrelation", ["fran_id", "till_id", "relation"],
                  ["fran_id", "till_id", "relation"],
                  [(f"begrepp:{a}", f"begrepp:{b}", r) for a, b, r in RELATIONER])
        log.info("%d begrepp, %d termer, %d relationer", len(entiteter), len(termer), len(RELATIONER))
    finally:
        conn.close()


def kandidater(antal: int) -> None:
    """
    Skriver ut ord som är vanliga i SDHK:s regester och som också är
    uppslagsord hos Schlyter, men som inte finns i registret. Listan är ett
    underlag för att utöka registret, inget som skrivs till databasen.
    """
    p, ph = db._prefix(), db._ph()
    conn = db._hamta_db()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT sokform FROM {p}term")
        kanda = {r[0] for r in cur.fetchall()}
        cur.execute(f"SELECT sokform, lemma FROM {p}ordboksartikel WHERE kallsamling_id = {ph}",
                    ("schlyter",))
        schlyter: dict[str, str] = {}
        for sokform, lemma in cur.fetchall():
            schlyter.setdefault(sokform, lemma)
        cur.execute(f"SELECT text FROM {p}passage WHERE typ = 'regest'")
        # Bara ord med liten begynnelsebokstav räknas, så att personnamn
        # (Olof, Karl) och ortnamn (Lund) inte tar över listan
        frekvens = collections.Counter(
            ord_ for (text,) in cur.fetchall()
            for ord_ in re.findall(r"(?<![\w-])[a-zåäö][^\W\d_]{3,}", text)
            if ord_ not in FUNKTIONSORD
        )
    finally:
        conn.close()
    traffar = [(ord_, n, schlyter[ordform(ord_)]) for ord_, n in frekvens.most_common()
               if ordform(ord_) in schlyter and ordform(ord_) not in kanda]
    print(f"{'ord i regesterna':24} {'antal':>6}  uppslagsord hos Schlyter")
    for ord_, n, lemma in traffar[:antal]:
        print(f"{ord_:24} {n:>6}  {lemma}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("--kandidater", type=int, metavar="N",
                      help="skriv ut N termförslag ur SDHK:s regester i stället för att bygga")
    arg = tolk.parse_args()
    if arg.kandidater:
        kandidater(arg.kandidater)
    else:
        bygg()


if __name__ == "__main__":
    main()

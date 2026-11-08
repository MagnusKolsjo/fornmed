#!/usr/bin/env bash
# =============================================================================
# Läser in RDF-exporten från utvecklingsdatorn i SPARQL-ändpunkten och
# publicerar dumpfilerna, och EDM-profilen i underkatalogen edm/.
#
#     sudo bash /srv/fornmed/fornmed/deploy/las_in_rdf.sh /srv/fornmed/inkommande/rdf-<TIDPUNKT>
#
# Katalogen innehåller en gzippad N-Quads-fil per graf, skriven av
# rdf_export.py. Filerna läses in i en ny Oxigraph-databas medan den gamla
# fortsätter att svara. Efter en kontroll av antalet tripler pekas länken
# sparql/aktuell om till den nya databasen och fornmed-sparql startas om;
# avbrottet är de sekunder omstarten tar. Svarar tjänsten inte pekas länken
# tillbaka. Dumpfilerna flyttas till rdf/<TIDPUNKT>, och rdf/aktuell, som
# nginx visar under /data/rdf/, pekas om på samma sätt.
#
# Den förra databasen tas bort när den nya svarar, eftersom varje databas tar
# några GB. De förra dumpfilerna ligger kvar och kan läsas in igen med
#
#     sudo bash /srv/fornmed/fornmed/deploy/las_in_rdf.sh --aterstall
# =============================================================================

set -euo pipefail

BAS=/srv/fornmed
SPARQL=$BAS/sparql
RDF=$BAS/rdf
OXIGRAPH=/usr/local/bin/oxigraph
PORT=7878

steg() { printf '\n==> %s\n' "$*"; }
fel() { printf 'FEL: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fel "Kör skriptet med sudo."
[[ $# -eq 1 ]] || fel "Ange katalogen med dumpfilerna, eller --aterstall."
[[ -x $OXIGRAPH ]] || fel "$OXIGRAPH saknas. Kör installera_server.sh."
mkdir -p "$SPARQL" "$RDF"

antal_tripler() {
    curl -fsS -m 30 -G -H 'Accept: text/csv' \
        --data-urlencode 'query=SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }' \
        "http://127.0.0.1:$PORT/query" 2>/dev/null | tail -1 | tr -d '\r'
}

svarar() {
    for _ in $(seq 1 20); do
        local n
        n=$(antal_tripler || true)
        [[ $n =~ ^[0-9]+$ && $n -gt 0 ]] && { echo "$n"; return 0; }
        sleep 2
    done
    return 1
}

if [[ $1 == --aterstall ]]; then
    foregaende=$(ls -1d "$RDF"/20* 2>/dev/null | grep -v "$(readlink -f "$RDF/aktuell" || echo ingen)" | tail -1 || true)
    [[ -n $foregaende ]] || fel "Det finns inga tidigare dumpfiler att läsa in."
    INKOMMANDE=$(mktemp -d "$BAS/inkommande/rdf-aterstall-XXXX")
    cp "$foregaende"/*.nq.gz "$INKOMMANDE/"
    [[ -d $foregaende/edm ]] && cp -r "$foregaende/edm" "$INKOMMANDE/"
    set -- "$INKOMMANDE"
fi

INKOMMANDE=${1%/}
[[ -d $INKOMMANDE ]] || fel "Katalogen $INKOMMANDE finns inte."
compgen -G "$INKOMMANDE/*.nq.gz" > /dev/null || fel "Inga .nq.gz-filer i $INKOMMANDE."
[[ -f $INKOMMANDE/metadata.nq.gz ]] || fel "metadata.nq.gz saknas; är det en hel export?"

TIDPUNKT=$(date +%Y%m%d-%H%M%S)
NY=$SPARQL/$TIDPUNKT
NYA_DUMPAR=$RDF/$TIDPUNKT
GAMMAL=$(readlink -f "$SPARQL/aktuell" 2>/dev/null || true)
GAMLA_DUMPAR=$(readlink -f "$RDF/aktuell" 2>/dev/null || true)

# -----------------------------------------------------------------------------
steg "Läser in $(ls "$INKOMMANDE"/*.nq.gz | wc -l) filer i $NY"
# -----------------------------------------------------------------------------
"$OXIGRAPH" load --location "$NY" --file "$INKOMMANDE"/*.nq.gz
"$OXIGRAPH" optimize --location "$NY"

# Exporten anger i sin VoID-beskrivning hur många tripler den skrev. Några
# tripler kan förekomma två gånger i exporten och slås då ihop, så den nya
# databasen får ha något färre, men inte många färre.
vantat=$("$OXIGRAPH" query --location "$NY" --results-format csv --query \
    'SELECT ?n WHERE { GRAPH ?g { <https://w3id.org/fornmed/> <http://rdfs.org/ns/void#triples> ?n } }' \
    | tail -1 | tr -d '\r')
inlast=$("$OXIGRAPH" query --location "$NY" --results-format csv --query \
    'SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }' | tail -1 | tr -d '\r')
echo "Tripler enligt exporten: $vantat  Inlästa: $inlast"
[[ $vantat =~ ^[0-9]+$ && $inlast =~ ^[0-9]+$ && $inlast -gt 0 && $inlast -ge $((vantat * 99 / 100)) ]] || {
    rm -rf "$NY"
    fel "Inläsningen ser ofullständig ut. Den gamla databasen är orörd."
}

# -----------------------------------------------------------------------------
steg "Byter in den nya databasen och dumpfilerna"
# -----------------------------------------------------------------------------
mkdir -p "$NYA_DUMPAR"
cp "$INKOMMANDE"/*.nq.gz "$NYA_DUMPAR/"
# EDM-profilen publiceras bredvid dumpfilerna men läses inte in i SPARQL-ändpunkten
[[ -d $INKOMMANDE/edm ]] && cp -r "$INKOMMANDE/edm" "$NYA_DUMPAR/"
chmod -R a+rX "$NY" "$NYA_DUMPAR"

ln -sfn "$NY" "$SPARQL/aktuell.ny" && mv -T "$SPARQL/aktuell.ny" "$SPARQL/aktuell"
# Omstarten och kontrollen står i villkoret, så att set -e inte avbryter skriptet
# när omstarten misslyckas: då ska länken alltid tillbaka till den gamla databasen
if systemctl restart fornmed-sparql.service && n=$(svarar); then
    ln -sfn "$NYA_DUMPAR" "$RDF/aktuell.ny" && mv -T "$RDF/aktuell.ny" "$RDF/aktuell"
    echo "SPARQL-ändpunkten svarar med $n tripler."
else
    echo "SPARQL-ändpunkten svarar inte med den nya databasen. Byter tillbaka." >&2
    rm -rf "$NYA_DUMPAR"
    if [[ -n $GAMMAL && -d $GAMMAL ]]; then
        ln -sfn "$GAMMAL" "$SPARQL/aktuell.ny" && mv -T "$SPARQL/aktuell.ny" "$SPARQL/aktuell"
        if systemctl restart fornmed-sparql.service && svarar > /dev/null; then
            echo "Den gamla databasen svarar igen." >&2
        else
            echo "Den gamla databasen svarar inte heller. SPARQL-ändpunkten är nere." >&2
        fi
    else
        echo "Det finns ingen tidigare databas att byta tillbaka till. SPARQL-ändpunkten är nere." >&2
    fi
    fel "Den nya databasen ligger kvar i $NY. Se: journalctl -u fornmed-sparql -n 50"
fi

# -----------------------------------------------------------------------------
steg "Städar"
# -----------------------------------------------------------------------------
# Bara den aktuella databasen sparas. Av dumpfilerna sparas de aktuella och
# de förra, så att --aterstall kan läsa in dem igen.
for katalog in "$SPARQL"/20*; do
    [[ $(readlink -f "$katalog") == "$NY" ]] || rm -rf "$katalog"
done
for katalog in "$RDF"/20*; do
    case "$(readlink -f "$katalog")" in
        "$NYA_DUMPAR"|"$GAMLA_DUMPAR") ;;
        *) rm -rf "$katalog" ;;
    esac
done
rm -rf "$INKOMMANDE"
echo "Klart. Ledigt på disken: $(df -h "$BAS" | awk 'NR == 2 {print $4}')"

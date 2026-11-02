#!/usr/bin/env bash
# =============================================================================
# Läser in en databaskopia från utvecklingsdatorn och byter in den.
#
#     sudo bash /srv/fornmed/fornmed/deploy/las_in_databas.sh /srv/fornmed/inkommande/<FIL>.pgdump
#
# Kopian läses in i fornmed_ny medan söktjänsten fortsätter att svara från
# fornmed. Därefter körs ANALYZE och en kontroll av innehållet. Först när
# kontrollen går igenom byter databaserna namn (fornmed → fornmed_foregaende,
# fornmed_ny → fornmed) i en och samma transaktion, så att fornmed hela tiden
# finns. Söktjänsten startas inte om: den öppnar en ny anslutning för varje
# anrop och har modellerna kvar i minnet, och MCP-sessionerna överlever.
# Avbrottet är de millisekunder då den gamla databasen stängs för nya
# anslutningar. Svarar tjänsten inte med den nya kopian byts namnen tillbaka.
#
# Den förra kopian ligger kvar som fornmed_foregaende till nästa inläsning
# och kan återställas med
#
#     sudo bash /srv/fornmed/fornmed/deploy/las_in_databas.sh --aterstall
# =============================================================================

set -euo pipefail

PORT=8424
LAS=/run/fornmed-inlasning

steg() { printf '\n==> %s\n' "$*"; }
fel() { printf 'FEL: %s\n' "$*" >&2; exit 1; }
psql_su() { sudo -u postgres psql -v ON_ERROR_STOP=1 -qAt "$@"; }
finns() { [[ -n $(psql_su -c "SELECT 1 FROM pg_database WHERE datname = '$1'") ]]; }

[[ $EUID -eq 0 ]] || fel "Kör skriptet med sudo."
[[ $# -eq 1 ]] || fel "Ange dumpfilen, eller --aterstall."

stang_anslutningar() {
    psql_su -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                WHERE datname = '$1' AND pid <> pg_backend_pid();" > /dev/null
}

# Söktjänsten svarar och har innehåll, alltså verk i databasen den läser
svarar() {
    for _ in $(seq 1 20); do
        curl -fsS -m 10 "http://127.0.0.1:$PORT/v1/verk?per_sida=1" 2>/dev/null \
            | grep -q '"total":[1-9]' && return 0
        sleep 3
    done
    return 1
}

# Byter in databasen $in som fornmed; den nuvarande fornmed får namnet $ut.
# Den gamla databasen stängs för nya anslutningar, de pågående avbryts och
# båda namnbytena görs i en transaktion. Hinner en anslutning öppnas emellan
# misslyckas namnbytet, och då görs det om. Hälsokontrollen låter tjänsten
# vara medan låsfilen finns.
byt() {
    local ut=$1 in=$2 klart=nej
    touch "$LAS"
    trap 'rm -f "$LAS"' EXIT
    if finns "$ut"; then
        stang_anslutningar "$ut"
        psql_su -c "DROP DATABASE \"$ut\";"
    fi
    psql_su -c "ALTER DATABASE fornmed WITH ALLOW_CONNECTIONS false;"
    for _ in $(seq 1 20); do
        stang_anslutningar fornmed
        stang_anslutningar "$in"
        if psql_su -1 -c "ALTER DATABASE fornmed RENAME TO \"$ut\";" \
                      -c "ALTER DATABASE \"$in\" RENAME TO fornmed;" 2>/dev/null; then
            klart=ja
            break
        fi
        sleep 0.2
    done
    if [[ $klart == ja ]]; then
        psql_su -c "ALTER DATABASE \"$ut\" WITH ALLOW_CONNECTIONS true;"
    else
        psql_su -c "ALTER DATABASE fornmed WITH ALLOW_CONNECTIONS true;"
        rm -f "$LAS"
        fel "Namnbytet lyckades inte; fornmed är orörd och $in ligger kvar."
    fi
    rm -f "$LAS"
}

if [[ $1 == --aterstall ]]; then
    finns fornmed_foregaende || fel "Det finns ingen tidigare kopia att återställa."
    steg "Återställer den tidigare kopian"
    byt fornmed_aterstalld fornmed_foregaende
    psql_su -c "ALTER DATABASE fornmed_aterstalld RENAME TO fornmed_foregaende;"
    svarar && echo "Den tidigare kopian är tillbaka." || fel "Söktjänsten svarar inte med den tidigare kopian."
    exit 0
fi

DUMP=$1
[[ -f $DUMP ]] || fel "Filen $DUMP finns inte."

# -----------------------------------------------------------------------------
steg "Läser in $DUMP i fornmed_ny"
# -----------------------------------------------------------------------------
if finns fornmed_ny; then
    stang_anslutningar fornmed_ny
    psql_su -c "DROP DATABASE fornmed_ny;"
fi
sudo -u postgres createdb fornmed_ny
# pg_restore körs som postgres, som kan skapa tillägget vector, och utan
# ägare och behörigheter från utvecklingsdatorn; söktjänstens roll får sina
# rättigheter nedan. -j kräver att pg_restore läser filen själv, och
# postgres kommer inte åt inkommande, så filen kopieras först.
TMP=/var/lib/postgresql/fornmed-inlasning.pgdump
install -o postgres -g postgres -m 600 "$DUMP" "$TMP"
trap 'rm -f "$TMP"' EXIT
sudo -u postgres pg_restore --no-owner --no-acl --exit-on-error -j 3 -d fornmed_ny "$TMP"
rm -f "$TMP"

psql_su -c "GRANT CONNECT ON DATABASE fornmed_ny TO fornmed_las;"
psql_su -d fornmed_ny -c "GRANT USAGE ON SCHEMA fornmed TO fornmed_las;
                         GRANT SELECT ON ALL TABLES IN SCHEMA fornmed TO fornmed_las;"

# -----------------------------------------------------------------------------
steg "ANALYZE och kontroll"
# -----------------------------------------------------------------------------
sudo -u postgres vacuumdb --analyze-only -q -d fornmed_ny
verk=$(psql_su -d fornmed_ny -c "SELECT count(*) FROM fornmed.verk")
passager=$(psql_su -d fornmed_ny -c "SELECT count(*) FROM fornmed.passage")
vektorer=$(psql_su -d fornmed_ny -c "SELECT count(*) FROM fornmed.embedding")
traffar=$(psql_su -d fornmed_ny -c "SELECT count(*) FROM fornmed.passage
                                    WHERE sokvektor @@ to_tsquery('simple', 'konung')")
echo "Verk: $verk  Passager: $passager  Vektorer: $vektorer  Fulltextträffar på 'konung': $traffar"
[[ $verk -gt 0 && $passager -gt 0 && $vektorer -gt 0 && $traffar -gt 0 ]] || \
    fel "Kopian ser ofullständig ut. fornmed är orörd; fornmed_ny ligger kvar för kontroll."

# -----------------------------------------------------------------------------
steg "Byter in den nya kopian"
# -----------------------------------------------------------------------------
byt fornmed_foregaende fornmed_ny
if svarar; then
    leverans=$(psql_su -d fornmed -c "SELECT id || ' ' || coalesce(anmarkning, '') FROM fornmed.leverans
                                      ORDER BY tidpunkt DESC LIMIT 1" 2>/dev/null || true)
    echo "Söktjänsten svarar med den nya kopian. Leverans: ${leverans:-ingen registrerad}"
else
    echo "Söktjänsten svarar inte med den nya kopian. Byter tillbaka." >&2
    byt fornmed_misslyckad fornmed_foregaende
    psql_su -c "ALTER DATABASE fornmed_misslyckad RENAME TO fornmed_ny;"
    svarar || true
    fel "Den nya kopian ligger kvar som fornmed_ny. Se: journalctl -u fornmed-tjanst -n 50"
fi

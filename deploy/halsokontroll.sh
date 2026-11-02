#!/usr/bin/env bash
# =============================================================================
# Hälsokontrollen, körd av fornmed-halsokontroll.timer var femte minut.
#
# Kontrollerar söktjänsten, de publika adresserna, MCP-servern, Umami,
# databasen, disken och certifikatet, och skriver en slutrad STATUS: GRÖNT
# eller STATUS: RÖTT med orsakerna.
#
# Svarar söktjänsten inte lokalt startas den om. Det ordnar de flesta fel
# utan att någon behöver larmas.
#
# Healthchecks.io är larmkanalen (FORNMED_HEALTHCHECKS_URL i .env):
#
# - Vid GRÖNT pingas kontrollen. Kontrollen är en "dead man's switch": stannar
#   timern, kraschar skriptet eller når servern inte Healthchecks uteblir
#   pingen, och Healthchecks larmar när fristen löpt ut.
# - Vid RÖTT skickas ingenting första gången, eftersom en omstart efter en
#   kodleverans kan träffas av en körning. Står felet kvar vid nästa körning
#   skickas utskriften till kontrollens /fail, som larmar direkt och säger
#   vad som fallerade.
#
# Under en databasinläsning (/run/fornmed-inlasning) är tjänsten stoppad med
# avsikt; då görs ingenting.
#
# Sätt kontrollen hos Healthchecks till period 5 minuter och frist 15 minuter.
# =============================================================================

set -uo pipefail

# Domänen och underdomänerna ur deploy/server.env (mall: server.example.env)
KONFIG="$(cd "$(dirname "$0")" && pwd)/server.env"
[[ -f $KONFIG ]] || { echo "FEL: $KONFIG saknas. Kopiera server.example.env och ange domänen." >&2; exit 1; }
# shellcheck source=/dev/null
source "$KONFIG"
DOMAN=${FORNMED_DOMAN:-}
[[ $DOMAN =~ ^[a-z0-9.-]+\.[a-z]+$ ]] || { echo "FEL: FORNMED_DOMAN i $KONFIG är inte en domän: '$DOMAN'" >&2; exit 1; }

KOD=/srv/fornmed/fornmed
TILLSTAND=/var/lib/fornmed/halsokontroll-roda-i-foljd
UTSKRIFT=/var/lib/fornmed/halsokontroll-senaste.txt
ROTT_LARMAR_EFTER=2
MIN_LEDIG_DISK_GB=3
MIN_CERTIFIKAT_DAGAR=14

[[ -e /run/fornmed-inlasning ]] && exit 0

URL=$(grep -E '^FORNMED_HEALTHCHECKS_URL=' "$KOD/.env" 2>/dev/null | tail -1 | cut -d= -f2- || true)
install -d -m 755 /var/lib/fornmed

fel=()
kontroll() {
    # kontroll <namn> <kommando …>: noterar namnet som fel om kommandot misslyckas
    local namn=$1; shift
    if "$@" > /dev/null 2>&1; then
        echo "ok    $namn"
    else
        echo "FEL   $namn"
        fel+=("$namn")
    fi
}

{
    # Söktjänsten lokalt; startas om en gång om den inte svarar
    if ! curl -fsS -m 15 -o /dev/null http://127.0.0.1:8424/halsa; then
        echo "Söktjänsten svarar inte lokalt; startar om"
        logger -t fornmed "Söktjänsten svarar inte; startar om"
        systemctl restart fornmed-tjanst
        for _ in $(seq 1 40); do
            curl -fsS -m 5 -o /dev/null http://127.0.0.1:8424/halsa && break
            sleep 3
        done
    fi
    kontroll "söktjänsten lokalt" curl -fsS -m 15 -o /dev/null http://127.0.0.1:8424/halsa

    kontroll "https://$DOMAN" curl -fsS -m 15 -o /dev/null "https://$DOMAN/"
    kontroll "https://api.$DOMAN" curl -fsS -m 15 -o /dev/null "https://api.$DOMAN/halsa"
    kontroll "databasen har innehåll" sh -c \
        "curl -fsS -m 30 'https://api.$DOMAN/v1/verk?per_sida=1' | grep -q '\"total\":[1-9]'"
    kontroll "https://mcp.$DOMAN" curl -fsS -m 15 -o /dev/null -X POST "https://mcp.$DOMAN/" \
        -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"fornmed-halsokontroll","version":"1"}}}'
    kontroll "Umami" curl -fsS -m 15 -o /dev/null "https://stat.$DOMAN/script.js"

    ledig=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
    kontroll "ledig disk ${ledig} GB (minst $MIN_LEDIG_DISK_GB)" test "$ledig" -ge "$MIN_LEDIG_DISK_GB"

    slut=$(openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$DOMAN/cert.pem" 2>/dev/null | cut -d= -f2)
    dagar=$(( ( $(date -d "${slut:-now}" +%s) - $(date +%s) ) / 86400 ))
    kontroll "certifikatet gäller $dagar dagar till (minst $MIN_CERTIFIKAT_DAGAR)" \
        test "$dagar" -ge "$MIN_CERTIFIKAT_DAGAR"

    if [[ ${#fel[@]} -eq 0 ]]; then
        echo "STATUS: GRÖNT"
    else
        echo "STATUS: RÖTT — $(IFS=';'; echo "${fel[*]}")"
    fi
} > "$UTSKRIFT" 2>&1

slutrad=$(tail -1 "$UTSKRIFT")
echo "$slutrad"

tidigare=$(cat "$TILLSTAND" 2>/dev/null)
[[ $tidigare =~ ^[0-9]+$ ]] || tidigare=0

if [[ $slutrad == "STATUS: GRÖNT" ]]; then
    echo 0 > "$TILLSTAND"
    [[ -n $URL ]] && curl -fsS -m 10 --retry 3 -o /dev/null "$URL"
else
    roda=$(( tidigare + 1 ))
    echo "$roda" > "$TILLSTAND"
    if [[ -n $URL ]] && (( roda >= ROTT_LARMAR_EFTER )); then
        echo "Rött $roda körningar i följd; felsignal till Healthchecks."
        curl -fsS -m 10 --retry 3 -o /dev/null --data-binary "@$UTSKRIFT" "${URL%/}/fail"
    fi
fi
[[ -n $URL ]] || echo "FORNMED_HEALTHCHECKS_URL saknas i $KOD/.env; inget larm skickas." >&2
exit 0

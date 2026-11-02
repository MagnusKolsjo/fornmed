#!/usr/bin/env bash
# =============================================================================
# Registrerar en leverans, gör en databaskopia och läser in den på servern.
#
#     deploy/skicka_databas.sh "Erikskrönikan och 2 000 nya påståenden"
#
# Körs på utvecklingsdatorn, från kodkatalogen vars .env pekar mot databasen
# som ska ut. Anmärkningen visas i webbplatsens lista över uppdateringar.
#
# Inställningar, i miljön eller i .env:
#     FORNMED_PYTHON   Python med projektets paket   (standard: .venv/bin/python)
#     FORNMED_PG_DUMP  pg_dump i serverns huvudversion, 16
#     FORNMED_SSH      ssh-namnet för servern         (standard: fornmed)
# =============================================================================

set -euo pipefail

KALLA=$(cd "$(dirname "$0")/.." && pwd)
[[ $# -eq 1 && -n $1 ]] || { echo "Ange en anmärkning om vad leveransen innehåller." >&2; exit 2; }
ANMARKNING=$1

installning() {
    local namn=$1 standard=$2 varde=${!1:-}
    if [[ -z $varde && -f $KALLA/.env ]]; then
        varde=$(grep -E "^$namn=" "$KALLA/.env" | tail -1 | cut -d= -f2- || true)
    fi
    echo "${varde:-$standard}"
}

PYTHON=$(installning FORNMED_PYTHON "$KALLA/.venv/bin/python")
PG_DUMP=$(installning FORNMED_PG_DUMP pg_dump)
SERVER=$(installning FORNMED_SSH fornmed)

[[ -x $PYTHON ]] || { echo "FEL: hittar inte $PYTHON. Ange FORNMED_PYTHON." >&2; exit 1; }
version=$("$PG_DUMP" --version | grep -oE '[0-9]+' | head -1)
[[ $version == 16 ]] || {
    echo "FEL: $PG_DUMP är version $version; servern kör Postgres 16 och kan inte läsa kopian." >&2
    echo "     Ange FORNMED_PG_DUMP, t.ex. pg_dump i Postgres.app:s version 16." >&2
    exit 1
}

FIL=fornmed-$(date +%Y%m%d-%H%M%S).pgdump
LOKAL=${TMPDIR:-/tmp}/$FIL
trap 'rm -f "$LOKAL"' EXIT

echo "==> Registrerar leveransen och gör kopian"
(cd "$KALLA" && "$PYTHON" leverans.py --anmarkning "$ANMARKNING" --fil "$LOKAL" --pg-dump "$PG_DUMP")
echo "Kopian är $(du -h "$LOKAL" | cut -f1)."

echo "==> Skickar kopian"
rsync -a --partial --progress "$LOKAL" "$SERVER:/srv/fornmed/inkommande/$FIL"

echo "==> Läser in kopian på servern"
ssh -t "$SERVER" "sudo bash /srv/fornmed/fornmed/deploy/las_in_databas.sh /srv/fornmed/inkommande/$FIL"

# De två senaste kopiorna sparas på servern; äldre tas bort
ssh "$SERVER" "ls -t /srv/fornmed/inkommande/*.pgdump | tail -n +3 | xargs -r rm --"

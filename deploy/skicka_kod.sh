#!/usr/bin/env bash
# =============================================================================
# Skickar koden till servern och startar om söktjänsten.
#
# Körs på utvecklingsdatorn, från den kodkatalog som ska ut (oftast
# produktionsmappen). Allt som behövs i drift följer med: Python-modulerna,
# db/, deploy/ och grafisk_profil/. Källdata, .env, Python-miljöer och
# dumpfiler stannar kvar.
#
#     deploy/skicka_kod.sh             skicka och starta om tjänsten
#     deploy/skicka_kod.sh --bara-kod  skicka utan omstart (före första installationen)
#
# Servern nås med ssh-namnet i FORNMED_SSH (standard: fornmed).
# =============================================================================

set -euo pipefail

KALLA=$(cd "$(dirname "$0")/.." && pwd)
SERVER=${FORNMED_SSH:-fornmed}
MAL=/srv/fornmed/fornmed
OMSTART=ja
[[ ${1:-} == --bara-kod ]] && OMSTART=nej

[[ -f $KALLA/tjanst.py ]] || { echo "FEL: $KALLA ser inte ut som Fornmeds kodkatalog." >&2; exit 1; }
[[ -d $KALLA/grafisk_profil ]] || echo "OBS: grafisk_profil/ saknas i $KALLA; startsidan blir utan typsnitt och logotyp."

# Kodkatalogen ägs av den som skickar koden och läses av söktjänsten (www-data)
ssh "$SERVER" "sudo install -d -m 755 /srv/fornmed && sudo install -d -o \"\$USER\" -g www-data -m 755 $MAL"

rsync -az --delete \
    --exclude '.env' --exclude '.venv*/' --exclude '__pycache__/' --exclude '.DS_Store' \
    --exclude 'data/' --exclude 'oberoende_extraktion/' --exclude 'rapporter/' \
    --exclude '*.pgdump' --exclude '*.db' --exclude 'grafisk_profil/fonts/*.ttf' \
    --exclude 'webb/staticfiles/' --exclude 'webb/media/' \
    "$KALLA/" "$SERVER:$MAL/"
echo "Koden skickad till $SERVER:$MAL."

if [[ $OMSTART == ja ]]; then
    ssh "$SERVER" "systemctl list-unit-files fornmed-tjanst.service >/dev/null 2>&1 \
        && sudo systemctl restart fornmed-tjanst && echo 'Söktjänsten omstartad.' \
        || echo 'Söktjänsten är inte installerad än: kör deploy/installera_server.sh på servern.'"
fi

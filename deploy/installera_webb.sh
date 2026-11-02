#!/usr/bin/env bash
# =============================================================================
# Installerar webbplatsen: Django och Wagtail i en egen
# Python-miljö, med en egen databas för sidorna.
#
# Anropas av installera_server.sh och kan också köras ensamt efter en
# kodleverans, för att köra migreringar och samla statiska filer:
#
#     sudo bash /srv/fornmed/fornmed/deploy/installera_webb.sh
#
# Webbplatsen läser källförteckningen och uppdateringarna ur Fornmeds
# databas med söktjänstens skrivskyddade roll. Sidorna skapas med sina
# första texter första gången; därefter redigeras de i Wagtail på
# https://<domän>/admin/, som bara nås från adresserna i
# /etc/nginx/fornmed-admin.conf. Ett konto för redigering skapas med
#
#     sudo -u www-data /srv/fornmed/webb-venv/bin/python /srv/fornmed/fornmed/webb/manage.py createsuperuser
# =============================================================================

set -euo pipefail

# Domänen och underdomänerna ur deploy/server.env (mall: server.example.env)
KONFIG="$(cd "$(dirname "$0")" && pwd)/server.env"
[[ -f $KONFIG ]] || { echo "FEL: $KONFIG saknas. Kopiera server.example.env och ange domänen." >&2; exit 1; }
# shellcheck source=/dev/null
source "$KONFIG"
DOMAN=${FORNMED_DOMAN:-}
[[ $DOMAN =~ ^[a-z0-9.-]+\.[a-z]+$ ]] || { echo "FEL: FORNMED_DOMAN i $KONFIG är inte en domän: '$DOMAN'" >&2; exit 1; }

BAS=/srv/fornmed
WEBB=$BAS/fornmed/webb
VENV=$BAS/webb-venv
STATISKT=$BAS/webb-static
MEDIA=$BAS/webb-media

steg() { printf '\n==> %s\n' "$*"; }
fel() { printf 'FEL: %s\n' "$*" >&2; exit 1; }
psql_su() { sudo -u postgres psql -v ON_ERROR_STOP=1 -qAt "$@"; }

[[ $EUID -eq 0 ]] || fel "Kör skriptet med sudo."
[[ -f $WEBB/manage.py ]] || fel "$WEBB saknar webbplatsen. Skicka koden med deploy/skicka_kod.sh."

# -----------------------------------------------------------------------------
steg "Webbplatsen: databas och miljö"
# -----------------------------------------------------------------------------
psql_su -c "DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fornmed_webb') THEN
        CREATE ROLE fornmed_webb LOGIN;
    END IF;
END \$\$;"
[[ -n $(psql_su -c "SELECT 1 FROM pg_database WHERE datname = 'fornmed_webb'") ]] || \
    sudo -u postgres createdb -O fornmed_webb fornmed_webb

install -d -m 755 "$STATISKT"
install -d -o www-data -g www-data -m 755 "$MEDIA"

if [[ ! -f $WEBB/.env ]]; then
    LOSENORD=$(openssl rand -hex 24)
    psql_su -c "ALTER ROLE fornmed_webb PASSWORD '$LOSENORD';"
    # Fornmeds databas läses med samma skrivskyddade roll som söktjänsten
    FORNMED_URL=$(grep -E '^DATABASE_URL=' "$BAS/fornmed/.env" | cut -d= -f2-)
    cat > "$WEBB/.env" <<ENV
# Skapad av installera_webb.sh
WEBB_DATABASE_URL=postgresql://fornmed_webb:$LOSENORD@localhost:5432/fornmed_webb
FORNMED_DATABASE_URL=$FORNMED_URL
WEBB_SECRET_KEY=$(openssl rand -hex 32)
WEBB_ALLOWED_HOSTS=$DOMAN,www.$DOMAN
WEBB_ADMIN_URL=https://$DOMAN
WEBB_STATIC_ROOT=$STATISKT
WEBB_MEDIA_ROOT=$MEDIA
WEBB_STATISTIK_URL=https://stat.$DOMAN
WEBB_API_URL=https://api.$DOMAN
WEBB_MCP_URL=https://mcp.$DOMAN
ENV
fi
# Webbplatsens id i Umami sätts från installera_umami.sh varje gång
if [[ -s $BAS/umami/webbplats-id ]]; then
    sed -i '/^WEBB_STATISTIK_ID=/d' "$WEBB/.env"
    echo "WEBB_STATISTIK_ID=$(cat "$BAS/umami/webbplats-id")" >> "$WEBB/.env"
fi
chown "$(stat -c %U "$BAS/fornmed"):www-data" "$WEBB/.env"
chmod 640 "$WEBB/.env"

[[ -d $VENV ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$WEBB/requirements.txt"

# -----------------------------------------------------------------------------
steg "Webbplatsen: migreringar, statiska filer och sidor"
# -----------------------------------------------------------------------------
manage() { sudo -u www-data "$VENV/bin/python" "$WEBB/manage.py" "$@"; }
manage migrate --noinput -v 0
# collectstatic skriver som root till $STATISKT, som www-data bara läser
"$VENV/bin/python" "$WEBB/manage.py" collectstatic --noinput -v 0 --clear
manage skapa_sidor

install -m 644 "$(dirname "$0")/fornmed-webb.service" /etc/systemd/system/fornmed-webb.service
for enhet in fornmed-sakerhetskopia.service fornmed-sakerhetskopia.timer; do
    install -m 644 "$(dirname "$0")/$enhet" "/etc/systemd/system/$enhet"
done
systemctl daemon-reload
systemctl enable fornmed-webb.service fornmed-sakerhetskopia.timer
systemctl restart fornmed-webb.service
systemctl start fornmed-sakerhetskopia.timer

for _ in $(seq 1 20); do
    [[ -S /run/fornmed-webb/fornmed-webb.sock ]] && break
    sleep 1
done
[[ -S /run/fornmed-webb/fornmed-webb.sock ]] || fel "Webbplatsen startade inte. Se: journalctl -u fornmed-webb -n 50"
echo "Webbplatsen är igång."

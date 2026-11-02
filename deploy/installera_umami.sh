#!/usr/bin/env bash
# =============================================================================
# Installerar Umami, kakfri besöksstatistik, för webbplatsen.
#
# Anropas av installera_server.sh och kan också köras ensamt:
#
#     sudo bash /srv/fornmed/fornmed/deploy/installera_umami.sh
#
# Umami byggs från sin git-tagg i /srv/fornmed/umami med en egen databas.
# Ett nytt bygge görs bara när UMAMI_VERSION ändras. Webbplatsen (domänen i
# deploy/server.env)
# registreras i Umami, och dess id skrivs till /srv/fornmed/umami/webbplats-id,
# som installera_server.sh läser när spårningsskriptet läggs in på startsidan.
#
# Umami skapar kontot admin med lösenordet umami. Byt det vid första
# inloggningen på https://stat.<domän>; inloggningen nås bara från
# adresserna i /etc/nginx/fornmed-admin.conf.
# =============================================================================

set -euo pipefail

# Domänen och underdomänerna ur deploy/server.env (mall: server.example.env)
KONFIG="$(cd "$(dirname "$0")" && pwd)/server.env"
[[ -f $KONFIG ]] || { echo "FEL: $KONFIG saknas. Kopiera server.example.env och ange domänen." >&2; exit 1; }
# shellcheck source=/dev/null
source "$KONFIG"
DOMAN=${FORNMED_DOMAN:-}
[[ $DOMAN =~ ^[a-z0-9.-]+\.[a-z]+$ ]] || { echo "FEL: FORNMED_DOMAN i $KONFIG är inte en domän: '$DOMAN'" >&2; exit 1; }

UMAMI_VERSION=v3.3.1
PNPM_VERSION=12.3.4
UMAMI=/srv/fornmed/umami
PORT=3000

steg() { printf '\n==> %s\n' "$*"; }
fel() { printf 'FEL: %s\n' "$*" >&2; exit 1; }
psql_su() { sudo -u postgres psql -v ON_ERROR_STOP=1 -qAt "$@"; }

[[ $EUID -eq 0 ]] || fel "Kör skriptet med sudo."

# -----------------------------------------------------------------------------
steg "Umami: Node och pnpm"
# -----------------------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q nodejs npm git
[[ $(pnpm -v 2>/dev/null || true) == "$PNPM_VERSION" ]] || npm install -g -q "pnpm@$PNPM_VERSION"

# -----------------------------------------------------------------------------
steg "Umami: databas"
# -----------------------------------------------------------------------------
psql_su -c "DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'umami') THEN
        CREATE ROLE umami LOGIN;
    END IF;
END \$\$;"
[[ -n $(psql_su -c "SELECT 1 FROM pg_database WHERE datname = 'umami'") ]] || \
    sudo -u postgres createdb -O umami umami

# -----------------------------------------------------------------------------
steg "Umami $UMAMI_VERSION"
# -----------------------------------------------------------------------------
install -d -o www-data -g www-data -m 755 "$UMAMI"
som_www() { sudo -u www-data env HOME="$UMAMI/.hem" "$@"; }
install -d -o www-data -g www-data -m 700 "$UMAMI/.hem"

if [[ ! -d $UMAMI/.git ]]; then
    som_www git clone -q --depth 1 --branch "$UMAMI_VERSION" \
        https://github.com/umami-software/umami.git "$UMAMI/kalla"
    # Klonen läggs direkt i katalogen, bredvid .env och webbplats-id
    som_www bash -c "shopt -s dotglob; mv '$UMAMI/kalla'/* '$UMAMI/'; rmdir '$UMAMI/kalla'"
fi

if [[ ! -f $UMAMI/.env ]]; then
    LOSENORD=$(openssl rand -hex 24)
    psql_su -c "ALTER ROLE umami PASSWORD '$LOSENORD';"
    cat > "$UMAMI/.env" <<ENV
# Skapad av installera_umami.sh
DATABASE_URL=postgresql://umami:$LOSENORD@localhost:5432/umami
APP_SECRET=$(openssl rand -hex 32)
TWO_FACTOR_ENCRYPTION_KEY=$(openssl rand -hex 32)
DISABLE_TELEMETRY=1
ENV
fi
chown www-data:www-data "$UMAMI/.env"
chmod 600 "$UMAMI/.env"

if [[ $(cat "$UMAMI/.byggd-version" 2>/dev/null || true) != "$UMAMI_VERSION" ]]; then
    som_www git -C "$UMAMI" fetch -q --depth 1 origin tag "$UMAMI_VERSION"
    som_www git -C "$UMAMI" checkout -q "$UMAMI_VERSION"
    # Bygget läser databasen ur .env och kör Umamis migrationer
    som_www bash -c "cd '$UMAMI' && set -a && . ./.env && set +a \
        && pnpm install --frozen-lockfile --silent && pnpm run build"
    echo "$UMAMI_VERSION" > "$UMAMI/.byggd-version"
fi

install -m 644 "$(dirname "$0")/umami-fornmed.service" /etc/systemd/system/umami-fornmed.service
systemctl daemon-reload
systemctl enable umami-fornmed.service
systemctl restart umami-fornmed.service
for _ in $(seq 1 40); do
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/api/heartbeat" && break
    sleep 3
done
curl -fsS -o /dev/null "http://127.0.0.1:$PORT/api/heartbeat" || fel "Umami svarar inte. Se: journalctl -u umami-fornmed -n 50"

# -----------------------------------------------------------------------------
steg "Umami: webbplatsen $DOMAN"
# -----------------------------------------------------------------------------
# Registreras direkt i databasen, så att spårningen kan läggas in utan att
# någon först loggar in. Webbplatsen ägs av kontot admin.
psql_su -d umami -c "INSERT INTO website (website_id, name, domain, user_id, created_by, created_at)
    SELECT gen_random_uuid(), 'Fornmed', '$DOMAN', u.user_id, u.user_id, now()
    FROM \"user\" u
    WHERE u.username = 'admin'
      AND NOT EXISTS (SELECT 1 FROM website WHERE domain = '$DOMAN' AND deleted_at IS NULL);"
psql_su -d umami -c "SELECT website_id FROM website WHERE domain = '$DOMAN' AND deleted_at IS NULL
    ORDER BY created_at LIMIT 1" > "$UMAMI/webbplats-id"
[[ -s $UMAMI/webbplats-id ]] || fel "Webbplatsen kunde inte registreras i Umami."
echo "Webbplatsens id i Umami: $(cat "$UMAMI/webbplats-id")"

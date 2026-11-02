#!/usr/bin/env bash
# =============================================================================
# Installerar Fornmed på en Ubuntu-server: Postgres 16 med pgvector,
# söktjänsten (API och MCP), Umami, webbplatsen, nginx med certifikat och
# statistiken. Domänen anges i deploy/server.env (mall: server.example.env).
#
# Körs på servern som root, från kodkatalogen som skicka_kod.sh har fyllt:
#
#     sudo bash /srv/fornmed/fornmed/deploy/installera_server.sh --epost <ADRESS>
#
# Skriptet kan köras om. Det som redan finns behålls: lösenordet för den
# skrivskyddade databasrollen, .env, modellerna, certifikaten och databasen.
# Konfigurationsfilerna för systemd, nginx och Postgres skrivs om varje gång,
# så att ändringar i deploy/ slår igenom.
#
# Flaggor:
#     --epost ADRESS          e-post till Let's Encrypt (krävs första gången
#                             certifikaten skaffas)
#     --utan-certifikat       hoppa över certbot, t.ex. innan DNS pekar hit
#     --admin-ip ADRESS       adress som får nå Umamis inloggning på
#                             stat.<domän>; kan anges flera gånger
# =============================================================================

set -euo pipefail

# Domänen och underdomänerna ur deploy/server.env (mall: server.example.env)
KONFIG="$(cd "$(dirname "$0")" && pwd)/server.env"
[[ -f $KONFIG ]] || { echo "FEL: $KONFIG saknas. Kopiera server.example.env och ange domänen." >&2; exit 1; }
# shellcheck source=/dev/null
source "$KONFIG"
DOMAN=${FORNMED_DOMAN:-}
[[ $DOMAN =~ ^[a-z0-9.-]+\.[a-z]+$ ]] || { echo "FEL: FORNMED_DOMAN i $KONFIG är inte en domän: '$DOMAN'" >&2; exit 1; }
NAMN=("$DOMAN" "www.$DOMAN" "api.$DOMAN" "mcp.$DOMAN" "stat.$DOMAN")

BAS=/srv/fornmed
KOD=$BAS/fornmed
VENV=$BAS/venv
MODELLER=$BAS/modeller
INKOMMANDE=$BAS/inkommande
WEBB=/var/www/fornmed
STATISTIK=/var/www/goaccess-fornmed
PG_VERSION=16
PORT=8424

EPOST=""
CERTIFIKAT=ja
ADMIN_IP=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --epost) EPOST="$2"; shift 2 ;;
        --utan-certifikat) CERTIFIKAT=nej; shift ;;
        --admin-ip) ADMIN_IP+=("$2"); shift 2 ;;
        *) echo "Okänd flagga: $1" >&2; exit 2 ;;
    esac
done

steg() { printf '\n==> %s\n' "$*"; }
fel() { printf 'FEL: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fel "Kör skriptet med sudo."
[[ -f $KOD/tjanst.py ]] || fel "$KOD saknar koden. Kör deploy/skicka_kod.sh från utvecklingsdatorn först."
# Kodkatalogens ägare är den som skickar koden; .env och inkommande ägs av samma användare
AGARE=$(stat -c %U "$KOD")

# -----------------------------------------------------------------------------
steg "Paket"
# -----------------------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q ca-certificates curl gnupg rsync nginx certbot python3-certbot-nginx \
    python3-venv python3-dev build-essential libpq-dev goaccess apache2-utils fail2ban

# Postgres 16 och pgvector från PostgreSQL:s eget arkiv: Ubuntu levererar en
# nyare huvudversion, och dumparna från utvecklingsdatorn kommer från 16
if [[ ! -f /etc/apt/sources.list.d/pgdg.list ]]; then
    install -d /usr/share/postgresql-common/pgdg
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list
    apt-get update -q
fi
apt-get install -y -q "postgresql-$PG_VERSION" "postgresql-$PG_VERSION-pgvector"

# -----------------------------------------------------------------------------
steg "Postgres"
# -----------------------------------------------------------------------------
install -m 644 "$KOD/deploy/postgresql-fornmed.conf" "/etc/postgresql/$PG_VERSION/main/conf.d/fornmed.conf"
systemctl enable --now "postgresql@$PG_VERSION-main"
systemctl restart "postgresql@$PG_VERSION-main"

psql_su() { sudo -u postgres psql -v ON_ERROR_STOP=1 -qAt "$@"; }

# Databasen ägs av postgres och läses in av las_in_databas.sh; fornmed_las är
# söktjänstens roll och får bara läsa
psql_su -c "DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fornmed_las') THEN
        CREATE ROLE fornmed_las LOGIN;
    END IF;
END \$\$;"

if [[ -z $(psql_su -c "SELECT 1 FROM pg_database WHERE datname = 'fornmed'") ]]; then
    # En tom databas tills den första kopian läses in med las_in_databas.sh
    sudo -u postgres createdb fornmed
    psql_su -d fornmed -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE SCHEMA IF NOT EXISTS fornmed;"
fi
psql_su -c "GRANT CONNECT ON DATABASE fornmed TO fornmed_las;"
psql_su -d fornmed -c "GRANT USAGE ON SCHEMA fornmed TO fornmed_las; GRANT SELECT ON ALL TABLES IN SCHEMA fornmed TO fornmed_las;"

# -----------------------------------------------------------------------------
steg "Kataloger och konfiguration"
# -----------------------------------------------------------------------------
install -d -m 755 "$BAS"
install -d -o "$AGARE" -g "$AGARE" -m 750 "$INKOMMANDE"
install -d -o www-data -g www-data -m 755 "$MODELLER"
install -d -m 755 "$WEBB" "$STATISTIK"

if [[ ! -f $KOD/.env ]]; then
    LOSENORD=$(openssl rand -hex 24)
    psql_su -c "ALTER ROLE fornmed_las PASSWORD '$LOSENORD';"
    cat > "$KOD/.env" <<ENV
# Skapad av installera_server.sh. Lösenordet finns bara här och i Postgres.
DATABASE_URL=postgresql://fornmed_las:$LOSENORD@localhost:5432/fornmed

EMBEDDING_MODELL=KBLab/sentence-bert-swedish-cased
EMBEDDING_MODELL_FLERSPRAK=intfloat/multilingual-e5-base

# Söktjänsten (tjanst.py)
FORNMED_HOST=127.0.0.1
FORNMED_PORT=$PORT
# Databasen kommer färdig från utvecklingsdatorn, och rollen får bara läsa
FORNMED_INITIERA_SCHEMA=av

# MCP-servern: öppet läsläge, bakom nginx på mcp.$DOMAN
MCP_OPPEN_LASNING=på
MCP_TILLATNA_VARDAR=mcp.$DOMAN
ENV
    echo "Skapade $KOD/.env med ett nytt lösenord för fornmed_las."
fi
chown "$AGARE:www-data" "$KOD/.env"
chmod 640 "$KOD/.env"

# -----------------------------------------------------------------------------
steg "Python-miljö"
# -----------------------------------------------------------------------------
[[ -d $VENV ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
# PyTorch för CPU först: standardpaketet drar med sig CUDA och flera GB
"$VENV/bin/pip" install -q torch --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/pip" install -q -r "$KOD/requirements.txt"

# -----------------------------------------------------------------------------
steg "Embeddingmodeller"
# -----------------------------------------------------------------------------
# Laddas ner en gång till $MODELLER; tjänsten läser dem sedan utan nätåtkomst
sudo -u www-data env HF_HOME="$MODELLER" XDG_CACHE_HOME="$MODELLER/cache" "$VENV/bin/python" - <<'PY'
from sentence_transformers import SentenceTransformer
for modell in ("KBLab/sentence-bert-swedish-cased", "intfloat/multilingual-e5-base"):
    SentenceTransformer(modell, device="cpu")
    print("Modell på plats:", modell)
PY

# -----------------------------------------------------------------------------
steg "Söktjänsten och timrarna"
# -----------------------------------------------------------------------------
for enhet in fornmed-tjanst.service fornmed-halsokontroll.service fornmed-halsokontroll.timer \
             fornmed-goaccess.service fornmed-goaccess.timer; do
    install -m 644 "$KOD/deploy/$enhet" "/etc/systemd/system/$enhet"
done
systemctl daemon-reload
systemctl enable fornmed-tjanst.service fornmed-halsokontroll.timer fornmed-goaccess.timer
systemctl restart fornmed-tjanst.service
systemctl start fornmed-halsokontroll.timer fornmed-goaccess.timer

# -----------------------------------------------------------------------------
steg "Umami"
# -----------------------------------------------------------------------------
bash "$KOD/deploy/installera_umami.sh"

# -----------------------------------------------------------------------------
steg "Webbplatsen"
# -----------------------------------------------------------------------------
bash "$KOD/deploy/installera_webb.sh"

# -----------------------------------------------------------------------------
steg "Sidan vid omstart"
# -----------------------------------------------------------------------------
# Sidan som nginx visar när webbplatsen eller söktjänsten startar om
install -m 644 "$KOD/deploy/startsida/503.html" "$WEBB/503.html"
[[ -f $STATISTIK/index.html ]] || install -m 644 "$KOD/deploy/startsida/statistik.html" "$STATISTIK/index.html"

# -----------------------------------------------------------------------------
steg "nginx"
# -----------------------------------------------------------------------------
# certbot skriver in sina 443-block i den installerade filen. Den skrivs
# därför bara över när källan i deploy/ har ändrats; då saknas certbots block
# och läggs in igen nedan.
# Mallen har __DOMAN__ där domänen ska stå
NGINX_KONF=$(mktemp)
sed "s/__DOMAN__/$DOMAN/g" "$KOD/deploy/nginx-fornmed.conf" > "$NGINX_KONF"
if ! cmp -s "$NGINX_KONF" /etc/nginx/fornmed.conf.kalla 2>/dev/null; then
    install -m 644 "$NGINX_KONF" "/etc/nginx/sites-available/$DOMAN"
    install -m 644 "$NGINX_KONF" /etc/nginx/fornmed.conf.kalla
fi
rm -f "$NGINX_KONF"
ln -sf "/etc/nginx/sites-available/$DOMAN" "/etc/nginx/sites-enabled/$DOMAN"
rm -f /etc/nginx/sites-enabled/default
[[ -f /etc/nginx/fornmed-statistik.htpasswd ]] || touch /etc/nginx/fornmed-statistik.htpasswd
# Vilka adresser som når Umamis inloggning. Utan --admin-ip behålls den
# befintliga listan, och finns ingen är inloggningen stängd.
if [[ ${#ADMIN_IP[@]} -gt 0 ]]; then
    { for ip in "${ADMIN_IP[@]}"; do echo "allow $ip;"; done; echo "deny all;"; } > /etc/nginx/fornmed-admin.conf
elif [[ ! -f /etc/nginx/fornmed-admin.conf ]]; then
    echo "deny all;" > /etc/nginx/fornmed-admin.conf
fi
nginx -t
systemctl enable --now nginx
systemctl reload nginx

if [[ $CERTIFIKAT == ja ]] && ! grep -q "managed by Certbot" "/etc/nginx/sites-available/$DOMAN"; then
    domaner=()
    for n in "${NAMN[@]}"; do domaner+=(-d "$n"); done
    if [[ -d /etc/letsencrypt/live/$DOMAN ]]; then
        # Certifikaten finns men nginx-filen är ny: lägg in dem igen, och
        # utvidga certifikatet om ett namn har tillkommit
        certbot --nginx --non-interactive --keep-until-expiring --expand --redirect \
            --cert-name "$DOMAN" "${domaner[@]}"
    elif [[ -n $EPOST ]]; then
        certbot --nginx --non-interactive --agree-tos --redirect -m "$EPOST" \
            --cert-name "$DOMAN" "${domaner[@]}"
    else
        echo "Inga certifikat ännu. Kör om med --epost <ADRESS> för att skaffa dem."
    fi
    systemctl reload nginx
fi

# -----------------------------------------------------------------------------
steg "fail2ban"
# -----------------------------------------------------------------------------
systemctl enable --now fail2ban

# -----------------------------------------------------------------------------
steg "Kontroll"
# -----------------------------------------------------------------------------
for i in $(seq 1 60); do
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/halsa" && break
    sleep 3
done
if curl -fsS "http://127.0.0.1:$PORT/halsa"; then
    echo
    echo "Söktjänsten svarar på 127.0.0.1:$PORT."
else
    echo "Söktjänsten svarar inte. Se: journalctl -u fornmed-tjanst -n 50" >&2
fi
antal=$(psql_su -d fornmed -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'fornmed'")
[[ $antal -gt 0 ]] || echo "Databasen är tom. Skicka en kopia med deploy/skicka_databas.sh."
[[ -s /etc/nginx/fornmed-statistik.htpasswd ]] || \
    echo "Statistiken saknar lösenord: sudo htpasswd -c /etc/nginx/fornmed-statistik.htpasswd <ANVÄNDARE>"
echo "Klart."

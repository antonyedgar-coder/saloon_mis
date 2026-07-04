#!/usr/bin/env bash
# One-time setup on the DigitalOcean droplet.
# Run as root: bash setup_droplet.sh
set -euo pipefail

APP_DIR=/var/www/saloon-mis
REPO_URL="${REPO_URL:-}"
DOMAIN_OR_IP="${DOMAIN_OR_IP:-168.144.17.152}"

if [[ -z "$REPO_URL" ]]; then
  echo "Set REPO_URL to your GitHub clone URL, e.g.:"
  echo "  REPO_URL=https://github.com/YOU/saloon-mis.git bash deploy/setup_droplet.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx git curl

mkdir -p /var/log/saloon-mis
mkdir -p /var/www

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [[ ! -f .env ]]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  cat > .env <<EOF
SECRET_KEY=${SECRET}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN_OR_IP}
CSRF_TRUSTED_ORIGINS=http://${DOMAIN_OR_IP}
DATABASE_URL=
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
EOF
  echo "Created $APP_DIR/.env — edit if you add a domain later."
fi

.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput

# Optional demo users (ignore if command missing)
.venv/bin/python manage.py seed_demo 2>/dev/null || true

chown -R www-data:www-data "$APP_DIR" /var/log/saloon-mis
chmod 640 "$APP_DIR/.env"

cp deploy/saloon-mis.service /etc/systemd/system/saloon-mis.service
sed "s/168.144.17.152/${DOMAIN_OR_IP}/g; s/YOUR_DOMAIN_OR_IP/${DOMAIN_OR_IP}/g" deploy/nginx-saloon-mis.conf \
  > /etc/nginx/sites-available/saloon-mis
ln -sfn /etc/nginx/sites-available/saloon-mis /etc/nginx/sites-enabled/saloon-mis
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable saloon-mis
systemctl restart saloon-mis
nginx -t
systemctl restart nginx

echo ""
echo "Setup complete."
echo "Open: http://${DOMAIN_OR_IP}"
echo "App path: ${APP_DIR}"

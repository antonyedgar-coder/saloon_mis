#!/usr/bin/env bash
# Run on the droplet after each git push (also used by GitHub Actions).
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/salon-mis}"
cd "$APP_DIR"

echo ">> Pulling latest code"
git fetch origin
git reset --hard origin/main

echo ">> Installing dependencies"
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo ">> Migrations & static files"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput

echo ">> Fixing permissions"
chown -R www-data:www-data "$APP_DIR"
chmod 640 "$APP_DIR/.env" 2>/dev/null || true

echo ">> Restarting app"
systemctl restart salon-mis
systemctl reload nginx

echo ">> Deploy finished"
systemctl --no-pager --full status salon-mis | head -n 15

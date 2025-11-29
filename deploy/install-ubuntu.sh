#!/usr/bin/env bash
#
# Bare-metal VPS install for Ubuntu 22.04 / 24.04 (no Docker).
# Installs system deps (including Tesseract OCR), builds the frontend, and
# wires up systemd (backend) + nginx (static frontend + API proxy).
#
# Usage (as root or with sudo), from the repo root:
#   sudo bash deploy/install-ubuntu.sh
#
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SERVICE_USER="${SERVICE_USER:-www-data}"
PYTHON="${PYTHON:-python3.11}"

echo "==> Installing system packages (Tesseract, Python, Node, nginx)…"
apt-get update
apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 libglib2.0-0 \
    python3.11 python3.11-venv \
    nginx curl ca-certificates

# Node.js 20 (for building the frontend)
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "==> Tesseract version:"
tesseract --version | head -n1

echo "==> Setting up backend virtualenv…"
cd "$APP_DIR/backend"
$PYTHON -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "!! Created backend/.env from template — edit it and add your keys."
fi
# On Linux, tesseract is on PATH; make sure no Windows path lingers.
sed -i 's|^TESSERACT_CMD=.*|TESSERACT_CMD=|' .env || true

echo "==> Building frontend…"
cd "$APP_DIR/frontend"
npm install
npm run build   # outputs to frontend/dist

echo "==> Installing systemd service…"
sed "s|{{APP_DIR}}|$APP_DIR|g; s|{{USER}}|$SERVICE_USER|g" \
    "$APP_DIR/deploy/docprocessor.service" > /etc/systemd/system/docprocessor.service
systemctl daemon-reload
systemctl enable docprocessor
systemctl restart docprocessor

echo "==> Installing nginx site…"
sed "s|{{APP_DIR}}|$APP_DIR|g" \
    "$APP_DIR/deploy/nginx-site.conf" > /etc/nginx/sites-available/docprocessor
ln -sf /etc/nginx/sites-available/docprocessor /etc/nginx/sites-enabled/docprocessor
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo
echo "==> Done. Backend: systemctl status docprocessor"
echo "    Open http://<server-ip>/  (edit backend/.env keys, then: systemctl restart docprocessor)"

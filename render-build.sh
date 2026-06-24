#!/usr/bin/env bash
set -euo pipefail

echo "━━━ [1/3] Upgrading pip and installing Python packages ━━━"
pip install --upgrade pip
pip install -r requirements.txt

echo "━━━ [2/3] Installing Chromium OS-level dependencies ━━━"
playwright install-deps chromium

echo "━━━ [3/3] Downloading Chromium browser binary ━━━"
playwright install chromium

echo "━━━ Build complete — Chromium is installed and ready ━━━"

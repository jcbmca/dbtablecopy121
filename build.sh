#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

venv/bin/python -m PyInstaller \
  --name mariadb-step-migrator \
  --windowed \
  --onedir \
  --clean \
  app.py

echo "Build listo: $ROOT_DIR/dist/mariadb-step-migrator/mariadb-step-migrator"

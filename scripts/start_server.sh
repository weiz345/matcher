#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# psycopg is used only when HINGE_DATABASE_URL is set (in .env or the environment).
if command -v uvx >/dev/null 2>&1; then
  exec uvx --with 'psycopg[binary]>=3.2,<4' python backend/server.py "$@"
elif [[ -x "$HOME/.local/bin/uvx" ]]; then
  exec "$HOME/.local/bin/uvx" --with 'psycopg[binary]>=3.2,<4' python backend/server.py "$@"
else
  exec python3 backend/server.py "$@"
fi

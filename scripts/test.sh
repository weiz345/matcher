#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s backend -v
if [[ "${1:-}" == "--backend-only" ]]; then exit 0; fi
if command -v uvx >/dev/null 2>&1; then
  runner="$(command -v uvx)"
elif [[ -x "$HOME/.local/bin/uvx" ]]; then
  runner="$HOME/.local/bin/uvx"
else
  echo 'Full direct-client tests require uvx (or run supabase/test_direct.py and browser_smoke.py with dependencies installed).' >&2
  exit 1
fi
"$runner" --with 'psycopg[binary]>=3.2,<4' python supabase/test_direct.py
"$runner" --with playwright --with 'psycopg[binary]>=3.2,<4' python supabase/browser_smoke.py

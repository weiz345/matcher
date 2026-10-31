#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
runner="$(command -v uvx || true)"
if [[ -z "$runner" ]]; then runner="$HOME/.local/bin/uvx"; fi
exec "$runner" --with numpy --with pillow --with onnxruntime python image_lab/server.py "$@"

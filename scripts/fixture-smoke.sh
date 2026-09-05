#!/usr/bin/env bash
# One-command fixture smoke: demo/CI web intel + pytest, no browser, no live network.
# Not production intel. Requires: pip install -r requirements-dev.txt (from repo root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export RIFT_WEB_INTEL=fixture
export RIFT_NO_BROWSER=1
if command -v pytest >/dev/null 2>&1; then
  exec pytest -q tests/test_fixture_scanner.py
fi
exec python3 -m pytest -q tests/test_fixture_scanner.py

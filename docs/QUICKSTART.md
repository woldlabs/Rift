# Quickstart Guide

Product north star / triage: see [VISION.md](../VISION.md) (purpose, non-goals, architecture boundaries, success metrics, Rift↔Judge).

## 1. Installation

```bash
git clone https://github.com/woldlabs/Rift.git
cd Rift
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For tests: `pip install -r requirements-dev.txt`.

Requires Python 3.10+ and a modern browser for the map UI.

## 2. Launch the map UI

```bash
python -m rift
# or
./run-rift.sh          # macOS / Linux (after deps)
# Windows: run-rift.bat
```

Starts a local Flask server (default http://127.0.0.1:7860) and opens a browser.

Useful env vars:

| Env | Effect |
|-----|--------|
| `RIFT_NO_BROWSER=1` | Skip opening a browser (CI / headless) |
| `RIFT_PORT` | Change listen port |
| `RIFT_DEBUG=1` | Flask debug |
| `RIFT_WEB_INTEL=fixture` | Deterministic demo/CI web scan (no live network) |

```bash
python -m rift version
```

## 3. Fixture demo path (no live network)

Checked-in reports: [`tests/fixtures/web_intel_reports.json`](../tests/fixtures/web_intel_reports.json).

```bash
# Headless / deterministic scan provider
export RIFT_WEB_INTEL=fixture
# optional override:
# export RIFT_WEB_INTEL_FIXTURE=/absolute/path/to/reports.json
export RIFT_NO_BROWSER=1
python -m rift
```

In the UI: click **SCAN THE WEB** — with `RIFT_WEB_INTEL=fixture`, Rift replays the fixture (not production intel; no live network).

API equivalent: `POST /api/scan` with `{"provider":"fixture"}`.

## 4. Local upload + Judge bridge (pointers)

Do not duplicate the full README novel — see those sections:

- **Local upload** — [README Usage](../README.md#usage) / [Data Formats](../README.md#data-formats): JSON, CSV, plain text; sample events in [`examples/sample_local_events.json`](../examples/sample_local_events.json).
- **Judge workflow** — [README Rift + Judge Workflow](../README.md#rift--judge-workflow-recommended): **EXPORT FOR JUDGE** → collect media → Judge analyze → upload report JSON back into Rift as `judge` pins.

## 5. One-command fixture smoke (no browser)

SE / CI demos: prove fixture web intel without opening a browser or hitting the network.

```bash
# from repo root, after: pip install -r requirements-dev.txt
./scripts/fixture-smoke.sh
```

Equivalent one-liner:

```bash
RIFT_WEB_INTEL=fixture RIFT_NO_BROWSER=1 python3 -m pytest -q tests/test_fixture_scanner.py
```

Fixture only — demo/CI replay of `tests/fixtures/web_intel_reports.json`. Not live web intel.

## 6. Tests

```bash
pip install -r requirements-dev.txt
RIFT_NO_BROWSER=1 pytest -q
```

## Tips

- Fixture provider is for demo/CI only — do not treat it as live web intel.
- Portal re-runs replace the previous overlay; bad coordinates are skipped on ingest.
- Keep Judge as the media analyzer; Rift owns geography and clustering ([VISION.md](../VISION.md#relation-to-judge)).

# Rift

**RIFT** — Reality Integrity & Fracture Tracker.

A system that hunts for **portals**, **rifts**, and **abnormal events** bleeding into our reality.

Rift ingests signals from three sources and triangulates them on geography:

- **The Internet** — scans for reports, eyewitness accounts, news anomalies, fringe logs, and pattern clusters (simulated feed today; provider-shaped for real connectors).
- **User Local Data** — files, logs, sensor dumps, notes, CSVs of sightings, and **Judge** forensic reports.
- **Interactive World Map** — a zoomable, pannable OpenStreetMap canvas where everything materializes as located events, heat, and portal zones.

**Current version:** 0.2.0

**Product vision / triage:** See [VISION.md](VISION.md) for purpose, non-goals, architecture boundaries, success metrics, and how Rift relates to Judge. **First-run path:** [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Core Features

- **Web Intelligence Scanner**: One-click "Scan the Web". Pulls simulated reports of dimensional anomalies, time slips, glowing rifts, vanishing points, sky tears, and high-strangeness clusters. Events are geolocated and scored with an internet skepticism discount.
  - **Fixture provider (demo/CI only):** set `RIFT_WEB_INTEL=fixture` (optional `RIFT_WEB_INTEL_FIXTURE=/path/to.json`) or POST `/api/scan` with `{"provider":"fixture"}` to replay checked-in reports under `tests/fixtures/web_intel_reports.json`. No live network. Not production intel.
- **Local Data Ingestion**: Upload JSON, CSV, or plain text. Rift parses locations, descriptions, and timestamps. Rift session exports and `{ "events": [...] }` wrappers round-trip. Invalid coordinates are skipped.
- **Zoomable Reality Map**: Leaflet map. Click anywhere to add an observation. Color-coded markers by source and anomaly strength. Optional **heatmap** of fracture intensity.
- **Portal Detector**: Seed-and-gather clustering. A portal is a *place*: every member must sit within ~45 km of the highest-scoring seed **and** within a 96-hour window. Independent sources at the same site raise likelihood. Chains that hop across a continent do not count as one rift.
- **Anomaly Scoring**: Every event receives a 0–100 Fracture Score from linguistic signals (`rift`, `portal`, `glitch`, `void`, `time slip`, …), source weight, and **cross-source corroboration** (nearby reports from a different source in the same time window).
- **Timeline filter**: Restrict the map to the last 24 hours / 3 / 7 / 30 days — for the "holes in the sky in multiple cities on the same night" question.
- **Session Persistence**: Everything lives in `rift_session.json`. Export JSON, GeoJSON, or KML.
- **Filters & Exploration**: Filter by source (Internet / Local / User / Judge), minimum score, time window, free-text search. Click list items to fly the map to the event.
- **Manual Entry & Map Clicks**: Add observations directly. Field notes.
- **Judge bridge**: Export a Judge-ready manifest (top sites + suggested video/audio/sensor). Upload a Judge report JSON and detections land on the map as `judge` pins.

## Why Rift?

Strange things happen. Lights that shouldn't be. People who remember differently. Holes in the sky reported in multiple cities on the same night.

Rift is the instrument that makes the invisible visible — by triangulating the internet's noise, your private data, and geography itself. **Judge** (https://github.com/woldlabs/Judge) is the instrument for the recordings you collect at those coordinates.

## Quick Start

### Prerequisites

- Python 3.10+
- A modern browser for the map

### Install & Run

```bash
git clone https://github.com/woldlabs/Rift.git
cd Rift

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

python -m rift
```

The app starts a local Flask server (default http://127.0.0.1:7860) and opens a browser to the map. Set `RIFT_NO_BROWSER=1` to skip the browser; `RIFT_PORT` to change the port; `RIFT_DEBUG=1` for Flask debug. For deterministic demo/CI scans: `RIFT_WEB_INTEL=fixture`.

On Windows you can also double-click `run-rift.bat` after installing deps.

```bash
python -m rift version
pytest -q          # after pip install -r requirements-dev.txt
```

## Usage

1. **The Map** loads with sample seed events from past incidents (Fremont already forms a demo portal site).
2. Click **SCAN THE WEB** — Rift adds fresh reports from around the globe.
3. **UPLOAD LOCAL DATA** — Drop a CSV or JSON with your own sightings. Judge `demo_report.json` files convert automatically.
4. Click the map to drop a personal observation.
5. Hit **DETECT PORTALS** to run the site engine. Red circles mark high-likelihood convergence zones. Re-running replaces the previous overlay.
6. Toggle **HEATMAP** for fracture intensity. Use the time window and source filters (including **Judge**) to slice the night.
7. **JSON / GeoJSON / KML** export the current dataset. **EXPORT FOR JUDGE** downloads a media-collection manifest for the top sites.

## Data Formats

### JSON import (recommended)

```json
[
  {
    "title": "Glowing vertical tear above the lake",
    "description": "Perfect circle of light, lasted 4 minutes. No sound. Two witnesses.",
    "lat": 47.6062,
    "lon": -122.3321,
    "timestamp": "2026-06-19T02:14:00Z",
    "tags": ["visual", "light"]
  }
]
```

A Rift session file (`{ "events": [ ... ] }`) is accepted as well.

### CSV

Columns: `title,lat,lon,description,timestamp,tags` (tags comma-separated). `latitude` / `longitude` aliases work.

Plain text uploads are treated as a single user observation (default location unless you later edit).

## How Scoring & Portal Detection Works

- **Fracture Score** (0–100): keyword density + report length, then a source weight. Internet reports are discounted (~0.88). Local logs are trusted at 1.0. User field notes and Judge detections are weighted slightly up.
- **Corroboration**: if another *source* reports within ~48 km and 96 hours, the event gets up to +18 on its effective score. This is the triangulation the product is built on.
- **Clustering**: greedy seed-and-gather on effective score. Members must be within `max_dist_km` (default 45) of the seed and within `time_window_hours` (default 96). Not a transcontinental hop-chain.
- **Portal Likelihood**: average fracture + size bonus + keyword density (`portal` / `rift` / `door` / `void`) + **source diversity** + **tight time span** (same 24h is strongest).

All deterministic and fully transparent. Tune `rift/core/detector.py` and `SOURCE_WEIGHT` in `rift/core/events.py`.

## Architecture

```
rift/
├── core/
│   ├── geo.py        # haversine, timestamps, coordinate checks
│   ├── events.py     # Event model, persistence, scoring, corroboration
│   ├── scanner.py    # Web intelligence + local ingest (+ fixture provider)
│   └── detector.py   # Site clustering + portal identification
├── integrations/
│   └── judge.py      # Bridge to Wold Labs Judge
└── web/
    ├── app.py        # Flask factory + API
    └── templates/
        └── index.html
```

## Rift + Judge Workflow (Recommended)

1. Use Rift to aggregate sightings, run web scans, and cluster high-fracture zones on the map.
2. For promising locations, record video, audio, and sensor logs.
3. Analyze the raw media with **Judge** (`python -m judge` or an `AnalysisSession`).
4. Upload the resulting report JSON back into Rift. Judge-detected events appear as map pins with modality tags (slightly offset so stacked pins stay clickable). Provide `default_lat` / `default_lon` if the recordings were not at the New York default.
5. **EXPORT FOR JUDGE** downloads a manifest of what to collect next.

```python
from rift.integrations.judge import import_judge_report, prepare_for_judge
import json

judge_report = json.load(open("judge_report.json"))
rift_events = import_judge_report(judge_report, default_lat=47.66, default_lon=-122.35)

manifest = prepare_for_judge(rift_events)
```

## Future / Roadmap Ideas

- Real-time X / news feed connectors (scanner is already provider-shaped)
- Image upload + visual anomaly hints (tie into Judge)
- Path tracing of moving anomalies
- Multi-user collaborative sessions

## Updates

### 0.2.0

- Portal detection is now a **site**, not a hop-chain: members must sit within the seed radius and a 96-hour window. Likelihood rewards independent sources and same-night convergence.
- Fracture scores match the product claim: internet skepticism discount, plus live **cross-source corroboration** for nearby reports from a different source.
- Judge workflow in the UI actually works: **EXPORT FOR JUDGE** is a real manifest endpoint; Judge reports auto-detect on upload; `judge` is a first-class source filter; stacked Judge pins are nudged so they stay clickable.
- Map tools that serve the mission: fracture **heatmap**, **time window** filter, GeoJSON and **KML** export, portal overlay that clears on re-run.
- Safer ingest (skip bad coordinates, accept session wrappers) and XSS-escaped popups/list items.
- CLI (`python -m rift`, `version`), app factory for tests, expanded pytest suite, GitHub Actions.

### 0.1.0

- Initial public release: map UI, web scan, local ingest, basic clustering, session JSON, Judge helper module.

## License

MIT License. See [LICENSE](LICENSE).

## Acknowledgments

Built by Wold Labs.

Rift stands on the shoulders of OpenStreetMap, Leaflet, Flask, and everyone who has ever looked up and asked "what the hell was that?"

---

**"The map is not the territory. But sometimes the territory leaks."**

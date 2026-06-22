# Rift

**RIFT** — Reality Integrity & Fracture Tracker.

A system that hunts for **portals**, **rifts**, and **abnormal events** bleeding into our reality.

Rift ingests signals from three sources:

- **The Internet** — live scans for reports, eyewitness accounts, news anomalies, fringe logs, and pattern clusters.
- **User Local Data** — your files, logs, sensor dumps, notes, photos descriptions, CSVs of sightings.
- **Interactive World Map** — a fully zoomable, pannable OpenStreetMap-powered canvas where everything materializes as located events.

## Core Features

- **Web Intelligence Scanner**: One-click "Scan the Web". Pulls simulated (and extensible to real) reports of dimensional anomalies, time slips, glowing rifts, vanishing points, sky tears, and high-strangeness clusters. Events auto-geolocated and scored.
- **Local Data Ingestion**: Upload JSON, CSV or plain text. Rift parses locations, descriptions, timestamps and turns them into map-native anomalies.
- **Zoomable Reality Map**: Smooth Leaflet.js map. Click anywhere to add an observation. Color-coded markers by source and anomaly strength. Pan, zoom from street to planet.
- **Portal Detector**: Heuristic + clustering engine. Identifies geographic clusters of high-anomaly events and flags them as **potential portal sites** with confidence.
- **Anomaly Scoring**: Every event receives a 0–100 "Fracture Score" based on linguistic signals ("rift", "portal", "glitch", "void", "time slip"...), cross-source corroboration, and clustering.
- **Session Persistence**: Everything lives in `rift_session.json`. Export, import, share sessions with collaborators.
- **Filters & Exploration**: Filter by source (Internet / Local / User), minimum score, free-text search. Click list items to fly the map to the event.
- **Manual Entry & Map Clicks**: Add observations directly. Perfect for field notes.
- **Export**: Download the current dataset as clean JSON for further analysis or feeding into Judge.

## Why Rift?

Strange things happen. Lights that shouldn't be. People who remember differently. Holes in the sky reported in multiple cities on the same night.

Rift is the instrument that makes the invisible visible — by triangulating the internet's noise, your private data, and geography itself.

## Quick Start

### Prerequisites

- Python 3.10+
- (optional but nice) A modern browser for the map

### Install & Run

```bash
git clone https://github.com/woldlabs/Rift.git
cd Rift

# Create venv
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

python -m rift.web.app
```

The app will start a local Flask server (default http://127.0.0.1:7860). It auto-opens your browser to the map.

On Windows you can also double-click `run-rift.bat` after installing deps (or the script can bootstrap).

## Usage

1. **The Map** loads with sample seed events from past "incidents".
2. Click **SCAN THE WEB** — Rift fabricates (or will fetch) fresh reports from around the globe and drops them on the map.
3. **UPLOAD LOCAL DATA** — Drop a CSV or JSON with your own sightings. Example format below.
4. Click the map to drop a personal observation.
5. Hit **DETECT PORTALS** to run the clustering engine. Red circles + special markers highlight high-likelihood convergence zones.
6. Use the sidebar filters and event list to explore.
7. **EXPORT SESSION** when you're done.

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

### CSV

Columns: `title,lat,lon,description,timestamp,tags` (tags comma-separated)

Plain text uploads are treated as a single user-provided local event (you will be prompted for approx location or it uses a default).

## How Scoring & Portal Detection Works

- **Fracture Score** (0-100): Keyword density + length + source weighting. Internet reports start with a slight skepticism discount.
- **Clustering**: Simple geographic DBSCAN-style grouping (haversine distance). Clusters with 3+ high-scoring events within ~40km get promoted.
- **Portal Likelihood**: Average cluster fracture + size bonus + keyword "portal/rift/door/void" density.

All deterministic and fully transparent. Edit `rift/core/detector.py` to tune.

## Architecture

```
rift/
├── core/
│   ├── events.py     # Event model, persistence, scoring
│   ├── scanner.py    # Web intelligence + local ingest
│   └── detector.py   # Clustering + portal identification
├── integrations/
│   └── judge.py      # Bridge to Wold Labs Judge (import reports, export manifests)
└── web/
    ├── app.py        # Flask API + server
    └── templates/
        └── index.html  # Leaflet map + dark rift UI
```

Extensible: Add real search providers to `scanner.py`. Upload Judge report JSONs — they are auto-converted and placed on the map (you supply the default lat/lon for the media location).

## Rift + Judge Workflow (Recommended)

1. Use Rift to aggregate sightings, run web scans, and visually cluster high-fracture zones on the map.
2. For promising locations, record video, audio, and sensor logs.
3. Analyze the raw media with **Judge** (https://github.com/woldlabs/Judge) for rigorous multimodal anomaly detection.
4. Upload the resulting `demo_report.json` (or your report) back into Rift. Judge-detected events appear as map pins with modality tags and scores.
5. Export a "for Judge" manifest from Rift to document what media to collect.

```python
# Example (after pip install -e ../Judge or from the package)
from rift.integrations.judge import import_judge_report, prepare_for_judge

judge_report = json.load(open("judge_report.json"))
rift_events = import_judge_report(judge_report, default_lat=47.66, default_lon=-122.35)
# ... add to store or map

manifest = prepare_for_judge(your_rift_events)
```

## License

MIT License. See [LICENSE](LICENSE).

## Acknowledgments

Built by Wold Labs.

Rift stands on the shoulders of OpenStreetMap, Leaflet, Flask, and everyone who has ever looked up and asked "what the hell was that?"

---

**"The map is not the territory. But sometimes the territory leaks."**
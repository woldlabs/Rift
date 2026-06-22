"""Flask web application for Rift - the portal & anomaly tracker."""
from __future__ import annotations
import os
import json
import uuid
from flask import Flask, request, jsonify, render_template
from datetime import datetime

from ..core.events import Event, EventStore
from ..core.scanner import WebScanner, LocalIngester
from ..core.detector import PortalDetector
from ..integrations.judge import import_judge_report

app = Flask(__name__, template_folder="templates", static_folder="static")

# Single shared store for the session (in-memory + persisted to CWD)
STORE = EventStore(path="rift_session.json")
SCANNER = WebScanner()
INGESTER = LocalIngester()
DETECTOR = PortalDetector(max_dist_km=45.0, min_events=2, min_avg_score=22.0)

# Seed a few interesting starting events if empty
def _ensure_seed():
    if not STORE.get_all():
        seeds = [
            Event(id="seed-1", title="Pale blue rift above Fremont", description="Multiple reports of a vertical shimmering rift approximately 8 stories tall. Lasted ~6 minutes. No seismic or weather data.", lat=47.66, lon=-122.35, source="internet", timestamp="2026-06-14T03:11:00Z", tags=["visual","internet"], fracture_score=78.0),
            Event(id="seed-1b", title="Companion sighting nearby", description="Another witness ~150m away reported identical column + humming. Same timestamp.", lat=47.659, lon=-122.349, source="internet", timestamp="2026-06-14T03:12:00Z", tags=["visual"], fracture_score=72.0),
            Event(id="seed-2", title="Repeated sky echo", description="Witness heard own voice repeat 4s delayed while looking at clear sky. Recorded on two phones.", lat=34.05, lon=-118.25, source="user", timestamp="2026-06-18T01:40:00Z", tags=["auditory"], fracture_score=64.0),
            Event(id="seed-3", title="Sensor spike + visual distortion", description="Tri-band magnetometer + camera both registered transient at same second. Object appeared briefly in frame then gone.", lat=51.51, lon=-0.12, source="local", timestamp="2026-06-20T22:05:00Z", tags=["sensor","em"], fracture_score=82.0),
            # Extra close high-score for immediate demo portal cluster
            Event(id="seed-1c", title="Third corroborating report", description="Cellphone video of same rift event. Strong portal signature.", lat=47.6585, lon=-122.3485, source="user", timestamp="2026-06-14T03:12:30Z", tags=["video","portal"], fracture_score=88.0),
        ]
        for s in seeds:
            STORE.add(s)

_ensure_seed()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events", methods=["GET"])
def api_events():
    """Return all events (optionally filtered)."""
    source = request.args.get("source")
    min_score = float(request.args.get("min_score", 0))
    q = request.args.get("q", "")
    events = STORE.filter(source=source or None, min_score=min_score, query=q)
    return jsonify({
        "events": [e.to_dict() for e in events],
        "geojson": STORE.to_geojson() if not (source or min_score or q) else {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [e.lon, e.lat]},
                "properties": {
                    "id": e.id, "title": e.title, "description": e.description,
                    "source": e.source, "fracture_score": e.fracture_score,
                    "timestamp": e.timestamp, "tags": e.tags
                }
            } for e in events]
        }
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Perform a web intelligence scan."""
    data = request.get_json(silent=True) or {}
    count = max(3, min(15, int(data.get("count", 6))))
    new_events = SCANNER.scan(count=count)
    added = STORE.add_many(new_events)
    return jsonify({
        "added": len(added),
        "events": [e.to_dict() for e in added]
    })


@app.route("/api/add", methods=["POST"])
def api_add():
    """Manually add a user event (or map click)."""
    data = request.get_json(force=True)
    required = {"title", "lat", "lon"}
    if not required.issubset(set(data.keys())):
        return jsonify({"error": "title, lat, lon required"}), 400

    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon must be valid numbers"}), 400

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"error": "lat must be -90..90, lon must be -180..180"}), 400

    ev = Event(
        id=str(uuid.uuid4()),
        title=str(data["title"])[:120],
        description=str(data.get("description", ""))[:2000],
        lat=round(lat, 6),
        lon=round(lon, 6),
        source=data.get("source", "user"),
        timestamp=data.get("timestamp") or datetime.utcnow().isoformat() + "Z",
        tags=[str(t) for t in data.get("tags", ["user"]) if str(t).strip()],
    )
    if "fracture_score" in data:
        try:
            ev.fracture_score = max(0.0, min(100.0, float(data["fracture_score"])))
        except Exception:
            pass
    added = STORE.add(ev)
    return jsonify({"event": added.to_dict()})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Upload and ingest local data (JSON or CSV)."""
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    raw = f.read()
    fname = (f.filename or "").lower()

    try:
        content = raw.decode("utf-8", errors="ignore")
        parsed = None
        if fname.endswith(".json"):
            try:
                parsed = json.loads(content) if content.strip() else []
            except Exception as je:
                return jsonify({"error": f"invalid json: {je}"}), 400

            # Auto-detect Judge report and convert
            if isinstance(parsed, dict) and ("events" in parsed and "session_id" in parsed or "modality" in str(parsed)[:200]):
                lat = float(request.form.get("default_lat") or request.args.get("default_lat") or 40.71)
                lon = float(request.form.get("default_lon") or request.args.get("default_lon") or -74.0)
                events = import_judge_report(parsed, default_lat=lat, default_lon=lon)
            else:
                events = INGESTER.ingest_json(parsed)
        elif fname.endswith(".csv"):
            events = INGESTER.ingest_csv(content)
        else:
            events = INGESTER.ingest_text(content)
    except Exception as exc:
        return jsonify({"error": f"failed to parse {fname or 'file'}: {exc}"}), 400

    if not events:
        return jsonify({"added": 0, "warning": "no valid events found in file"}), 200

    added = STORE.add_many(events)
    return jsonify({"added": len(added), "events": [e.to_dict() for e in added]})


@app.route("/api/import_judge", methods=["POST"])
def api_import_judge():
    """Upload a Judge report JSON and convert its anomalies into Rift map events.
    Provide optional default_lat / default_lon in form or json.
    """
    if "file" not in request.files:
        # also accept raw json body
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "no file or json body"}), 400
        lat = float(request.args.get("default_lat", 40.71))
        lon = float(request.args.get("default_lon", -74.0))
        try:
            new_evs = import_judge_report(data, default_lat=lat, default_lon=lon)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        added = STORE.add_many(new_evs)
        return jsonify({"added": len(added), "source": "judge", "events": [e.to_dict() for e in added]})

    f = request.files["file"]
    content = f.read()
    lat = float(request.form.get("default_lat") or request.args.get("default_lat") or 40.71)
    lon = float(request.form.get("default_lon") or request.args.get("default_lon") or -74.0)
    try:
        new_evs = import_judge_report(content, default_lat=lat, default_lon=lon)
    except Exception as exc:
        return jsonify({"error": f"failed to import Judge report: {exc}"}), 400

    added = STORE.add_many(new_evs)
    return jsonify({"added": len(added), "source": "judge", "events": [e.to_dict() for e in added]})


@app.route("/api/portals", methods=["GET"])
def api_portals():
    """Run detector and return potential portal clusters."""
    clusters = DETECTOR.find_clusters(STORE.get_all())
    return jsonify({
        "clusters": DETECTOR.as_dicts(clusters),
        "count": len(clusters)
    })


@app.route("/api/clear", methods=["POST"])
def api_clear():
    STORE.clear()
    _ensure_seed()  # always leave a couple seeds
    return jsonify({"status": "cleared", "remaining": len(STORE.get_all())})


@app.route("/api/export", methods=["GET"])
def api_export():
    """Download full session as JSON."""
    data = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "events": [e.to_dict() for e in STORE.get_all()]
    }
    resp = app.response_class(
        response=json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=rift_export.json"}
    )
    return resp


@app.route("/api/stats", methods=["GET"])
def api_stats():
    evs = STORE.get_all()
    if not evs:
        return jsonify({"total": 0})
    by_source = {}
    for e in evs:
        by_source[e.source] = by_source.get(e.source, 0) + 1
    avg = sum(e.fracture_score for e in evs) / len(evs)
    return jsonify({
        "total": len(evs),
        "avg_fracture": round(avg, 1),
        "by_source": by_source,
        "high_score": sum(1 for e in evs if e.fracture_score >= 70)
    })


if __name__ == "__main__":
    port = int(os.environ.get("RIFT_PORT", 7860))
    print(f"\n[RIFT] Starting on http://127.0.0.1:{port}")
    print("[RIFT] Open the URL above in your browser.")
    app.run(host="127.0.0.1", port=port, debug=True)

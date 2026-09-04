"""Flask web application for Rift - the portal & anomaly tracker."""
from __future__ import annotations

import json
import os
import uuid

from flask import Flask, current_app, jsonify, render_template, request

from ..core.detector import PortalDetector
from ..core.events import Event, EventStore
from ..core.geo import utc_now_iso, valid_coords
from ..core.scanner import LocalIngester, make_web_scanner
from ..integrations.judge import import_judge_report, is_judge_report, prepare_for_judge


def _ensure_seed(store: EventStore) -> None:
    if store.get_all():
        return
    seeds = [
        Event(
            id="seed-1",
            title="Pale blue rift above Fremont",
            description="Multiple reports of a vertical shimmering rift approximately 8 stories tall. Lasted ~6 minutes. No seismic or weather data.",
            lat=47.66, lon=-122.35, source="internet",
            timestamp="2026-06-14T03:11:00Z", tags=["visual", "internet"], fracture_score=78.0,
        ),
        Event(
            id="seed-1b",
            title="Companion sighting nearby",
            description="Another witness ~150m away reported identical column + humming. Same timestamp.",
            lat=47.659, lon=-122.349, source="internet",
            timestamp="2026-06-14T03:12:00Z", tags=["visual"], fracture_score=72.0,
        ),
        Event(
            id="seed-2",
            title="Repeated sky echo",
            description="Witness heard own voice repeat 4s delayed while looking at clear sky. Recorded on two phones.",
            lat=34.05, lon=-118.25, source="user",
            timestamp="2026-06-18T01:40:00Z", tags=["auditory"], fracture_score=64.0,
        ),
        Event(
            id="seed-3",
            title="Sensor spike + visual distortion",
            description="Tri-band magnetometer + camera both registered transient at same second. Object appeared briefly in frame then gone.",
            lat=51.51, lon=-0.12, source="local",
            timestamp="2026-06-20T22:05:00Z", tags=["sensor", "em"], fracture_score=82.0,
        ),
        Event(
            id="seed-1c",
            title="Third corroborating report",
            description="Cellphone video of same rift event. Strong portal signature.",
            lat=47.6585, lon=-122.3485, source="user",
            timestamp="2026-06-14T03:12:30Z", tags=["video", "portal"], fracture_score=88.0,
        ),
    ]
    store.add_many(seeds)


def get_store() -> EventStore:
    return current_app.extensions["rift_store"]


def get_scanner():
    return current_app.extensions["rift_scanner"]


def get_ingester() -> LocalIngester:
    return current_app.extensions["rift_ingester"]


def get_detector() -> PortalDetector:
    return current_app.extensions["rift_detector"]


def create_app(store_path: str | None = None, seed: bool = True) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    path = store_path or os.environ.get("RIFT_SESSION", "rift_session.json")
    store = EventStore(path=path)
    app.extensions["rift_store"] = store
    # RIFT_WEB_INTEL=fixture selects checked-in demo/CI replay (no network).
    app.extensions["rift_scanner"] = make_web_scanner()
    app.extensions["rift_ingester"] = LocalIngester()
    app.extensions["rift_detector"] = PortalDetector(
        max_dist_km=45.0, min_events=2, min_avg_score=22.0, time_window_hours=96.0
    )
    if seed:
        _ensure_seed(store)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/events", methods=["GET"])
    def api_events():
        source = request.args.get("source")
        min_score = float(request.args.get("min_score", 0) or 0)
        q = request.args.get("q", "")
        since = request.args.get("since_hours")
        since_hours = float(since) if since not in (None, "", "0") else None
        events = get_store().filter(
            source=source or None, min_score=min_score, query=q, since_hours=since_hours
        )
        return jsonify({
            "events": [e.to_dict() for e in events],
            "geojson": get_store().to_geojson(events),
        })

    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        data = request.get_json(silent=True) or {}
        count = max(3, min(15, int(data.get("count", 6))))
        provider = data.get("provider")
        if provider:
            scanner = make_web_scanner(provider=str(provider))
            used = str(provider).strip().lower()
        else:
            scanner = get_scanner()
            used = (os.environ.get("RIFT_WEB_INTEL") or "simulated").strip().lower()
        new_events = scanner.scan(count=count)
        added = get_store().add_many(new_events)
        return jsonify({
            "added": len(added),
            "provider": used,
            "events": [e.to_dict() for e in added],
        })

    @app.route("/api/add", methods=["POST"])
    def api_add():
        data = request.get_json(force=True) or {}
        required = {"title", "lat", "lon"}
        if not required.issubset(set(data.keys())):
            return jsonify({"error": "title, lat, lon required"}), 400
        try:
            lat = float(data["lat"])
            lon = float(data["lon"])
        except (TypeError, ValueError):
            return jsonify({"error": "lat and lon must be valid numbers"}), 400
        if not valid_coords(lat, lon):
            return jsonify({"error": "lat must be -90..90, lon must be -180..180"}), 400

        ev = Event(
            id=str(uuid.uuid4()),
            title=str(data["title"])[:120],
            description=str(data.get("description", ""))[:2000],
            lat=round(lat, 6),
            lon=round(lon, 6),
            source=data.get("source", "user"),
            timestamp=data.get("timestamp") or utc_now_iso(),
            tags=[str(t) for t in data.get("tags", ["user"]) if str(t).strip()],
        )
        if "fracture_score" in data:
            try:
                ev.fracture_score = max(0.0, min(100.0, float(data["fracture_score"])))
            except (TypeError, ValueError):
                pass
        added = get_store().add(ev)
        return jsonify({"event": added.to_dict()})

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        if "file" not in request.files:
            return jsonify({"error": "no file"}), 400
        f = request.files["file"]
        raw = f.read()
        fname = (f.filename or "").lower()

        try:
            content = raw.decode("utf-8", errors="ignore")
            if fname.endswith(".json"):
                try:
                    parsed = json.loads(content) if content.strip() else []
                except Exception as je:
                    return jsonify({"error": f"invalid json: {je}"}), 400

                if is_judge_report(parsed):
                    lat = float(request.form.get("default_lat") or request.args.get("default_lat") or 40.71)
                    lon = float(request.form.get("default_lon") or request.args.get("default_lon") or -74.0)
                    events = import_judge_report(parsed, default_lat=lat, default_lon=lon)
                else:
                    events = get_ingester().ingest_json(parsed)
            elif fname.endswith(".csv"):
                events = get_ingester().ingest_csv(content)
            else:
                events = get_ingester().ingest_text(content)
        except Exception as exc:
            return jsonify({"error": f"failed to parse {fname or 'file'}: {exc}"}), 400

        if not events:
            return jsonify({"added": 0, "warning": "no valid events found in file"}), 200

        added = get_store().add_many(events)
        return jsonify({"added": len(added), "events": [e.to_dict() for e in added]})

    @app.route("/api/import_judge", methods=["POST"])
    def api_import_judge():
        if "file" not in request.files:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "no file or json body"}), 400
            lat = float(request.args.get("default_lat", 40.71))
            lon = float(request.args.get("default_lon", -74.0))
            try:
                new_evs = import_judge_report(data, default_lat=lat, default_lon=lon)
            except Exception as exc:
                return jsonify({"error": str(exc)}), 400
            added = get_store().add_many(new_evs)
            return jsonify({"added": len(added), "source": "judge", "events": [e.to_dict() for e in added]})

        f = request.files["file"]
        content = f.read()
        lat = float(request.form.get("default_lat") or request.args.get("default_lat") or 40.71)
        lon = float(request.form.get("default_lon") or request.args.get("default_lon") or -74.0)
        try:
            new_evs = import_judge_report(content, default_lat=lat, default_lon=lon)
        except Exception as exc:
            return jsonify({"error": f"failed to import Judge report: {exc}"}), 400

        added = get_store().add_many(new_evs)
        return jsonify({"added": len(added), "source": "judge", "events": [e.to_dict() for e in added]})

    @app.route("/api/judge_manifest", methods=["GET"])
    def api_judge_manifest():
        manifest = prepare_for_judge(get_store().get_all())
        resp = app.response_class(
            response=json.dumps(manifest, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=rift_for_judge.json"},
        )
        return resp

    @app.route("/api/portals", methods=["GET"])
    def api_portals():
        clusters = get_detector().find_clusters(get_store().get_all())
        return jsonify({"clusters": get_detector().as_dicts(clusters), "count": len(clusters)})

    @app.route("/api/clear", methods=["POST"])
    def api_clear():
        get_store().clear()
        _ensure_seed(get_store())
        return jsonify({"status": "cleared", "remaining": len(get_store().get_all())})

    @app.route("/api/export", methods=["GET"])
    def api_export():
        fmt = (request.args.get("format") or "json").lower()
        events = get_store().get_all()
        if fmt in {"geojson", "jsonl"}:
            payload = get_store().to_geojson(events)
            return app.response_class(
                response=json.dumps(payload, indent=2),
                mimetype="application/geo+json",
                headers={"Content-Disposition": "attachment; filename=rift_export.geojson"},
            )
        if fmt == "kml":
            return app.response_class(
                response=get_store().to_kml(events),
                mimetype="application/vnd.google-earth.kml+xml",
                headers={"Content-Disposition": "attachment; filename=rift_export.kml"},
            )
        data = {"exported_at": utc_now_iso(), "events": [e.to_dict() for e in events]}
        return app.response_class(
            response=json.dumps(data, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=rift_export.json"},
        )

    @app.route("/api/stats", methods=["GET"])
    def api_stats():
        evs = get_store().get_all()
        if not evs:
            return jsonify({"total": 0, "avg_fracture": 0, "by_source": {}, "high_score": 0, "portals": 0})
        by_source: dict[str, int] = {}
        for e in evs:
            by_source[e.source] = by_source.get(e.source, 0) + 1
        avg = sum(e.effective_score for e in evs) / len(evs)
        portals = len(get_detector().find_clusters(evs))
        return jsonify({
            "total": len(evs),
            "avg_fracture": round(avg, 1),
            "by_source": by_source,
            "high_score": sum(1 for e in evs if e.effective_score >= 70),
            "portals": portals,
        })

    return app


def main() -> None:
    port = int(os.environ.get("RIFT_PORT", 7860))
    debug = os.environ.get("RIFT_DEBUG", "").lower() in {"1", "true", "yes"}
    url = f"http://127.0.0.1:{port}"
    print(f"\n[RIFT] Starting on {url}")
    print("[RIFT] Open the URL above in your browser.")
    server = create_app()
    if os.environ.get("RIFT_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
        try:
            import threading
            import webbrowser
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    server.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)


def __getattr__(name: str):
    # Lazy default app so `flask --app rift.web.app` works without writing
    # rift_session.json at import time (e.g. during tests).
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    main()

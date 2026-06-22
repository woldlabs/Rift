"""
Integration helpers between Rift and Judge (https://github.com/woldlabs/Judge).

Rift discovers geospatial "where/when" portal and anomaly sightings.
Judge performs deep multimodal analysis on collected video/audio/sensor recordings.

Typical workflow:
1. Use Rift to scan, map, and identify candidate events + locations.
2. Collect corroborating media at those times/locations.
3. Feed media to Judge for rigorous signal detection + report.
4. Optionally import Judge's anomaly results back into Rift map for geo context.
"""
from __future__ import annotations
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..core.events import Event, _score_text


def import_judge_report(
    report: Dict[str, Any] | str | bytes,
    default_lat: float = 40.71,
    default_lon: float = -74.0,
    source_tag: str = "judge",
) -> List[Event]:
    """
    Convert a Judge AnalysisResult (dict or JSON string/bytes) into Rift Events.

    Judge events lack geo info, so a default location is used (or caller can
    post-process). Timestamps from Judge are relative; we attach them in meta.

    Returns list of new Event objects (caller should STORE.add_many).
    """
    if isinstance(report, (str, bytes)):
        data = json.loads(report)
    else:
        data = report

    events: List[Event] = []
    j_events = data.get("events", []) or []

    for je in j_events:
        title = f"[{je.get('modality','?').upper()}] {je.get('description','Judge anomaly')[:80]}"
        desc = je.get("description", "")
        # Attach full Judge details for traceability
        meta = {
            "judge_event_id": je.get("event_id"),
            "modality": je.get("modality"),
            "start_time": je.get("start_time"),
            "duration": je.get("duration"),
            "judge_score": je.get("score"),
            "file_path": je.get("file_path"),
            "geometry": je.get("geometry"),
            "tags_from_judge": je.get("tags", []),
        }

        ev = Event(
            id=f"judge-{je.get('event_id', str(hash(title)))}",
            title=title[:110],
            description=desc,
            lat=default_lat,
            lon=default_lon,
            source=source_tag,
            timestamp=data.get("timestamp") or datetime.utcnow().isoformat() + "Z",
            tags=["judge", je.get("modality", "sensor")],
            fracture_score=max(30.0, min(95.0, float(je.get("score", 40)) * 1.2)),  # lift for visibility
        )
        ev.meta = meta  # attach
        # Re-score using combined text too
        ev.fracture_score = max(ev.fracture_score, _score_text(title + " " + desc))
        events.append(ev)

    return events


def prepare_for_judge(
    rift_events: List[Event],
    suggested_media: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Produce a manifest that helps a user prepare media for Judge analysis.

    Output contains high-interest Rift events + placeholders for the media files
    you should record/attach (video of the event, audio logs, sensor CSVs near
    the location/time).
    """
    manifest = {
        "generated_for": "Judge",
        "rift_events": [],
        "suggested_actions": [],
    }

    for e in sorted(rift_events, key=lambda x: -x.fracture_score)[:20]:
        item = {
            "rift_id": e.id,
            "title": e.title,
            "description": e.description,
            "lat": e.lat,
            "lon": e.lon,
            "fracture_score": e.fracture_score,
            "source": e.source,
            "timestamp": e.timestamp,
            "tags": e.tags,
            "suggested_media": (suggested_media or {}).get(e.id, [
                "video_clip.mp4 or .mov (ideally 30-120s around the event)",
                "audio_recording.wav (nearby mic)",
                "sensor_log.csv (magnetometer / emf / environmental time series)",
            ]),
        }
        manifest["rift_events"].append(item)

    manifest["suggested_actions"] = [
        "Collect synchronized multi-modal recordings at the marked locations/times.",
        "Use Judge GUI or headless AnalysisSession on the collected files.",
        "Import the resulting Judge report JSON back into Rift via Upload (auto-converts).",
    ]
    return manifest


def rift_events_to_judge_manifest(rift_session_path: str = "rift_session.json") -> Dict[str, Any]:
    """Convenience: load a saved Rift session and return a Judge-ready manifest."""
    with open(rift_session_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    evs = [Event.from_dict(e) for e in data.get("events", [])]
    return prepare_for_judge(evs)

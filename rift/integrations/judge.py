"""
Integration helpers between Rift and Judge (https://github.com/woldlabs/Judge).

Rift discovers geospatial "where/when" portal and anomaly sightings.
Judge performs deep multimodal analysis on collected video/audio/sensor recordings.

Typical workflow:
1. Use Rift to scan, map, and identify candidate events + locations.
2. Collect corroborating media at those times/locations.
3. Feed media to Judge for rigorous signal detection + report.
4. Import Judge's anomaly results back onto the Rift map for geo context.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..core.events import Event, score_text
from ..core.geo import utc_now_iso


def is_judge_report(data: Any) -> bool:
    """True if this looks like a Judge AnalysisResult JSON object."""
    if not isinstance(data, dict):
        return False
    events = data.get("events")
    if data.get("session_id") and isinstance(events, list):
        return True
    if isinstance(events, list) and events and isinstance(events[0], dict):
        sample = events[0]
        if "modality" in sample and ("file_path" in sample or "event_id" in sample):
            return True
    return False


def import_judge_report(
    report: Dict[str, Any] | str | bytes,
    default_lat: float = 40.71,
    default_lon: float = -74.0,
    source_tag: str = "judge",
) -> List[Event]:
    """
    Convert a Judge AnalysisResult (dict or JSON string/bytes) into Rift Events.

    Judge events lack geo info, so a default location is used. Multiple events
    at the same default are nudged by a few meters so pins remain clickable.
    """
    if isinstance(report, (str, bytes)):
        data = json.loads(report)
    else:
        data = report

    events: List[Event] = []
    j_events = data.get("events", []) or []

    for i, je in enumerate(j_events):
        if not isinstance(je, dict):
            continue
        modality = str(je.get("modality", "?") or "?")
        raw_desc = str(je.get("description") or "Judge anomaly")
        title = f"[{modality.upper()}] {raw_desc[:80]}"
        meta = {
            "judge_event_id": je.get("event_id"),
            "judge_session_id": data.get("session_id"),
            "modality": je.get("modality"),
            "start_time": je.get("start_time"),
            "duration": je.get("duration"),
            "judge_score": je.get("score"),
            "file_path": je.get("file_path"),
            "geometry": je.get("geometry"),
            "shape_description": je.get("shape_description"),
            "tags_from_judge": je.get("tags", []),
        }

        # Slight offset so stacked Judge pins can be selected independently.
        lat = float(default_lat) + ((i % 5) - 2) * 0.0018
        lon = float(default_lon) + ((i // 5) % 5 - 2) * 0.0018

        try:
            jscore = float(je.get("score", 40) or 40)
        except (TypeError, ValueError):
            jscore = 40.0

        ev = Event(
            id=f"judge-{je.get('event_id', i)}",
            title=title[:110],
            description=raw_desc,
            lat=round(lat, 6),
            lon=round(lon, 6),
            source=source_tag,
            timestamp=data.get("timestamp") or utc_now_iso(),
            tags=["judge", modality],
            fracture_score=max(30.0, min(95.0, jscore * 1.2)),
            meta=meta,
        )
        ev.fracture_score = max(ev.fracture_score, score_text(title + " " + raw_desc))
        events.append(ev)

    return events


def prepare_for_judge(
    rift_events: List[Event],
    suggested_media: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Produce a manifest that helps a user prepare media for Judge analysis.

    High-interest Rift sites first, with placeholders for the video/audio/sensor
    files that should be recorded at those locations/times.
    """
    manifest: Dict[str, Any] = {
        "generated_for": "Judge",
        "generated_at": utc_now_iso(),
        "rift_events": [],
        "suggested_actions": [],
    }

    ranked = sorted(rift_events, key=lambda x: -x.effective_score)[:20]
    for e in ranked:
        item = {
            "rift_id": e.id,
            "title": e.title,
            "description": e.description,
            "lat": e.lat,
            "lon": e.lon,
            "fracture_score": e.fracture_score,
            "effective_score": e.effective_score,
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
        "Use Judge (`python -m judge` or AnalysisSession) on the collected files.",
        "Import the resulting Judge report JSON back into Rift via Upload (auto-converts).",
    ]
    return manifest


def rift_events_to_judge_manifest(rift_session_path: str = "rift_session.json") -> Dict[str, Any]:
    """Convenience: load a saved Rift session and return a Judge-ready manifest."""
    with open(rift_session_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    evs = [Event.from_dict(e) for e in data.get("events", [])]
    return prepare_for_judge(evs)

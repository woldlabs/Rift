"""Event model, persistence, and fracture scoring for Rift."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .geo import haversine, hours_apart, utc_now_iso, valid_coords

# Keywords that raise the "fracture" (anomaly) score
FRACTURE_KEYWORDS = [
    "portal", "rift", "tear", "glitch", "void", "dimension", "dimensional",
    "reality", "slip", "time slip", "vanish", "disappear", "vanished",
    "glow", "glowing", "light", "hole", "sky", "opening", "door", "gate",
    "mirror", "echo", "uap", "ufo", "anomaly", "strange", "unexplained",
    "abnormal", "bleed", "fracture", "shift", "overlap", "merge", "entity",
    "figure", "silhouette", "missing time", "lost time", "witnesses",
]

# Internet reports are noisier than field notes; apply a mild skepticism discount.
SOURCE_WEIGHT = {
    "internet": 0.88,
    "local": 1.0,
    "user": 1.05,
    "judge": 1.08,
}


@dataclass
class Event:
    id: str
    title: str
    description: str
    lat: float
    lon: float
    source: str  # 'internet' | 'local' | 'user' | 'judge'
    timestamp: str
    tags: List[str] = field(default_factory=list)
    fracture_score: float = 0.0  # 0.0 - 100.0  (linguistic + source weight)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def effective_score(self) -> float:
        boost = float((self.meta or {}).get("corroboration_boost", 0.0) or 0.0)
        return round(min(100.0, max(0.0, self.fracture_score + boost)), 1)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["effective_score"] = self.effective_score
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            title=data.get("title") or data.get("name") or "Untitled",
            description=data.get("description", ""),
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            source=data.get("source", "user"),
            timestamp=data.get("timestamp") or utc_now_iso(),
            tags=list(data.get("tags") or []),
            fracture_score=float(data.get("fracture_score", 0.0) or 0.0),
            meta=dict(data.get("meta") or {}),
        )


def score_text(text: str) -> float:
    """Compute a 0-100 fracture score from free text using keyword hits + length."""
    if not text:
        return 5.0
    text_l = text.lower()
    hits = 0.0
    for kw in FRACTURE_KEYWORDS:
        if kw in text_l:
            hits += 1.5 if " " in kw else 1.0
    length_bonus = min(len(text) / 120.0, 12)
    raw = hits * 7.5 + length_bonus
    return round(max(3.0, min(100.0, raw)), 1)


def score_event_text(title: str, description: str, source: str = "user") -> float:
    """Linguistic score adjusted by source reliability."""
    base = score_text(f"{title} {description}")
    weight = SOURCE_WEIGHT.get((source or "user").lower(), 1.0)
    return round(max(3.0, min(100.0, base * weight)), 1)


# Back-compat alias used by scanner / judge
_score_text = score_text


class EventStore:
    """In-memory + file-backed store for Rift events."""

    def __init__(self, path: str = "rift_session.json"):
        self.path = path
        self.events: List[Event] = []
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                loaded = []
                for raw in data.get("events", []):
                    try:
                        ev = Event.from_dict(raw)
                        if valid_coords(ev.lat, ev.lon):
                            loaded.append(ev)
                    except (KeyError, TypeError, ValueError):
                        continue
                self.events = loaded
                self.apply_corroboration(save=False)
            except Exception:
                self.events = []
        else:
            self.events = []

    def save(self) -> None:
        data = {
            "version": 1,
            "saved_at": utc_now_iso(),
            "events": [e.to_dict() for e in self.events],
        }
        parent = os.path.dirname(os.path.abspath(self.path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, event: Event, save: bool = True) -> Event:
        if not event.id:
            event.id = str(uuid.uuid4())
        if event.fracture_score < 1:
            event.fracture_score = score_event_text(event.title, event.description, event.source)
        # replace existing id rather than duplicating
        self.events = [e for e in self.events if e.id != event.id]
        self.events.append(event)
        if save:
            self.apply_corroboration(save=True)
        return event

    def add_many(self, events: List[Event]) -> List[Event]:
        added: List[Event] = []
        for e in events:
            added.append(self.add(e, save=False))
        self.apply_corroboration(save=True)
        return added

    def clear(self) -> None:
        self.events = []
        self.save()

    def get_all(self) -> List[Event]:
        return list(self.events)

    def filter(
        self,
        source: Optional[str] = None,
        min_score: float = 0.0,
        query: str = "",
        since_hours: Optional[float] = None,
    ) -> List[Event]:
        q = query.lower().strip() if query else ""
        out = []
        for e in self.events:
            if source and e.source != source:
                continue
            if e.effective_score < min_score:
                continue
            if since_hours is not None:
                # hours from now; keep events with unparseable timestamps
                age = hours_apart(e.timestamp, utc_now_iso())
                if age > float(since_hours):
                    continue
            if q:
                blob = f"{e.title} {e.description} {' '.join(e.tags)}".lower()
                if q not in blob:
                    continue
            out.append(e)
        return out

    def apply_corroboration(
        self,
        radius_km: float = 48.0,
        window_hours: float = 96.0,
        save: bool = False,
    ) -> None:
        """
        Boost events that are independently reported nearby by a *different* source.

        This is the triangulation the product is built around: internet noise +
        local logs + user/Judge field data at the same place and time.
        """
        for e in self.events:
            others: set[str] = set()
            for o in self.events:
                if o.id == e.id:
                    continue
                if haversine(e.lat, e.lon, o.lat, o.lon) > radius_km:
                    continue
                if hours_apart(e.timestamp, o.timestamp) > window_hours:
                    continue
                if o.source != e.source:
                    others.add(o.source)
            boost = round(min(18.0, 6.0 * len(others)), 1)
            e.meta = dict(e.meta or {})
            e.meta["corroboration_boost"] = boost
            e.meta["corroborating_sources"] = sorted(others)
        if save:
            self.save()

    def to_geojson(self, events: Optional[List[Event]] = None) -> Dict[str, Any]:
        """Return a GeoJSON FeatureCollection for the map / export."""
        features = []
        for e in events if events is not None else self.events:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [e.lon, e.lat],
                },
                "properties": {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "source": e.source,
                    "fracture_score": e.fracture_score,
                    "effective_score": e.effective_score,
                    "timestamp": e.timestamp,
                    "tags": e.tags,
                    "corroboration_boost": (e.meta or {}).get("corroboration_boost", 0),
                },
            })
        return {"type": "FeatureCollection", "features": features}

    def to_kml(self, events: Optional[List[Event]] = None) -> str:
        """KML for Google Earth / field GIS overlays."""
        rows = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<kml xmlns="http://www.opengis.net/kml/2.2">',
                "<Document><name>Rift session</name>"]
        for e in events if events is not None else self.events:
            title = _kml_escape(e.title)
            desc = _kml_escape(
                f"{e.description}\n\nsource={e.source} score={e.effective_score} {e.timestamp}"
            )
            rows.append(
                f"<Placemark><name>{title}</name><description>{desc}</description>"
                f"<Point><coordinates>{e.lon},{e.lat},0</coordinates></Point></Placemark>"
            )
        rows.append("</Document></kml>")
        return "\n".join(rows)


def _kml_escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

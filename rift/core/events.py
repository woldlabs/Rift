"""Event model, persistence, and basic scoring for Rift."""
from __future__ import annotations
import json
import os
import time
import uuid
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Keywords that raise the "fracture" (anomaly) score
FRACTURE_KEYWORDS = [
    "portal", "rift", "tear", "glitch", "void", "dimension", "dimensional",
    "reality", "slip", "time slip", "vanish", "disappear", "vanished",
    "glow", "glowing", "light", "hole", "sky", "opening", "door", "gate",
    "mirror", "echo", "uap", "ufo", "anomaly", "strange", "unexplained",
    "abnormal", "bleed", "fracture", "shift", "overlap", "merge", "entity",
    "figure", "silhouette", "missing time", "lost time", "witnesses"
]


@dataclass
class Event:
    id: str
    title: str
    description: str
    lat: float
    lon: float
    source: str  # 'internet' | 'local' | 'user'
    timestamp: str
    tags: List[str] = field(default_factory=list)
    fracture_score: float = 0.0  # 0.0 - 100.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            title=data["title"],
            description=data.get("description", ""),
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            source=data.get("source", "user"),
            timestamp=data.get("timestamp") or datetime.utcnow().isoformat() + "Z",
            tags=data.get("tags", []),
            fracture_score=float(data.get("fracture_score", 0.0)),
            meta=data.get("meta", {}),
        )


def _score_text(text: str) -> float:
    """Compute a 0-100 fracture score from free text using keyword hits + length."""
    if not text:
        return 5.0
    text_l = text.lower()
    hits = 0
    for kw in FRACTURE_KEYWORDS:
        if kw in text_l:
            hits += 1.5 if " " in kw else 1.0
    # Bonus for longer coherent reports
    length_bonus = min(len(text) / 120.0, 12)
    raw = hits * 7.5 + length_bonus
    score = max(3.0, min(100.0, raw))
    return round(score, 1)


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
                self.events = [Event.from_dict(e) for e in data.get("events", [])]
            except Exception:
                self.events = []
        else:
            self.events = []

    def save(self) -> None:
        data = {
            "version": 1,
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "events": [e.to_dict() for e in self.events],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, event: Event) -> Event:
        if not event.id:
            event.id = str(uuid.uuid4())
        # (re)compute score if not already high
        if event.fracture_score < 1:
            combined = f"{event.title} {event.description}"
            event.fracture_score = _score_text(combined)
        self.events.append(event)
        self.save()
        return event

    def add_many(self, events: List[Event]) -> List[Event]:
        for e in events:
            self.add(e)
        return events

    def clear(self) -> None:
        self.events = []
        self.save()

    def get_all(self) -> List[Event]:
        return list(self.events)

    def filter(self, source: Optional[str] = None, min_score: float = 0.0, query: str = "") -> List[Event]:
        q = query.lower().strip() if query else ""
        out = []
        for e in self.events:
            if source and e.source != source:
                continue
            if e.fracture_score < min_score:
                continue
            if q:
                blob = f"{e.title} {e.description} {' '.join(e.tags)}".lower()
                if q not in blob:
                    continue
            out.append(e)
        return out

    def to_geojson(self) -> Dict[str, Any]:
        """Return simple GeoJSON FeatureCollection for the map."""
        features = []
        for e in self.events:
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
                    "timestamp": e.timestamp,
                    "tags": e.tags,
                }
            })
        return {"type": "FeatureCollection", "features": features}

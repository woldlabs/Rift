"""Web scanner (simulated intelligence feed) + local data ingester for Rift."""
from __future__ import annotations

import csv
import io
import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Protocol

from .events import Event, score_event_text, score_text
from .geo import utc_now_iso, valid_coords

# Plausible locations for "internet" anomalies (lat, lon, place hint)
SEED_LOCATIONS = [
    (47.6062, -122.3321, "Seattle, WA"),
    (34.0522, -118.2437, "Los Angeles, CA"),
    (51.5074, -0.1278, "London, UK"),
    (35.6762, 139.6503, "Tokyo, JP"),
    (-33.8688, 151.2093, "Sydney, AU"),
    (55.7558, 37.6173, "Moscow, RU"),
    (19.4326, -99.1332, "Mexico City, MX"),
    (40.7128, -74.0060, "New York, NY"),
    (1.3521, 103.8198, "Singapore"),
    (-23.5505, -46.6333, "Sao Paulo, BR"),
    (48.8566, 2.3522, "Paris, FR"),
    (31.2304, 121.4737, "Shanghai, CN"),
    (28.6139, 77.2090, "Delhi, IN"),
    (-1.2921, 36.8219, "Nairobi, KE"),
    (64.1466, -21.9426, "Reykjavik, IS"),
]

INTERNET_TEMPLATES = [
    ("Vertical light column reported over {place}", "Eyewitnesses describe a perfectly straight pillar of blue-white light lasting 3-7 minutes. No aircraft or weather explanation. Multiple independent phone videos."),
    ("Sudden time discrepancy cluster in {place}", "Residents report clocks and phones jumping 11-14 minutes simultaneously. Some describe a brief period of 'missing time' and a low hum."),
    ("Circular 'tear' appears in sky above {place}", "A dark circular region ~15-20m across opened for ~90 seconds. Stars visible inside the circle were 'wrong'. Two pilots also reported it."),
    ("Glowing humanoid silhouette vanished into thin air", "Multiple witnesses at {place} saw a tall luminous figure step sideways and disappear. Local wildlife went silent."),
    ("Reality 'echo' recorded on security cams in {place}", "Footage shows the same pedestrian repeating identical path 4 seconds out of sync. Audio track contains reversed speech."),
    ("Portal-like shimmer observed over water near {place}", "A 4m tall rectangular distortion hovering over the surface. Reflected light behaved incorrectly. Lasted 22 minutes."),
    ("Mass 'glitch' event reported downtown {place}", "Hundreds of people simultaneously saw buildings 'flicker' and a brief different skyline. Social media went wild for 11 minutes then posts began disappearing."),
    ("Unexplained gravity anomaly, {place}", "Objects rolled uphill for 40 seconds. Several phones captured it. Seismometers showed nothing."),
    ("Three people independently report same impossible memory at {place}", "They all recall an extra street that has never existed. One produced a hand-drawn map that matches the others exactly."),
    ("Low-frequency 'door slam' heard across city {place}", "A deep concussive sound followed by 8 seconds of complete silence. Reported by thousands. No explosion registered."),
]

_DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "web_intel_reports.json"
)


class WebIntelProvider(Protocol):
    def scan(self, count: int = 7) -> List[Event]: ...


class WebScanner:
    """Generates plausible 'internet-sourced' anomaly events."""

    def __init__(self, rng_seed: int | None = None):
        self.rng = random.Random(rng_seed if rng_seed is not None else int(time.time()))

    def scan(self, count: int = 7) -> List[Event]:
        events: List[Event] = []
        count = max(1, min(30, int(count)))
        for _ in range(count):
            lat, lon, place = self.rng.choice(SEED_LOCATIONS)
            lat += self.rng.uniform(-0.6, 0.6)
            lon += self.rng.uniform(-0.8, 0.8)

            template_title, template_desc = self.rng.choice(INTERNET_TEMPLATES)
            title = template_title.format(place=place)
            desc = template_desc.format(place=place)

            hours_ago = self.rng.randint(1, 72)
            ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")

            tags = ["internet", self.rng.choice(["visual", "auditory", "temporal", "gravitic", "memory", "em"])]

            ev = Event(
                id=str(uuid.uuid4()),
                title=title,
                description=desc,
                lat=round(lat, 4),
                lon=round(lon, 4),
                source="internet",
                timestamp=ts,
                tags=tags,
            )
            # Linguistic score with the internet skepticism discount, then a
            # floor: these templates are curated incident reports, not raw noise.
            ev.fracture_score = max(16.0, min(96.0, score_event_text(title, desc, source="internet")))
            events.append(ev)
        return events


class FixtureWebScanner:
    """Replay checked-in anomaly reports. Demo/CI only — no network I/O."""

    def __init__(self, fixture_path: str | Path | None = None):
        path = Path(fixture_path) if fixture_path else Path(
            os.environ.get("RIFT_WEB_INTEL_FIXTURE", str(_DEFAULT_FIXTURE))
        )
        self.fixture_path = path
        self._events = self._load(path)

    @staticmethod
    def _load(path: Path) -> List[Event]:
        if not path.is_file():
            raise FileNotFoundError(
                f"web-intel fixture not found: {path} "
                "(demo/CI only; run from a Rift checkout or set RIFT_WEB_INTEL_FIXTURE)"
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("events", raw) if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            raise ValueError(f"fixture {path} must be a list or {{events: [...]}}")
        out: List[Event] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                lat = float(item["lat"])
                lon = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if not valid_coords(lat, lon):
                continue
            title = str(item.get("title") or "Fixture internet event")
            desc = str(item.get("description") or "")
            tags = list(item.get("tags") or ["internet", "fixture"])
            if "fixture" not in tags:
                tags.append("fixture")
            if "internet" not in tags:
                tags.append("internet")
            ev = Event(
                id=str(item.get("id") or f"fixture-{uuid.uuid4()}"),
                title=title,
                description=desc,
                lat=lat,
                lon=lon,
                source="internet",
                timestamp=str(item.get("timestamp") or "2026-01-01T00:00:00Z"),
                tags=tags,
                meta={"provider": "fixture", "fixture_path": str(path)},
            )
            if item.get("fracture_score") not in (None, ""):
                try:
                    ev.fracture_score = float(item["fracture_score"])
                except (TypeError, ValueError):
                    ev.fracture_score = max(
                        16.0, min(96.0, score_event_text(title, desc, source="internet"))
                    )
            else:
                ev.fracture_score = max(
                    16.0, min(96.0, score_event_text(title, desc, source="internet"))
                )
            out.append(ev)
        if not out:
            raise ValueError(f"fixture {path} produced zero valid events")
        return out

    def scan(self, count: int = 7) -> List[Event]:
        count = max(1, min(30, int(count)))
        # Deterministic slice; no shuffle, no network.
        return list(self._events[: min(count, len(self._events))])


def make_web_scanner(
    provider: str | None = None,
    *,
    rng_seed: int | None = None,
    fixture_path: str | Path | None = None,
) -> WebIntelProvider:
    """Select web-intel backend: simulated (default) or fixture (demo/CI)."""
    name = (provider or os.environ.get("RIFT_WEB_INTEL") or "simulated").strip().lower()
    if name in {"fixture", "fixtures"}:
        return FixtureWebScanner(fixture_path=fixture_path)
    return WebScanner(rng_seed=rng_seed)


class LocalIngester:
    """Parses user-provided local data into Events."""

    def ingest_json(self, payload: str | bytes | list | dict) -> List[Event]:
        if isinstance(payload, (str, bytes)):
            data = json.loads(payload)
        else:
            data = payload

        if isinstance(data, dict):
            if isinstance(data.get("events"), list):
                data = data["events"]
            elif isinstance(data.get("data"), list):
                data = data["data"]
            else:
                data = [data]

        out: List[Event] = []
        if not isinstance(data, list):
            return out
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                lat = float(item.get("lat", item.get("latitude")))
                lon = float(item.get("lon", item.get("longitude", item.get("lng"))))
            except (TypeError, ValueError):
                continue
            if not valid_coords(lat, lon):
                continue
            title = item.get("title") or item.get("name") or "Untitled local event"
            desc = item.get("description", item.get("desc", ""))
            source = item.get("source") or "local"
            ev = Event(
                id=item.get("id") or str(uuid.uuid4()),
                title=str(title),
                description=str(desc),
                lat=lat,
                lon=lon,
                source=source if source in {"internet", "local", "user", "judge"} else "local",
                timestamp=item.get("timestamp") or utc_now_iso(),
                tags=list(item.get("tags") or ["local"]),
                meta=dict(item.get("meta") or {}),
            )
            if item.get("fracture_score") not in (None, ""):
                try:
                    ev.fracture_score = float(item["fracture_score"])
                except (TypeError, ValueError):
                    ev.fracture_score = score_event_text(ev.title, ev.description, ev.source)
            else:
                ev.fracture_score = score_event_text(ev.title, ev.description, ev.source)
            out.append(ev)
        return out

    def ingest_csv(self, text: str) -> List[Event]:
        out: List[Event] = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                lat = float(row.get("lat") or row.get("latitude"))
                lon = float(row.get("lon") or row.get("longitude") or row.get("lng"))
            except (TypeError, ValueError):
                continue
            if not valid_coords(lat, lon):
                continue
            title = row.get("title") or row.get("name") or "Local observation"
            desc = row.get("description") or row.get("desc") or row.get("notes") or ""
            tags_raw = row.get("tags", "")
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else ["local"]
            ts = row.get("timestamp") or utc_now_iso()
            ev = Event(
                id=str(uuid.uuid4()),
                title=title,
                description=desc,
                lat=lat,
                lon=lon,
                source="local",
                timestamp=ts,
                tags=tags,
            )
            ev.fracture_score = score_event_text(title, desc, "local")
            out.append(ev)
        return out

    def ingest_text(self, text: str, default_lat: float = 40.7, default_lon: float = -74.0) -> List[Event]:
        """Treat whole text blob as a single user-provided local event."""
        if not valid_coords(default_lat, default_lon):
            default_lat, default_lon = 40.7, -74.0
        title = (text.strip().split("\n")[0] if text.strip() else "User note")[:80]
        ev = Event(
            id=str(uuid.uuid4()),
            title=title or "User note",
            description=text.strip(),
            lat=default_lat,
            lon=default_lon,
            source="local",
            timestamp=utc_now_iso(),
            tags=["text-note"],
        )
        ev.fracture_score = score_text(text)
        return [ev]

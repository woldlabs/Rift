"""Web scanner (simulated intelligence feed) + local data ingester for Rift."""
from __future__ import annotations
import json
import random
import csv
import io
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .events import Event, _score_text

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

LOCAL_TEMPLATES = [
    ("Field log: anomalous reading", "Sensor logged a 47-second spike across all EM bands coinciding with visual distortion reported by observer."),
    ("Notebook entry: repeating lights", "Same pattern of 3 short + 2 long flashes at 02:17 for three consecutive nights. No known aircraft schedule."),
    ("Audio log fragment", "Low pulsing tone increasing in pitch then abrupt cut to silence. Captured on phone mic at 03:41."),
]


class WebScanner:
    """Generates plausible 'internet-sourced' anomaly events."""

    def __init__(self, rng_seed: int | None = None):
        self.rng = random.Random(rng_seed or int(time.time()))

    def scan(self, count: int = 7) -> List[Event]:
        events: List[Event] = []
        used = set()
        for _ in range(count):
            lat, lon, place = self.rng.choice(SEED_LOCATIONS)
            # slight jitter so they don't stack exactly
            lat += self.rng.uniform(-0.6, 0.6)
            lon += self.rng.uniform(-0.8, 0.8)

            template_title, template_desc = self.rng.choice(INTERNET_TEMPLATES)
            title = template_title.format(place=place)
            desc = template_desc.format(place=place)

            # random recent time
            hours_ago = self.rng.randint(1, 72)
            ts = (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat() + "Z"

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
            # Force a re-score based on text (usually high for these)
            ev.fracture_score = _score_text(title + " " + desc) * self.rng.uniform(0.85, 1.05)
            ev.fracture_score = round(max(18, min(96, ev.fracture_score)), 1)
            events.append(ev)
        return events


class LocalIngester:
    """Parses user-provided local data into Events."""

    def ingest_json(self, payload: str | bytes | list) -> List[Event]:
        if isinstance(payload, (str, bytes)):
            data = json.loads(payload)
        else:
            data = payload
        out = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ev = Event(
                id=item.get("id") or str(uuid.uuid4()),
                title=item.get("title") or item.get("name") or "Untitled local event",
                description=item.get("description", item.get("desc", "")),
                lat=float(item["lat"]),
                lon=float(item["lon"]),
                source="local",
                timestamp=item.get("timestamp") or datetime.utcnow().isoformat() + "Z",
                tags=item.get("tags", []),
            )
            ev.fracture_score = float(item.get("fracture_score") or _score_text(ev.title + " " + ev.description))
            out.append(ev)
        return out

    def ingest_csv(self, text: str) -> List[Event]:
        out = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                lat = float(row.get("lat") or row.get("latitude"))
                lon = float(row.get("lon") or row.get("longitude") or row.get("lng"))
            except Exception:
                continue
            title = row.get("title") or row.get("name") or "Local observation"
            desc = row.get("description") or row.get("desc") or row.get("notes") or ""
            tags_raw = row.get("tags", "")
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else ["local"]
            ts = row.get("timestamp") or datetime.utcnow().isoformat() + "Z"
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
            ev.fracture_score = _score_text(f"{title} {desc}")
            out.append(ev)
        return out

    def ingest_text(self, text: str, default_lat: float = 40.7, default_lon: float = -74.0) -> List[Event]:
        """Treat whole text blob as a single user-provided local event."""
        title = text.strip().split("\n")[0][:80] or "User note"
        ev = Event(
            id=str(uuid.uuid4()),
            title=title,
            description=text.strip(),
            lat=default_lat,
            lon=default_lon,
            source="local",
            timestamp=datetime.utcnow().isoformat() + "Z",
            tags=["text-note"],
        )
        ev.fracture_score = _score_text(text)
        return [ev]

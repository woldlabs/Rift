"""Portal and cluster detection for Rift.

A portal is a *place* — a tight geographic site where independent reports
converge in space and time — not a chain of stepping-stone links that can
walk across a continent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .events import Event
from .geo import haversine, hours_apart, parse_ts


@dataclass
class Cluster:
    events: List[Event]
    center_lat: float
    center_lon: float
    radius_km: float
    avg_score: float
    portal_likelihood: float  # 0-100
    sources: List[str]
    time_span_hours: float


class PortalDetector:
    """
    Seed-and-gather clustering around high-scoring events.

    Every member of a cluster must lie within `max_dist_km` of the seed
    (the highest-scoring remaining event) *and* within `time_window_hours`
    of that seed. This matches the operational question: "is there a rift
    *here*, around this time?" rather than "can I hop 42 km repeatedly?"
    """

    def __init__(
        self,
        max_dist_km: float = 42.0,
        min_events: int = 2,
        min_avg_score: float = 22.0,
        time_window_hours: float = 96.0,
    ):
        self.max_dist_km = max_dist_km
        self.min_events = min_events
        self.min_avg_score = min_avg_score
        self.time_window_hours = time_window_hours

    def _effective(self, ev: Event) -> float:
        return float(getattr(ev, "effective_score", ev.fracture_score))

    def find_clusters(self, events: List[Event]) -> List[Cluster]:
        candidates = [e for e in events if self._effective(e) >= self.min_avg_score]
        if len(candidates) < self.min_events:
            return []

        remaining = sorted(candidates, key=self._effective, reverse=True)
        raw_clusters: List[List[Event]] = []

        while remaining:
            seed = remaining[0]
            members = [
                e
                for e in remaining
                if haversine(seed.lat, seed.lon, e.lat, e.lon) <= self.max_dist_km
                and hours_apart(seed.timestamp, e.timestamp) <= self.time_window_hours
            ]
            if len(members) >= self.min_events:
                raw_clusters.append(members)
                member_ids = {e.id for e in members}
                remaining = [e for e in remaining if e.id not in member_ids]
            else:
                remaining = remaining[1:]

        result: List[Cluster] = []
        for cl in raw_clusters:
            lats = [ev.lat for ev in cl]
            lons = [ev.lon for ev in cl]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

            max_r = 0.0
            for ev in cl:
                d = haversine(center_lat, center_lon, ev.lat, ev.lon)
                if d > max_r:
                    max_r = d

            scores = [self._effective(ev) for ev in cl]
            avg_score = sum(scores) / len(scores)
            sources = sorted({ev.source for ev in cl})

            times = [parse_ts(ev.timestamp) for ev in cl]
            known = [t for t in times if t is not None]
            if len(known) >= 2:
                span = (max(known) - min(known)).total_seconds() / 3600.0
            else:
                span = 0.0

            size_bonus = min(len(cl) * 6.5, 26)
            score_bonus = (avg_score - 25) * 0.8
            keyword_boost = 0.0
            for ev in cl:
                blob = (ev.title + " " + ev.description).lower()
                if any(k in blob for k in ("portal", "rift", "tear", "door", "void", "gate")):
                    keyword_boost += 7.5

            # Independent sources at the same site are the whole point of Rift.
            source_bonus = min(24.0, (len(sources) - 1) * 10.0)
            # Same-night / tight-window convergence is stronger evidence.
            if span <= 24:
                time_bonus = 12.0
            elif span <= 72:
                time_bonus = 6.0
            else:
                time_bonus = 0.0

            likelihood = max(
                15.0,
                min(
                    96.0,
                    avg_score * 0.50
                    + size_bonus
                    + score_bonus * 0.5
                    + keyword_boost
                    + source_bonus
                    + time_bonus,
                ),
            )

            result.append(
                Cluster(
                    events=cl,
                    center_lat=round(center_lat, 4),
                    center_lon=round(center_lon, 4),
                    radius_km=round(max_r, 1) or 5.0,
                    avg_score=round(avg_score, 1),
                    portal_likelihood=round(likelihood, 1),
                    sources=sources,
                    time_span_hours=round(span, 2),
                )
            )
        result.sort(key=lambda c: c.portal_likelihood, reverse=True)
        return result

    def as_dicts(self, clusters: List[Cluster]) -> List[Dict[str, Any]]:
        return [
            {
                "center": [c.center_lat, c.center_lon],
                "radius_km": c.radius_km,
                "num_events": len(c.events),
                "avg_fracture": c.avg_score,
                "portal_likelihood": c.portal_likelihood,
                "event_ids": [e.id for e in c.events],
                "sources": c.sources,
                "time_span_hours": c.time_span_hours,
                "summary": (
                    f"Cluster of {len(c.events)} events from {', '.join(c.sources) or 'unknown'}; "
                    f"avg fracture {c.avg_score}; span {c.time_span_hours:.1f}h; "
                    f"portal likelihood {c.portal_likelihood}%"
                ),
            }
            for c in clusters
        ]

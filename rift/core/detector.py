"""Portal and cluster detection for Rift."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Dict, Any

from .events import Event


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometers between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@dataclass
class Cluster:
    events: List[Event]
    center_lat: float
    center_lon: float
    radius_km: float
    avg_score: float
    portal_likelihood: float   # 0-100


class PortalDetector:
    """
    Simple geographic clustering detector.

    Groups nearby high-scoring events and computes a portal likelihood.
    """

    def __init__(self, max_dist_km: float = 42.0, min_events: int = 2, min_avg_score: float = 22.0):
        self.max_dist_km = max_dist_km
        self.min_events = min_events
        self.min_avg_score = min_avg_score

    def find_clusters(self, events: List[Event]) -> List[Cluster]:
        if len(events) < self.min_events:
            return []

        # Build adjacency: indices of events within distance (full connected components)
        n = len(events)
        adj = [[] for _ in range(n)]
        for i in range(n):
            if events[i].fracture_score < self.min_avg_score:
                continue
            for j in range(i + 1, n):
                if events[j].fracture_score < self.min_avg_score:
                    continue
                if haversine(events[i].lat, events[i].lon, events[j].lat, events[j].lon) <= self.max_dist_km:
                    adj[i].append(j)
                    adj[j].append(i)

        # DFS / flood fill for components
        visited = [False] * n
        raw_clusters: List[List[Event]] = []

        def dfs(start: int, comp: List[int]):
            stack = [start]
            visited[start] = True
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in adj[u]:
                    if not visited[v]:
                        visited[v] = True
                        stack.append(v)

        for i in range(n):
            if not visited[i] and events[i].fracture_score >= self.min_avg_score:
                comp_idx: List[int] = []
                dfs(i, comp_idx)
                if len(comp_idx) >= self.min_events:
                    raw_clusters.append([events[k] for k in comp_idx])

        result = []
        for cl in raw_clusters:
            lats = [ev.lat for ev in cl]
            lons = [ev.lon for ev in cl]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

            # crude radius
            max_r = 0.0
            for ev in cl:
                d = haversine(center_lat, center_lon, ev.lat, ev.lon)
                if d > max_r:
                    max_r = d

            avg_score = sum(ev.fracture_score for ev in cl) / len(cl)

            # Portal likelihood formula
            size_bonus = min(len(cl) * 6.5, 26)
            score_bonus = (avg_score - 25) * 0.8
            keyword_boost = 0
            for ev in cl:
                blob = (ev.title + " " + ev.description).lower()
                if any(k in blob for k in ("portal", "rift", "tear", "door", "void", "gate")):
                    keyword_boost += 7.5
            likelihood = max(15.0, min(96.0, avg_score * 0.55 + size_bonus + score_bonus * 0.6 + keyword_boost))
            likelihood = round(likelihood, 1)

            result.append(Cluster(
                events=cl,
                center_lat=round(center_lat, 4),
                center_lon=round(center_lon, 4),
                radius_km=round(max_r, 1) or 5.0,
                avg_score=round(avg_score, 1),
                portal_likelihood=likelihood,
            ))
        # sort best first
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
                "summary": f"Cluster of {len(c.events)} events, avg fracture {c.avg_score}, portal likelihood {c.portal_likelihood}%"
            }
            for c in clusters
        ]

from rift.core.detector import PortalDetector
from rift.core.events import Event


def _ev(eid, lat, lon, score, source="user", ts="2026-06-14T03:11:00Z", title="sighting"):
    return Event(
        id=eid, title=title, description="portal rift tear",
        lat=lat, lon=lon, source=source, timestamp=ts,
        tags=["t"], fracture_score=score,
    )


def test_seattle_seeds_form_a_portal_site():
    events = [
        _ev("a", 47.66, -122.35, 78, "internet"),
        _ev("b", 47.659, -122.349, 72, "internet"),
        _ev("c", 47.6585, -122.3485, 88, "user"),
    ]
    det = PortalDetector(max_dist_km=45, min_events=2, min_avg_score=22)
    clusters = det.find_clusters(events)
    assert len(clusters) == 1
    assert len(clusters[0].events) == 3
    assert "internet" in clusters[0].sources and "user" in clusters[0].sources
    assert clusters[0].portal_likelihood >= 45
    d = det.as_dicts(clusters)[0]
    assert d["num_events"] == 3
    assert "sources" in d


def test_no_transcontinental_chain():
    """A 40 km stepping-stone chain must not become one mega-portal."""
    events = [
        _ev("ny", 40.71, -74.00, 90, "internet"),
        _ev("mid1", 40.71, -73.55, 40, "internet"),  # ~38 km east
        _ev("mid2", 40.71, -73.10, 40, "internet"),
        _ev("mid3", 40.71, -72.65, 40, "internet"),
        _ev("london", 51.51, -0.12, 80, "local", ts="2026-06-20T22:05:00Z"),
    ]
    det = PortalDetector(max_dist_km=45, min_events=2, min_avg_score=22)
    clusters = det.find_clusters(events)
    for cl in clusters:
        ids = {e.id for e in cl.events}
        assert not ("ny" in ids and "london" in ids)
        assert not ("ny" in ids and "mid3" in ids)


def test_temporal_window_splits_same_place():
    events = [
        _ev("now", 47.66, -122.35, 80, "user", ts="2026-06-14T03:00:00Z"),
        _ev("old", 47.66, -122.35, 80, "local", ts="2026-01-01T03:00:00Z"),
    ]
    det = PortalDetector(max_dist_km=45, min_events=2, min_avg_score=22, time_window_hours=96)
    clusters = det.find_clusters(events)
    assert clusters == []

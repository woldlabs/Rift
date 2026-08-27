from rift.core.events import Event, EventStore, score_event_text, score_text


def test_internet_skepticism_discount():
    text_title = "Portal rift tear in the sky"
    text_desc = "Witnesses saw a glowing void door"
    internet = score_event_text(text_title, text_desc, "internet")
    local = score_event_text(text_title, text_desc, "local")
    assert internet < local


def test_corroboration_boosts_cross_source(tmp_path):
    store = EventStore(path=str(tmp_path / "s.json"))
    store.add(Event(
        id="i", title="rift", description="portal",
        lat=47.66, lon=-122.35, source="internet",
        timestamp="2026-06-14T03:11:00Z", tags=[], fracture_score=70,
    ), save=False)
    store.add(Event(
        id="u", title="same rift", description="portal",
        lat=47.661, lon=-122.351, source="user",
        timestamp="2026-06-14T03:20:00Z", tags=[], fracture_score=70,
    ), save=True)
    by_id = {e.id: e for e in store.get_all()}
    assert by_id["i"].meta["corroboration_boost"] >= 6
    assert "user" in by_id["i"].meta["corroborating_sources"]
    assert by_id["i"].effective_score > by_id["i"].fracture_score


def test_add_many_dedupes_ids(tmp_path):
    store = EventStore(path=str(tmp_path / "s.json"))
    a = Event(id="x", title="a", description="", lat=1, lon=1, source="user",
              timestamp="2026-01-01T00:00:00Z", tags=[], fracture_score=10)
    b = Event(id="x", title="b", description="", lat=2, lon=2, source="user",
              timestamp="2026-01-01T00:00:00Z", tags=[], fracture_score=10)
    store.add_many([a, b])
    assert len(store.get_all()) == 1
    assert store.get_all()[0].title == "b"


def test_score_text_keywords():
    low = score_text("weather was fine")
    high = score_text("a glowing portal rift opened in the sky with missing time")
    assert high > low

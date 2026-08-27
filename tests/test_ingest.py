from rift.core.scanner import LocalIngester, WebScanner


def test_ingest_json_list_and_session_wrapper():
    ing = LocalIngester()
    raw = [
        {"title": "A", "lat": 47.6, "lon": -122.3, "description": "portal"},
        {"title": "bad", "lat": "nope", "lon": 1},
        {"title": "oob", "lat": 200, "lon": 0},
    ]
    evs = ing.ingest_json(raw)
    assert len(evs) == 1
    assert evs[0].source == "local"

    wrapped = {"version": 1, "events": raw}
    evs2 = ing.ingest_json(wrapped)
    assert len(evs2) == 1


def test_ingest_csv_lat_aliases():
    ing = LocalIngester()
    csv = "title,latitude,longitude,description\nGlow,34.05,-118.25,rift in the sky\n"
    evs = ing.ingest_csv(csv)
    assert len(evs) == 1
    assert evs[0].lat == 34.05


def test_web_scan_deterministic_seed():
    a = WebScanner(rng_seed=1).scan(count=4)
    b = WebScanner(rng_seed=1).scan(count=4)
    assert [e.title for e in a] == [e.title for e in b]
    assert all(e.source == "internet" for e in a)
    assert all(16 <= e.fracture_score <= 100 for e in a)

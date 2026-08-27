import io
import json

import pytest

from rift.web.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(store_path=str(tmp_path / "session.json"), seed=True)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"RIFT" in res.data


def test_seeded_events_and_portals(client):
    res = client.get("/api/events")
    data = res.get_json()
    assert len(data["events"]) >= 5
    geo = data["geojson"]
    assert geo["type"] == "FeatureCollection"

    portals = client.get("/api/portals").get_json()
    assert portals["count"] >= 1
    assert portals["clusters"][0]["portal_likelihood"] > 0
    assert "sources" in portals["clusters"][0]


def test_add_scan_export(client):
    bad = client.post("/api/add", json={"title": "x", "lat": 200, "lon": 0})
    assert bad.status_code == 400

    ok = client.post("/api/add", json={
        "title": "Field note portal",
        "description": "glowing rift",
        "lat": 47.66,
        "lon": -122.35,
        "source": "user",
    })
    assert ok.status_code == 200
    assert ok.get_json()["event"]["id"]

    scan = client.post("/api/scan", json={"count": 3})
    assert scan.get_json()["added"] == 3

    exp = client.get("/api/export")
    payload = json.loads(exp.data)
    assert "events" in payload

    kml = client.get("/api/export?format=kml")
    assert b"<kml" in kml.data

    geo = client.get("/api/export?format=geojson")
    assert json.loads(geo.data)["type"] == "FeatureCollection"

    man = client.get("/api/judge_manifest")
    body = json.loads(man.data)
    assert body["generated_for"] == "Judge"


def test_upload_local_json(client):
    data = json.dumps([
        {"title": "Hiker", "lat": 48.85, "lon": 2.35, "description": "stone arch vanished"}
    ]).encode()
    res = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(data), "sightings.json")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    assert res.get_json()["added"] == 1


def test_upload_judge_report(client):
    report = {
        "session_id": "abc",
        "events": [
            {"event_id": "j1", "modality": "video", "description": "flow spike", "score": 9, "file_path": "a.mp4"}
        ],
    }
    raw = json.dumps(report).encode()
    res = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(raw), "demo_report.json")},
        content_type="multipart/form-data",
    )
    body = res.get_json()
    assert body["added"] == 1
    assert body["events"][0]["source"] == "judge"


def test_stats_and_clear(client):
    stats = client.get("/api/stats").get_json()
    assert stats["total"] >= 5
    assert "by_source" in stats
    cleared = client.post("/api/clear").get_json()
    assert cleared["remaining"] >= 1

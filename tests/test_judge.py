from rift.integrations.judge import import_judge_report, is_judge_report, prepare_for_judge
from rift.core.events import Event


def test_is_judge_report():
    assert is_judge_report({"session_id": "abc", "events": []})
    assert is_judge_report({"events": [{"modality": "video", "file_path": "a.mp4", "event_id": "1"}]})
    assert not is_judge_report([{"lat": 1, "lon": 2, "title": "x"}])
    assert not is_judge_report({"events": [{"lat": 1, "lon": 2, "title": "x"}]})


def test_import_judge_report_offsets_pins():
    report = {
        "session_id": "s1",
        "timestamp": "2026-06-22T00:00:00Z",
        "events": [
            {"event_id": "e1", "modality": "video", "description": "kinematic transient", "score": 8.0, "file_path": "a.mp4"},
            {"event_id": "e2", "modality": "audio", "description": "acoustic spike", "score": 12.0, "file_path": "b.wav"},
        ],
    }
    evs = import_judge_report(report, default_lat=47.66, default_lon=-122.35)
    assert len(evs) == 2
    assert all(e.source == "judge" for e in evs)
    assert evs[0].lat != evs[1].lat or evs[0].lon != evs[1].lon
    assert evs[0].meta["judge_session_id"] == "s1"


def test_prepare_for_judge_ranks_by_score():
    evs = [
        Event(id="low", title="n", description="", lat=1, lon=1, source="user",
              timestamp="2026-01-01T00:00:00Z", tags=[], fracture_score=10),
        Event(id="high", title="portal", description="rift", lat=2, lon=2, source="user",
              timestamp="2026-01-01T00:00:00Z", tags=[], fracture_score=90),
    ]
    man = prepare_for_judge(evs)
    assert man["generated_for"] == "Judge"
    assert man["rift_events"][0]["rift_id"] == "high"
    assert "suggested_media" in man["rift_events"][0]

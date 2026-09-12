"""Fixture web-intel provider — deterministic replay, no network."""
from pathlib import Path

from rift.core.scanner import FixtureWebScanner, make_web_scanner

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "web_intel_reports.json"


def test_fixture_scan_deterministic():
    a = FixtureWebScanner(fixture_path=FIXTURE).scan(count=5)
    b = FixtureWebScanner(fixture_path=FIXTURE).scan(count=5)
    assert [e.id for e in a] == [e.id for e in b]
    assert [e.title for e in a] == [e.title for e in b]
    assert all(e.source == "internet" for e in a)
    assert all("fixture" in e.tags for e in a)
    assert all(16 <= e.fracture_score <= 100 for e in a)


def test_fixture_scan_respects_count():
    sc = FixtureWebScanner(fixture_path=FIXTURE)
    assert len(sc.scan(count=2)) == 2
    assert len(sc.scan(count=99)) == 5  # fixture length


def test_make_web_scanner_fixture_env(monkeypatch):
    monkeypatch.setenv("RIFT_WEB_INTEL", "fixture")
    monkeypatch.setenv("RIFT_WEB_INTEL_FIXTURE", str(FIXTURE))
    sc = make_web_scanner()
    assert isinstance(sc, FixtureWebScanner)
    evs = sc.scan(count=3)
    assert len(evs) == 3
    assert evs[0].id == "fixture-seattle-rift"


def test_make_web_scanner_default_simulated(monkeypatch):
    monkeypatch.delenv("RIFT_WEB_INTEL", raising=False)
    sc = make_web_scanner(rng_seed=1)
    from rift.core.scanner import WebScanner

    assert isinstance(sc, WebScanner)


def test_missing_fixture_is_explicit(tmp_path):
    missing = tmp_path / "nope.json"
    try:
        FixtureWebScanner(fixture_path=missing)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as exc:
        assert "RIFT_WEB_INTEL_FIXTURE" in str(exc)

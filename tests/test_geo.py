from rift.core.geo import haversine, hours_apart, parse_ts, valid_coords


def test_haversine_known_distance():
    # Seattle to roughly nearby Fremont is small
    d = haversine(47.66, -122.35, 47.659, -122.349)
    assert d < 1.0
    # Seattle to London is thousands of km
    d2 = haversine(47.6062, -122.3321, 51.5074, -0.1278)
    assert d2 > 7000


def test_valid_coords():
    assert valid_coords(0, 0)
    assert valid_coords(90, 180)
    assert not valid_coords(91, 0)
    assert not valid_coords(0, 181)
    assert not valid_coords("x", 0)


def test_hours_apart_and_parse():
    a = "2026-06-14T03:11:00Z"
    b = "2026-06-14T15:11:00Z"
    assert abs(hours_apart(a, b) - 12) < 0.01
    assert parse_ts("not-a-date") is None
    assert hours_apart("bad", b) == 0.0

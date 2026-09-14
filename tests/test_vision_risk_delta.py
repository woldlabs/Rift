import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "rift_vision_risk_delta",
    Path(__file__).resolve().parents[1] / "scripts" / "vision_risk_delta.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_mod)
map_paths = _mod.map_paths
render_comment = _mod.render_comment


def test_maps_core_and_bridge_paths():
    mapped = map_paths(
        [
            "rift/core/detector.py",
            "rift/integrations/judge.py",
            "docs/QUICKSTART.md",
            "LICENSE",
        ]
    )
    themes = {row["theme"] for row in mapped["themes"]}
    assert "Architecture boundaries" in themes
    assert any("Judge" in t for t in themes)
    assert "Success metrics (docs / operator path)" in themes
    assert "LICENSE" in mapped["unmatched"]
    assert "needs-vision-review" in mapped["labels"]


def test_comment_uses_absolute_vision_links():
    mapped = map_paths(["VISION.md"])
    body = render_comment(mapped)
    assert "<!-- rift-vision-risk-delta -->" in body
    assert "https://github.com/woldlabs/Rift/blob/main/VISION.md" in body
    assert "https://github.com/woldlabs/Rift/blob/main/docs/TRIAGE.md" in body

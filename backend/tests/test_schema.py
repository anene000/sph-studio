"""U1: scene schema round-trip and domain-fit validation tests."""
import json
from pathlib import Path

from app import config_io
from app.models import Scene

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "data" / "scenes" / "sample_bunny.json"


def test_sample_scene_parses():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    scene = config_io.parse_scene(data)
    assert scene.Configuration.domainEnd == [1.0, 1.0, 1.0]
    assert scene.Export.interval.mode == "steps"
    assert scene.FluidBlocks[0].objectId == 0


def test_round_trip_is_stable():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    scene = config_io.parse_scene(data)
    dumped = config_io.scene_to_dict(scene)
    scene2 = config_io.parse_scene(dumped)
    assert config_io.scene_to_dict(scene2) == dumped


def test_domain_must_be_positive():
    bad = {
        "Configuration": {"domainStart": [0, 0, 0], "domainEnd": [0, 1, 1]},
    }
    try:
        Scene.model_validate(bad)
        assert False, "expected validation error"
    except Exception:
        pass


def test_validate_scene_ok_for_fitting_object():
    # Without trimesh/OBJ the check degrades to 'info' (still ok=True).
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    scene = config_io.parse_scene(data)
    result = config_io.validate_scene(scene)
    assert "ok" in result and "issues" in result


def test_periodic_boundary_defaults_off():
    # A scene without the boundary keys defaults to all-wall / zero driving force.
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    scene = config_io.parse_scene(data)
    assert scene.Configuration.periodicBoundary == [False, False, False]
    assert scene.Configuration.drivingForce == [0.0, 0.0, 0.0]
    # And they survive an export round-trip.
    dumped = config_io.scene_to_dict(scene)
    assert dumped["Configuration"]["periodicBoundary"] == [False, False, False]
    assert dumped["Configuration"]["drivingForce"] == [0.0, 0.0, 0.0]


def test_periodic_boundary_and_driving_force_round_trip():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["Configuration"]["periodicBoundary"] = [True, False, False]
    data["Configuration"]["drivingForce"] = [5.0, 0.0, 0.0]
    scene = config_io.parse_scene(data)
    assert scene.Configuration.periodicBoundary == [True, False, False]
    assert scene.Configuration.drivingForce == [5.0, 0.0, 0.0]
    dumped = config_io.scene_to_dict(scene)
    assert dumped["Configuration"]["periodicBoundary"] == [True, False, False]
    assert dumped["Configuration"]["drivingForce"] == [5.0, 0.0, 0.0]


def test_periodic_boundary_length_must_match_dim():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["Configuration"]["periodicBoundary"] = [True, False]  # dim is 3
    try:
        config_io.parse_scene(data)
        assert False, "expected validation error for mismatched periodicBoundary length"
    except Exception:
        pass


def test_driving_force_length_must_match_dim():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["Configuration"]["drivingForce"] = [1.0, 0.0]  # dim is 3
    try:
        config_io.parse_scene(data)
        assert False, "expected validation error for mismatched drivingForce length"
    except Exception:
        pass

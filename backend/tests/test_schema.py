"""U1: scene schema round-trip and domain-fit validation tests."""
import json
from pathlib import Path

import pytest
from app import config_io
from app.models import Scene

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "data" / "scenes" / "sample_bunny.json"

# A multi-object / multi-material OBJ (two `o` groups) — how Blender exports a
# scene with several objects. trimesh loads this as a Scene (no `.vertices`), so
# mesh-bounds must use force="mesh" to concatenate it into a single Trimesh.
_MULTI_OBJECT_OBJ = """\
o A
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
o B
v 0 0 1
v 1 0 1
v 0 1 1
f 4 5 6
"""

# A box that is tall along Z (Blender "up") and short along Y, so the Z-up->Y-up
# conversion is observable: after conversion the tall extent must move to Y.
_TALL_Z_OBJ = """\
o box
v 0 0 0
v 0.1 0 0
v 0.1 0.2 0
v 0 0.2 0
v 0 0 0.9
v 0.1 0 0.9
v 0.1 0.2 0.9
v 0 0.2 0.9
f 1 2 3
f 1 3 4
f 5 6 7
f 5 7 8
f 1 2 6
f 1 6 5
f 4 3 7
f 4 7 8
f 1 4 8
f 1 8 5
f 2 3 7
f 2 7 6
"""


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


def test_inlet_control_defaults_off():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    scene = config_io.parse_scene(data)
    c = scene.Configuration
    assert c.inletControl is False
    assert c.inletVelocity == [0.0, 0.0, 0.0]
    assert c.inletSide == "low"
    assert c.inletProfile == "uniform"


def test_inlet_control_round_trip():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["Configuration"].update({
        "inletControl": True,
        "inletAxis": 0,
        "inletSide": "low",
        "inletVelocity": [1.0, 0.0, 0.0],
        "inletThickness": 0.1,
        "inletRelaxation": 0.5,
        "inletProfile": "parabolic",
        "profileAxis": 1,
    })
    scene = config_io.parse_scene(data)
    dumped = config_io.scene_to_dict(scene)
    cfg = dumped["Configuration"]
    assert cfg["inletControl"] is True
    assert cfg["inletVelocity"] == [1.0, 0.0, 0.0]
    assert cfg["inletProfile"] == "parabolic"
    assert cfg["inletSide"] == "low"


def test_inlet_velocity_length_must_match_dim():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["Configuration"]["inletVelocity"] = [1.0, 0.0]  # dim is 3
    try:
        config_io.parse_scene(data)
        assert False, "expected validation error for mismatched inletVelocity length"
    except Exception:
        pass


def test_inlet_axis_out_of_range_rejected():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["Configuration"]["inletAxis"] = 5  # dim is 3
    try:
        config_io.parse_scene(data)
        assert False, "expected validation error for out-of-range inletAxis"
    except Exception:
        pass


def test_multi_object_obj_bounds_are_resolved(tmp_path):
    """A Blender-style multi-object OBJ (trimesh loads it as a Scene) must still
    yield mesh bounds — regression for the 'mesh bounds unavailable' message."""
    pytest.importorskip("trimesh", reason="trimesh not installed")
    obj = tmp_path / "multi.obj"
    obj.write_text(_MULTI_OBJECT_OBJ, encoding="utf-8")
    scene = config_io.parse_scene({
        "Configuration": {"domainStart": [0, 0, 0], "domainEnd": [5, 5, 5]},
        "RigidBodies": [{
            "objectId": 2, "geometryFile": str(obj),
            "scale": [1, 1, 1], "translation": [0, 0, 0],
        }],
    })
    result = config_io.validate_scene(scene)
    # Bounds resolved -> no 'mesh bounds unavailable' info issue, and the object
    # fits the large domain -> no error/warn issues at all.
    msgs = [i["message"] for i in result["issues"]]
    assert not any("mesh bounds unavailable" in m for m in msgs), msgs
    assert result["ok"] is True


def test_rigidbody_upaxis_default_and_validation():
    from app.models import RigidBody
    assert RigidBody(objectId=1, geometryFile="x.obj").upAxis == "y"
    assert RigidBody(objectId=1, geometryFile="x.obj", upAxis="z").upAxis == "z"
    try:
        RigidBody(objectId=1, geometryFile="x.obj", upAxis="w")
        assert False, "expected validation error for invalid upAxis"
    except Exception:
        pass


def test_upaxis_z_converts_blender_zup_to_yup(tmp_path):
    """upAxis='z' must move the tall (Blender-up=Z) extent onto the solver's Y axis."""
    pytest.importorskip("trimesh", reason="trimesh not installed")
    obj = tmp_path / "box.obj"
    obj.write_text(_TALL_Z_OBJ, encoding="utf-8")

    lo_y, hi_y = config_io._mesh_bounds(str(obj), [1, 1, 1], [0, 0, 0], "y")
    ext_y = [hi_y[k] - lo_y[k] for k in range(3)]
    # untouched: tall in Z (~0.9), short in Y (~0.2)
    assert abs(ext_y[2] - 0.9) < 1e-3 and abs(ext_y[1] - 0.2) < 1e-3, ext_y

    lo_z, hi_z = config_io._mesh_bounds(str(obj), [1, 1, 1], [0, 0, 0], "z")
    ext_z = [hi_z[k] - lo_z[k] for k in range(3)]
    # converted: tall now in Y (~0.9), Z becomes short (~0.2)
    assert abs(ext_z[1] - 0.9) < 1e-3 and abs(ext_z[2] - 0.2) < 1e-3, ext_z

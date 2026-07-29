"""U16: every bundled sample scene parses via the schema and passes fit validation.

Runs without Taichi (schema + optional trimesh only), so it is safe for CI.
"""
import json
from pathlib import Path

import pytest

from app import config_io

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENES = sorted((REPO_ROOT / "data" / "scenes").glob("sample_*.json"))


def test_samples_exist():
    assert SCENES, "no sample_*.json scenes found"


@pytest.mark.parametrize("path", SCENES, ids=[p.name for p in SCENES])
def test_sample_parses_and_validates(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    scene = config_io.parse_scene(data)

    # Object ids must be unique across the union of fluid + rigid objects.
    ids = (
        [b.objectId for b in scene.FluidBlocks]
        + [b.objectId for b in scene.RigidBlocks]
        + [r.objectId for r in scene.RigidBodies]
    )
    assert len(ids) == len(set(ids)), f"duplicate objectId in {path.name}: {ids}"

    # Field-physics keys present after normalization.
    assert scene.Configuration.viscosity is not None
    assert scene.Configuration.surfaceTension is not None

    # Fit validation must not report an error-level issue (objects fit the domain).
    result = config_io.validate_scene(scene)
    errors = [i for i in result["issues"] if i["level"] == "error"]
    assert not errors, f"{path.name} has fit errors: {errors}"

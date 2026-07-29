"""Config import/export and domain-fit validation helpers.

``validate_scene`` re-implements the same geometry check the solver performs
(``ParticleSystem._check_object_fits_domain``) so the GUI can warn and recommend a
scale BEFORE a job is launched, without importing Taichi. Mesh bounds are read with
trimesh when available; otherwise the check is skipped gracefully.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import Scene

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFETY = 0.98


def parse_scene(data: dict) -> Scene:
    """Validate a raw dict into a Scene (raises pydantic ValidationError on failure)."""
    return Scene.model_validate(data)


def scene_to_dict(scene: Scene) -> dict:
    return scene.model_dump(mode="json", exclude_none=True)


def _mesh_bounds(geometry_file: str, scale, translation):
    """Return (world_min, world_max) after scale+translation, or None if unavailable."""
    try:
        import numpy as np
        import trimesh as tm
    except Exception:
        return None
    path = Path(geometry_file)
    if not path.is_absolute():
        path = REPO_ROOT / geometry_file
    if not path.exists():
        return None
    try:
        mesh = tm.load(str(path))
        mesh.apply_scale(scale)
        verts = np.asarray(mesh.vertices) + np.asarray(translation)
        return verts.min(axis=0), verts.max(axis=0)
    except Exception:
        return None


def validate_scene(scene: Scene) -> dict:
    """Return {"ok": bool, "issues": [...]} where each issue may carry a recommended scale."""
    import numpy as np

    cfg = scene.Configuration
    domain_start = np.asarray(cfg.domainStart, dtype=float)
    domain_end = np.asarray(cfg.domainEnd, dtype=float)
    domain_size = domain_end - domain_start

    issues = []
    for rb in scene.RigidBodies:
        bounds = _mesh_bounds(rb.geometryFile, rb.scale, rb.translation)
        if bounds is None:
            issues.append({
                "objectId": rb.objectId, "level": "info",
                "message": f"mesh bounds unavailable (trimesh/OBJ not found): {rb.geometryFile}",
            })
            continue
        world_min, world_max = bounds
        extent = world_max - world_min
        over_low = domain_start - world_min
        over_high = world_max - domain_end
        if not (np.any(over_low > 1e-9) or np.any(over_high > 1e-9)):
            continue  # fits
        cur_scale = np.asarray(rb.scale, dtype=float)
        safe_extent = np.where(extent > 1e-12, extent, np.inf)
        axis_ratio = domain_size / safe_extent
        if np.any(axis_ratio < 1.0):
            k_uniform = SAFETY * float(np.min(axis_ratio))
            per_axis_k = np.minimum(1.0, SAFETY * axis_ratio)
            issues.append({
                "objectId": rb.objectId, "level": "error",
                "message": "object size exceeds analysis space",
                "recommendedScaleUniform": (cur_scale * k_uniform).round(6).tolist(),
                "recommendedScalePerAxis": (cur_scale * per_axis_k).round(6).tolist(),
                "objectSize": extent.round(4).tolist(),
                "domainSize": domain_size.round(4).tolist(),
            })
        else:
            issues.append({
                "objectId": rb.objectId, "level": "warn",
                "message": "object fits by size but protrudes due to translation; adjust translation",
            })

    ok = not any(i["level"] == "error" for i in issues)
    return {"ok": ok, "issues": issues}


def load_scene_file(path: str) -> Scene:
    import json
    return parse_scene(json.loads(Path(path).read_text(encoding="utf-8")))

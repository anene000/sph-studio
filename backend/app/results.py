"""Results access: frame index, per-frame particle positions (for 3D playback),
and a zip bundle of all CSV files for download."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Optional


def frames_index(output_dir: str) -> dict:
    p = Path(output_dir) / "frames.json"
    if not p.exists():
        return {"frames": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _read_csv_points(path: Path) -> list:
    """Read x,y,z columns from a CSV frame (skips the leading '# simTime' comment)."""
    pts = []
    if not path.exists():
        return pts
    with path.open(encoding="utf-8") as f:
        header = None
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if header is None:
                header = line.split(",")
                try:
                    xi, yi, zi = header.index("x"), header.index("y"), header.index("z")
                except ValueError:
                    return pts
                continue
            cols = line.split(",")
            pts.append([float(cols[xi]), float(cols[yi]), float(cols[zi])])
    return pts


def frame_points(output_dir: str, frame: int) -> dict:
    """Aggregate fluid + object points for a given frame (for the 3D player)."""
    idx = frames_index(output_dir)
    entry = next((f for f in idx.get("frames", []) if f.get("frame") == frame), None)
    out = {"frame": frame, "fluid": [], "objects": {}}
    if not entry:
        return out
    base = Path(output_dir)
    for oid, meta in (entry.get("fluid") or {}).items():
        out["fluid"] += _read_csv_points(base / meta["file"])
    for oid, meta in (entry.get("objects") or {}).items():
        out["objects"][oid] = _read_csv_points(base / meta["file"])
    return out


def bundle_zip(output_dir: str) -> bytes:
    """Zip every CSV frame + frames.json + scene.json for download."""
    base = Path(output_dir)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.glob("*.csv")):
            z.write(p, p.name)
        for extra in ("frames.json", "scene.json"):
            fp = base / extra
            if fp.exists():
                z.write(fp, extra)
    return buf.getvalue()

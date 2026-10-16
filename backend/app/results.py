"""Results access: frame index, per-frame particle positions (for 3D playback),
and a zip bundle of all CSV files for download."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path


def frames_index(output_dir: str) -> dict:
    p = Path(output_dir) / "frames.json"
    if not p.exists():
        return {"frames": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path):
    """Read x,y,z and optional pressure / speed (|v|) from a CSV frame.
    Returns (positions, pressures, speeds); scalar lists are empty when their
    columns are absent."""
    pos, pressure, speed = [], [], []
    if not path.exists():
        return pos, pressure, speed
    with path.open(encoding="utf-8") as f:
        header = None
        xi = yi = zi = pi = vxi = vyi = vzi = None
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if header is None:
                header = line.split(",")
                try:
                    xi, yi, zi = header.index("x"), header.index("y"), header.index("z")
                except ValueError:
                    return pos, pressure, speed
                pi = header.index("pressure") if "pressure" in header else None
                if "vx" in header and "vy" in header and "vz" in header:
                    vxi, vyi, vzi = header.index("vx"), header.index("vy"), header.index("vz")
                continue
            cols = line.split(",")
            pos.append([float(cols[xi]), float(cols[yi]), float(cols[zi])])
            if pi is not None:
                pressure.append(float(cols[pi]))
            if vxi is not None:
                speed.append((float(cols[vxi]) ** 2 + float(cols[vyi]) ** 2 + float(cols[vzi]) ** 2) ** 0.5)
    return pos, pressure, speed


def _read_csv_points(path: Path) -> list:
    """Positions only (used for rigid objects)."""
    return _read_csv_rows(path)[0]


def frame_points(output_dir: str, frame: int) -> dict:
    """Aggregate fluid + object points for a given frame (for the 3D player).
    Fluid carries optional per-particle scalars (pressure, speed) for colormaps."""
    idx = frames_index(output_dir)
    entry = next((f for f in idx.get("frames", []) if f.get("frame") == frame), None)
    out = {"frame": frame, "fluid": [], "objects": {}, "fluidPressure": [], "fluidSpeed": []}
    if not entry:
        return out
    base = Path(output_dir)
    for _oid, meta in (entry.get("fluid") or {}).items():
        pos, pr, sp = _read_csv_rows(base / meta["file"])
        out["fluid"] += pos
        out["fluidPressure"] += pr
        out["fluidSpeed"] += sp
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

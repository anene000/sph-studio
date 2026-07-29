"""U16: end-to-end new-calculation flow (②→⑥ → CSV) using the real solver.

Skipped automatically when Taichi is not importable (e.g. CI without the solver
runtime). Locally, run inside the project venv with the solver deps installed:

    SPH_ARCH=cpu .venv/Scripts/python -m pytest backend/tests/test_e2e.py -q
"""
import csv
import io
import json
import os
import time
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("taichi", reason="solver runtime (taichi) not installed")

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "data" / "scenes" / "sample_bunny.json"


def _wait_done(client, job_id, timeout=180):
    deadline = time.time() + timeout
    status = "queued"
    while time.time() < deadline:
        status = client.get(f"/api/jobs/{job_id}").json()["status"]
        if status in ("completed", "failed", "canceled"):
            return status
        time.sleep(1)
    return status


def test_new_calculation_flow_produces_separate_csv():
    os.environ["SPH_ARCH"] = "cpu"  # force CPU so the subprocess runs headless anywhere
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    scene = json.loads(SAMPLE.read_text(encoding="utf-8"))
    scene["Configuration"]["totalTime"] = 0.02  # ~50 steps, fast

    # ① import/validate → ⑤ create job (auto-writes scene.json)
    assert client.post("/api/config/validate", json=scene).json()["ok"] is True
    created = client.post("/api/jobs", json=scene)
    assert created.status_code == 200, created.text
    job_id = created.json()["id"]

    # ⑥ wait for completion
    status = _wait_done(client, job_id)
    assert status == "completed", client.get(f"/api/jobs/{job_id}").json()

    out_dir = Path(client.get(f"/api/jobs/{job_id}").json()["outputDir"])
    assert (out_dir / "scene.json").exists(), "scene.json was not auto-generated"

    # frames + per-frame points
    frames = client.get(f"/api/jobs/{job_id}/frames").json()["frames"]
    assert len(frames) >= 2
    pts = client.get(f"/api/jobs/{job_id}/frames/0").json()
    assert len(pts["fluid"]) > 0, "no fluid particles exported"
    assert sum(len(v) for v in pts["objects"].values()) > 0, "no object particles exported"

    # fluid and object CSV are produced separately
    fluid_csvs = list(out_dir.glob("fluid_*.csv"))
    object_csvs = list(out_dir.glob("object_*.csv"))
    assert fluid_csvs, "no fluid_*.csv"
    assert object_csvs, "no object_*.csv (rigid tracking missing)"

    # fluid actually moved under gravity (time-series motion)
    last_fluid = sorted(fluid_csvs)[-1]
    rows = [
        r
        for r in csv.reader(last_fluid.open(encoding="utf-8"))
        if r and not r[0].startswith("#") and r[0] != "particle_id"
    ]
    max_speed = max(abs(float(r[5])) for r in rows)  # |vy|
    assert max_speed > 0.0, "fluid did not move"

    # zip download bundles the CSV + scene.json
    dl = client.get(f"/api/jobs/{job_id}/download")
    assert dl.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(dl.content)).namelist()
    assert any(n.startswith("fluid_") for n in names)
    assert any(n.startswith("object_") for n in names)
    assert "scene.json" in names

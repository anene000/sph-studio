"""Non-functional performance/load benchmark (P1, P2, P4, P5).

Run inside the project venv:
    SPH_ARCH=cpu .venv/Scripts/python scripts/benchmark.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "solver" / "run_headless.py"
os.environ.setdefault("SPH_ARCH", "cpu")


def base_scene(particle_radius, total_steps, interval=25):
    return {
        "Configuration": {
            "domainStart": [0, 0, 0], "domainEnd": [1, 1, 0.5],
            "particleRadius": particle_radius, "simulationMethod": 0,
            "timeStepSize": 4e-4, "gravitation": [0, -9.81, 0], "density0": 1000,
            "stiffness": 50000, "exponent": 7, "viscosity": 0.02, "surfaceTension": 0.01,
            "boundaryHandlingMethod": 0, "enforceDomainFit": True, "totalSteps": total_steps,
        },
        "FluidBlocks": [{
            "objectId": 0, "start": [0, 0, 0], "end": [0.5, 0.6, 0.5],
            "translation": [0.05, 0.3, 0.0], "scale": [1, 1, 1], "velocity": [0, 0, 0],
            "density": 1000.0, "color": [50, 100, 200],
        }],
        "Export": {"outputDir": "", "interval": {"mode": "steps", "value": interval},
                   "fluid": {"enabled": True, "objectIds": [0], "fields": ["position", "velocity"], "format": "csv"},
                   "objects": []},
    }


def run_one(scene, out_dir):
    scene["Export"]["outputDir"] = str(out_dir)
    sf = out_dir / "scene.json"
    sf.write_text(json.dumps(scene), encoding="utf-8")
    t0 = time.time()
    p = subprocess.run([sys.executable, str(SOLVER), "--scene_file", str(sf), "--output_dir", str(out_dir)],
                       capture_output=True, text=True, cwd=str(ROOT))
    wall = time.time() - t0
    last, frames = None, 0
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "progress":
            last = ev
        elif ev.get("type") == "frame":
            frames += 1
    return last, frames, wall, p.returncode


def bench_throughput():
    print("\n== P1 Solver throughput (steps/sec vs particle count) ==")
    print(f"{'radius':>8} {'particles':>10} {'steps':>6} {'wall(s)':>8} {'steps/s':>8}")
    with tempfile.TemporaryDirectory() as tmp:
        for r in (0.03, 0.02, 0.015):
            steps = 100
            d = Path(tmp) / f"r{r}"
            d.mkdir()
            last, frames, wall, code = run_one(base_scene(r, steps), d)
            pn = last["particleNum"] if last else -1
            sps = steps / wall if wall else 0
            print(f"{r:>8} {pn:>10} {steps:>6} {wall:>8.2f} {sps:>8.1f}  (frames={frames}, rc={code})")


def bench_api_and_concurrency():
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)

    print("\n== P2 API latency (single call) ==")
    for name, fn in [
        ("health", lambda: c.get("/api/health")),
        ("info", lambda: c.get("/api/info")),
        ("validate", lambda: c.post("/api/config/validate", json=base_scene(0.03, 10))),
    ]:
        t0 = time.time()
        r = fn()
        dt = (time.time() - t0) * 1000
        print(f"  {name:>10}: {r.status_code}  {dt:.1f} ms")

    print("\n== P4/P5 Concurrency (2 jobs) + frame count ==")
    scene = base_scene(0.03, 50, interval=25)  # expect frames at 0,25,50 -> 3
    ids = []
    for _ in range(2):
        r = c.post("/api/jobs", json=scene)
        ids.append(r.json()["id"])
    deadline = time.time() + 120
    done = {}
    while time.time() < deadline and len(done) < 2:
        for jid in ids:
            if jid in done:
                continue
            st = c.get(f"/api/jobs/{jid}").json()["status"]
            if st in ("completed", "failed", "canceled"):
                done[jid] = st
        time.sleep(1)
    for jid in ids:
        frames = c.get(f"/api/jobs/{jid}/frames").json().get("frames", [])
        print(f"  job {jid}: {done.get(jid, 'timeout')}  frames={len(frames)}")


if __name__ == "__main__":
    bench_throughput()
    bench_api_and_concurrency()
    print("\nbenchmark done.")

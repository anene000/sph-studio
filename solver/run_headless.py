"""Headless SPH runner for SPH Studio.

Runs the Taichi SPH solver WITHOUT any GGUI/Vulkan window, streaming progress as
JSON Lines to stdout and writing per-frame CSV (and optional PLY/OBJ) according to
the scene's ``Export`` section.

Usage:
    python solver/run_headless.py --scene_file scene.json --output_dir outputs/job

Progress line format (stdout, one JSON per line):
    {"type":"progress","step":N,"totalSteps":M,"simTime":t,"totalTime":T,
     "elapsed":s,"eta":s,"particleNum":P}
    {"type":"frame","frame":k,"simTime":t}
    {"type":"done","frames":k}
    {"type":"error","message":"..."}

This script only depends on the solver package (taichi, numpy, trimesh); it does
NOT import ``taichi.ui``.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import taichi as ti


# Keep a handle to the *real* stdout: it is reserved exclusively for JSON Lines.
# In main() we redirect sys.stdout -> sys.stderr so any print()/Taichi banner from
# the solver goes to stderr, leaving stdout a clean, parseable JSONL stream.
_REAL_STDOUT = sys.stdout


def emit(obj):
    """Write one JSON Lines record to the real stdout and flush (consumed by the backend)."""
    _REAL_STDOUT.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _REAL_STDOUT.flush()


def init_taichi():
    """Init Taichi, honouring SPH_ARCH env; fall back to CPU when GPU is unavailable."""
    arch_env = os.environ.get("SPH_ARCH", "").lower()
    if arch_env == "cpu":
        ti.init(arch=ti.cpu)
        return "cpu"
    try:
        ti.init(arch=ti.vulkan, device_memory_fraction=0.5)
        return "vulkan"
    except Exception as e:  # pragma: no cover - depends on runtime GPU
        emit({"type": "log", "message": f"Vulkan init failed ({e}); falling back to CPU."})
        ti.init(arch=ti.cpu)
        return "cpu"


def resolve_total_steps(config):
    """Return the total number of solver steps from totalSteps or totalTime/dt."""
    cfg = config.config["Configuration"]
    dt = float(cfg["timeStepSize"])
    if cfg.get("totalSteps"):
        return int(cfg["totalSteps"]), dt
    total_time = float(cfg.get("totalTime", 5.0))
    return int(round(total_time / dt)), dt


def get_export(config):
    """Return the Export section with sensible defaults."""
    export = config.config.get("Export", {}) or {}
    interval = export.get("interval", {}) or {}
    mode = interval.get("mode", "steps")
    value = interval.get("value", 40)
    fluid = export.get("fluid", {}) or {}
    objects = export.get("objects", []) or []
    return {
        "interval_mode": mode,
        "interval_value": value,
        "fluid_enabled": fluid.get("enabled", True),
        "fluid_object_ids": fluid.get("objectIds"),  # None => all fluid objects
        "fluid_fields": fluid.get("fields", ["position", "velocity", "density", "pressure"]),
        "objects": objects,
        "ply": export.get("ply", False),
        "obj": export.get("obj", False),
    }


def _snapshot(ps):
    """Read the live particle arrays into numpy once for the current frame."""
    n = ps.particle_num[None]
    return {
        "object_id": ps.object_id.to_numpy()[:n],
        "material": ps.material.to_numpy()[:n],
        "x": ps.x.to_numpy()[:n],
        "v": ps.v.to_numpy()[:n],
        "density": ps.density.to_numpy()[:n],
        "pressure": ps.pressure.to_numpy()[:n],
    }


def _write_fluid_csv(path, snap, obj_id, fields, sim_time):
    mask = (snap["object_id"] == obj_id) & (snap["material"] == 1)
    idx = np.nonzero(mask)[0]
    cols = ["particle_id"]
    if "position" in fields:
        cols += ["x", "y", "z"]
    if "velocity" in fields:
        cols += ["vx", "vy", "vz"]
    if "density" in fields:
        cols += ["density"]
    if "pressure" in fields:
        cols += ["pressure"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("# simTime=%g\n" % sim_time)
        f.write(",".join(cols) + "\n")
        for i in idx:
            row = [str(int(i))]
            if "position" in fields:
                row += ["%.6g" % v for v in snap["x"][i]]
            if "velocity" in fields:
                row += ["%.6g" % v for v in snap["v"][i]]
            if "density" in fields:
                row += ["%.6g" % snap["density"][i]]
            if "pressure" in fields:
                row += ["%.6g" % snap["pressure"][i]]
            f.write(",".join(row) + "\n")
    return int(idx.size)


def _write_object_csv(path, ps, snap, obj_spec, sim_time):
    obj_id = obj_spec["objectId"]
    mode = obj_spec.get("mode", "particles")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# simTime=%g\n" % sim_time)
        if mode == "meshVertices" and obj_id in ps.object_collection \
                and "mesh" in ps.object_collection[obj_id]:
            # Rest mesh vertices (exact for static bodies; approximate for dynamic).
            verts = np.asarray(ps.object_collection[obj_id]["mesh"].vertices)
            f.write("vertex_id,x,y,z\n")
            for i, p in enumerate(verts):
                f.write("%d,%.6g,%.6g,%.6g\n" % (i, p[0], p[1], p[2]))
            return int(verts.shape[0])
        # Default: rigid particle positions tracked live.
        mask = (snap["object_id"] == obj_id) & (snap["material"] == 0)
        idx = np.nonzero(mask)[0]
        f.write("particle_id,x,y,z\n")
        for i in idx:
            p = snap["x"][i]
            f.write("%d,%.6g,%.6g,%.6g\n" % (int(i), p[0], p[1], p[2]))
        return int(idx.size)


def run(scene_file, output_dir):
    # Import here so Taichi is initialised before the data-oriented classes load.
    from config_builder import SimConfig
    from particle_system import ParticleSystem

    os.makedirs(output_dir, exist_ok=True)
    config = SimConfig(scene_file_path=scene_file)
    total_steps, dt = resolve_total_steps(config)
    exp = get_export(config)

    ps = ParticleSystem(config, GGUI=False)
    solver = ps.build_solver()
    solver.initialize()

    # Which fluid object ids to export (default: every FluidBlock in the config).
    fluid_ids = exp["fluid_object_ids"]
    if fluid_ids is None:
        fluid_ids = [b["objectId"] for b in config.get_fluid_blocks()]

    frames_index = []
    frame = 0
    start = time.time()
    last_emit = 0.0

    def do_export(step, sim_time):
        nonlocal frame
        snap = _snapshot(ps)
        produced = {"fluid": {}, "objects": {}}
        if exp["fluid_enabled"]:
            for oid in fluid_ids:
                fname = "fluid_%d_%06d.csv" % (oid, frame)
                cnt = _write_fluid_csv(os.path.join(output_dir, fname), snap, oid,
                                       exp["fluid_fields"], sim_time)
                produced["fluid"][oid] = {"file": fname, "count": cnt}
        for obj_spec in exp["objects"]:
            oid = obj_spec["objectId"]
            fname = "object_%d_%06d.csv" % (oid, frame)
            cnt = _write_object_csv(os.path.join(output_dir, fname), ps, snap, obj_spec, sim_time)
            produced["objects"][oid] = {"file": fname, "count": cnt}
        frames_index.append({"frame": frame, "simTime": sim_time, "step": step, **produced})
        emit({"type": "frame", "frame": frame, "simTime": sim_time})
        frame += 1

    def is_export_step(step, sim_time):
        if exp["interval_mode"] == "time":
            iv = float(exp["interval_value"])
            return int(sim_time / iv) > (len(frames_index) - 1)
        return step % int(exp["interval_value"]) == 0

    # Export initial state (frame 0).
    do_export(0, 0.0)

    for step in range(1, total_steps + 1):
        solver.step()
        sim_time = step * dt
        if is_export_step(step, sim_time):
            do_export(step, sim_time)

        now = time.time()
        if now - last_emit > 0.2 or step == total_steps:
            elapsed = now - start
            eta = (elapsed / step) * (total_steps - step) if step else 0.0
            emit({
                "type": "progress", "step": step, "totalSteps": total_steps,
                "simTime": sim_time, "totalTime": total_steps * dt,
                "elapsed": round(elapsed, 3), "eta": round(eta, 3),
                "particleNum": int(ps.particle_num[None]),
            })
            last_emit = now

    with open(os.path.join(output_dir, "frames.json"), "w", encoding="utf-8") as f:
        json.dump({"frames": frames_index, "dt": dt, "totalSteps": total_steps}, f,
                  ensure_ascii=False, indent=2)
    emit({"type": "done", "frames": frame})


def main():
    parser = argparse.ArgumentParser(description="Headless SPH runner (SPH Studio)")
    parser.add_argument("--scene_file", required=True, help="scene JSON path")
    parser.add_argument("--output_dir", required=True, help="output directory")
    args = parser.parse_args()

    # Reserve stdout for JSONL only. Taichi prints its banner at the C/C++ level
    # straight to file descriptor 1, so a Python-level sys.stdout swap is not enough:
    # dup the real stdout fd for emit(), then redirect fd 1 -> fd 2 (stderr) so every
    # native/print message goes to stderr instead of polluting the JSONL stream.
    global _REAL_STDOUT
    try:
        real_fd = os.dup(1)
        _REAL_STDOUT = os.fdopen(real_fd, "w", encoding="utf-8", buffering=1)
        os.dup2(2, 1)
    except (AttributeError, OSError):  # pragma: no cover - unusual platforms
        pass
    sys.stdout = sys.stderr  # Python-level print() -> stderr as well

    init_taichi()
    try:
        run(args.scene_file, args.output_dir)
    except SystemExit as e:
        # The solver aborts (e.g. domain-fit) via sys.exit(msg); surface it as an error.
        emit({"type": "error", "message": str(e)})
        raise
    except Exception as e:  # pragma: no cover
        emit({"type": "error", "message": repr(e)})
        raise


if __name__ == "__main__":
    main()

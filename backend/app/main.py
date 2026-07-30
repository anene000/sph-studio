"""FastAPI backend for SPH Studio (Phase A: launched as a separate process).

Endpoints map 1:1 to the features in docs/04_機能一覧.md:
  ①  /api/config/import|export        JSON import / export
  ③  /api/config/validate             domain-fit check (recommended scale)
  ②  /api/models                      list / upload .obj
  ⑤⑥ /api/jobs, /ws/jobs/{id}         create (auto-writes scene.json) / progress
  結果 /api/jobs/{id}/frames|download  results
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import ValidationError

from . import config_io, results
from .jobs import OUTPUTS_ROOT, REPO_ROOT, manager
from .models import Scene

app = FastAPI(title="SPH Studio Backend", version="0.0.1")

# Local single-user desktop app: allow the Next.js dev origin.
app.add_middleware(
    CORSMiddleware,
    # Dev servers plus the Tauri WebView origin, which differs by OS:
    #   Windows (WebView2): http://tauri.localhost (or https://)
    #   macOS/Linux:        tauri://localhost
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=(
        r"^(tauri://localhost|https?://tauri\.localhost|"
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?)$"
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_DIR = REPO_ROOT / "data" / "models"


def model_dirs() -> list[Path]:
    """Model search roots: the bundled data/models plus any external directories from
    the ``SPH_EXTRA_MODELS_DIR`` env var (os.pathsep-separated). Read per call so the
    setting can change without restarting (and to keep it test-friendly)."""
    dirs = [MODELS_DIR]
    extra = os.environ.get("SPH_EXTRA_MODELS_DIR", "")
    for part in extra.split(os.pathsep):
        part = part.strip()
        if part:
            p = Path(part).expanduser()
            if p not in dirs:
                dirs.append(p)
    return dirs


@app.get("/api/health")
def health():
    return {"ok": True, "service": "sph-studio-backend"}


@app.get("/api/info")
def info():
    """Environment info for the S7 settings screen (read-only in Phase A)."""
    return {
        "repoRoot": str(REPO_ROOT),
        "modelsDir": str(MODELS_DIR),
        "modelDirs": [str(d) for d in model_dirs()],
        "outputsDir": str(OUTPUTS_ROOT),
        "python": sys.executable,
        "arch": os.environ.get("SPH_ARCH", "auto (vulkan→cpu)"),
    }


# ---------- ① config import / export ----------
@app.post("/api/config/import")
def config_import(payload: dict):
    try:
        scene = config_io.parse_scene(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=json.loads(e.json())) from None
    return config_io.scene_to_dict(scene)


@app.post("/api/config/export")
def config_export(scene: Scene):
    return JSONResponse(config_io.scene_to_dict(scene))


# ---------- ③ domain-fit validation ----------
@app.post("/api/config/validate")
def config_validate(scene: Scene):
    return config_io.validate_scene(scene)


# ---------- ② models (bundled data/models + external SPH_EXTRA_MODELS_DIR) ----------
@app.get("/api/models")
def models_list():
    """Aggregate .obj across all model roots (bundled + external). Unique by name."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    seen: set[str] = set()
    for d in model_dirs():
        if not d.exists():
            continue
        for p in sorted(d.glob("*.obj")):
            if p.name not in seen:
                seen.add(p.name)
                names.append(p.name)
    return {"models": names}


@app.post("/api/models")
async def models_upload(file: UploadFile):
    """Import an external .obj (chosen from anywhere on disk) into data/models."""
    if not file.filename.lower().endswith(".obj"):
        raise HTTPException(status_code=400, detail="only .obj files are accepted")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / Path(file.filename).name
    dest.write_bytes(await file.read())
    return {"name": dest.name}


@app.get("/api/models/{name}")
def model_file(name: str):
    """Serve a raw .obj for the browser 3D preview. Searches every model root and
    confines each lookup to that root (path-traversal safe)."""
    for d in model_dirs():
        base = d.resolve()
        p = (base / name).resolve()
        if (p == base or base in p.parents) and p.exists() and p.suffix.lower() == ".obj":
            return FileResponse(p, media_type="text/plain", filename=p.name)
    raise HTTPException(status_code=404, detail="model not found")


# ---------- ⑤⑥ jobs ----------
@app.post("/api/jobs")
def jobs_create(scene: Scene):
    # Pre-flight domain-fit check; block obviously invalid runs early.
    validation = config_io.validate_scene(scene)
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation)
    job = manager.create(config_io.scene_to_dict(scene))
    return job.public()


@app.get("/api/jobs")
def jobs_list():
    return {"jobs": manager.list()}


@app.get("/api/jobs/{job_id}")
def jobs_get(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.public()


@app.post("/api/jobs/{job_id}/cancel")
def jobs_cancel(job_id: str):
    if not manager.cancel(job_id):
        raise HTTPException(status_code=409, detail="job not cancelable")
    return {"ok": True}


@app.websocket("/ws/jobs/{job_id}")
async def jobs_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = manager.get(job_id)
    if not job:
        await websocket.send_json({"type": "error", "message": "job not found"})
        await websocket.close()
        return

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_event(event: dict):
        loop.call_soon_threadsafe(queue.put_nowait, event)

    manager.subscribe(job_id, on_event)
    try:
        # Send a snapshot first so late subscribers catch up.
        await websocket.send_json({"type": "snapshot", **job.public()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") == "status" and event.get("status") in (
                "completed", "failed", "canceled"
            ):
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(job_id, on_event)


# ---------- results ----------
@app.get("/api/jobs/{job_id}/scene")
def jobs_scene(job_id: str):
    """The auto-generated scene.json for a job (used by the result viewer to draw the
    fixed analysis-space grid/box)."""
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    p = Path(job.output_dir) / "scene.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="scene.json not found")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/jobs/{job_id}/frames")
def jobs_frames(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return results.frames_index(job.output_dir)


@app.get("/api/jobs/{job_id}/frames/{frame}")
def jobs_frame(job_id: str, frame: int):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return results.frame_points(job.output_dir, frame)


@app.get("/api/jobs/{job_id}/download")
def jobs_download(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    data = results.bundle_zip(job.output_dir)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_results.zip"'},
    )

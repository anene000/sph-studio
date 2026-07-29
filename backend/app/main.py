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
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from . import config_io, results
from .jobs import REPO_ROOT, manager
from .models import Scene

app = FastAPI(title="SPH Studio Backend", version="0.0.1")

# Local single-user desktop app: allow the Next.js dev origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "tauri://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_DIR = REPO_ROOT / "data" / "models"


@app.get("/api/health")
def health():
    return {"ok": True, "service": "sph-studio-backend"}


# ---------- ① config import / export ----------
@app.post("/api/config/import")
def config_import(payload: dict):
    try:
        scene = config_io.parse_scene(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=json.loads(e.json()))
    return config_io.scene_to_dict(scene)


@app.post("/api/config/export")
def config_export(scene: Scene):
    return JSONResponse(config_io.scene_to_dict(scene))


# ---------- ③ domain-fit validation ----------
@app.post("/api/config/validate")
def config_validate(scene: Scene):
    return config_io.validate_scene(scene)


# ---------- ② models ----------
@app.get("/api/models")
def models_list():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return {"models": [p.name for p in sorted(MODELS_DIR.glob("*.obj"))]}


@app.post("/api/models")
async def models_upload(file: UploadFile):
    if not file.filename.lower().endswith(".obj"):
        raise HTTPException(status_code=400, detail="only .obj files are accepted")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / Path(file.filename).name
    dest.write_bytes(await file.read())
    return {"name": dest.name}


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

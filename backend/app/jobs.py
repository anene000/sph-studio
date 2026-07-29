"""Job manager: launches the headless solver as a subprocess (one process per job),
parses its JSON Lines progress on stdout, and exposes state + cancellation.

Phase A runs the solver via ``python solver/run_headless.py``. In Phase B the same
contract is satisfied by the PyInstaller-built sidecar binary.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SOLVER_ENTRY = REPO_ROOT / "solver" / "run_headless.py"
OUTPUTS_ROOT = REPO_ROOT / "outputs"


@dataclass
class Job:
    id: str
    config_path: str
    output_dir: str
    status: str = "queued"  # queued|running|completed|failed|canceled
    progress: dict = field(default_factory=dict)
    log: List[str] = field(default_factory=list)
    error: Optional[str] = None
    _proc: Optional[subprocess.Popen] = None

    def public(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "outputDir": self.output_dir,
            "error": self.error,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._subscribers: Dict[str, List[Callable[[dict], None]]] = {}
        self._lock = threading.Lock()

    # --- subscription (used by the WebSocket endpoint) ---
    def subscribe(self, job_id: str, cb: Callable[[dict], None]) -> None:
        self._subscribers.setdefault(job_id, []).append(cb)

    def unsubscribe(self, job_id: str, cb: Callable[[dict], None]) -> None:
        if job_id in self._subscribers and cb in self._subscribers[job_id]:
            self._subscribers[job_id].remove(cb)

    def _publish(self, job_id: str, event: dict) -> None:
        for cb in list(self._subscribers.get(job_id, [])):
            try:
                cb(event)
            except Exception:
                pass

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list(self) -> List[dict]:
        return [j.public() for j in self._jobs.values()]

    def create(self, scene: dict) -> Job:
        """Persist scene.json (the '① config file, auto-generated') then start the solver."""
        job_id = uuid.uuid4().hex[:12]
        output_dir = OUTPUTS_ROOT / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure Export.outputDir points at this job's directory.
        scene = dict(scene)
        exp = dict(scene.get("Export") or {})
        exp["outputDir"] = str(output_dir)
        scene["Export"] = exp

        config_path = output_dir / "scene.json"
        config_path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

        job = Job(id=job_id, config_path=str(config_path), output_dir=str(output_dir))
        self._jobs[job_id] = job
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job._proc is None or job.status not in ("running", "queued"):
            return False
        job._proc.terminate()
        job.status = "canceled"
        self._publish(job_id, {"type": "status", "status": "canceled"})
        return True

    def _run(self, job: Job) -> None:
        cmd = [sys.executable, str(SOLVER_ENTRY),
               "--scene_file", job.config_path,
               "--output_dir", job.output_dir]
        env = dict(os.environ)
        # The solver writes JSONL to stdout and human logs / tracebacks to stderr.
        # Keep the two apart: parse stdout as events, tee stderr to a per-job file.
        log_path = os.path.join(job.output_dir, "solver.log")
        try:
            job.status = "running"
            self._publish(job.id, {"type": "status", "status": "running"})
            with open(log_path, "w", encoding="utf-8") as log_file:
                job._proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=log_file,
                    text=True, bufsize=1, env=env, cwd=str(REPO_ROOT),
                )
                for line in job._proc.stdout:  # type: ignore[union-attr]
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        # stdout should be pure JSONL now; keep any stray line as a log.
                        job.log.append(line)
                        self._publish(job.id, {"type": "log", "message": line})
                        continue
                    etype = event.get("type")
                    if etype == "progress":
                        job.progress = event
                    elif etype == "error":
                        job.error = event.get("message")
                    self._publish(job.id, event)

                code = job._proc.wait()

            if job.status == "canceled":
                pass
            elif code == 0:
                job.status = "completed"
                self._publish(job.id, {"type": "status", "status": "completed"})
            else:
                job.status = "failed"
                job.error = job.error or self._tail_log(log_path) or f"solver exited with code {code}"
                self._publish(job.id, {"type": "status", "status": "failed", "error": job.error})
        except Exception as e:  # pragma: no cover
            job.status = "failed"
            job.error = repr(e)
            self._publish(job.id, {"type": "status", "status": "failed", "error": job.error})

    @staticmethod
    def _tail_log(log_path: str, n: int = 20) -> Optional[str]:
        try:
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()
            return "".join(lines[-n:]).strip() or None
        except OSError:
            return None


manager = JobManager()

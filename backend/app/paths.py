"""Filesystem roots, resolved differently in dev vs a frozen (PyInstaller) build.

- dev: the repo root (…/backend/app/paths.py -> parents[2]).
- frozen sidecar: the directory of the executable, so outputs/ and data/models/ are
  writable folders next to the app (portable), independent of the PyInstaller temp dir.
"""
from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


APP_ROOT = app_root()
OUTPUTS_ROOT = APP_ROOT / "outputs"
MODELS_DIR = APP_ROOT / "data" / "models"
SOLVER_ENTRY = APP_ROOT / "solver" / "run_headless.py"  # dev only; frozen self-invokes


def seed_bundled_data() -> None:
    """Frozen only: copy the bundled sample models/scenes (from _MEIPASS) to writable
    folders next to the executable, so the default scene's model resolves and the models
    list is populated on first run. Existing files are never overwritten."""
    if not getattr(sys, "frozen", False):
        return
    meipass = Path(getattr(sys, "_MEIPASS", ""))
    for sub in ("data/models", "data/scenes"):
        src = meipass / sub
        if not src.is_dir():
            continue
        dst = APP_ROOT / sub
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            target = dst / f.name
            if f.is_file() and not target.exists():
                try:
                    target.write_bytes(f.read_bytes())
                except OSError:
                    pass

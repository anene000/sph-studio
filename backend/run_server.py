"""Unified entrypoint for the SPH Studio backend sidecar (U19).

Two modes in ONE executable so the PyInstaller-frozen binary can both serve the API
and run the headless solver (a frozen exe cannot re-exec `python run_headless.py`):

  server mode (default):   sph-backend [--host H] [--port P]
  solver mode:             sph-backend --run-solver --scene_file S --output_dir D

In dev this runs under the venv python; when frozen, ``sys.frozen`` is set and the
solver modules are imported from the bundle. ``backend/app/jobs.py`` picks the right
invocation for the current mode.
"""
import os
import sys
from pathlib import Path


def _solver_search_paths() -> list[str]:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return [str(base), str(base / "solver")]
    return [str(Path(__file__).resolve().parents[1] / "solver")]


def _run_solver() -> None:
    # Strip our dispatch flag; run_headless parses the remaining --scene_file/--output_dir.
    sys.argv = [a for a in sys.argv if a != "--run-solver"]
    for p in _solver_search_paths():
        if p not in sys.path:
            sys.path.insert(0, p)
    import run_headless  # noqa: E402  (path set up above)

    run_headless.main()


def _run_server() -> None:
    # Ensure the backend package is importable when frozen or launched from elsewhere.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import uvicorn
    from app.main import app

    host = os.environ.get("SPH_HOST", "127.0.0.1")
    port = int(os.environ.get("SPH_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    if "--run-solver" in sys.argv:
        _run_solver()
    else:
        _run_server()


if __name__ == "__main__":
    main()

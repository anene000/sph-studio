# PyInstaller spec for the SPH Studio backend sidecar (U19).
#
#   pyinstaller backend/sph-backend.spec           # run from repo root
#
# Produces a single `sph-backend` binary that serves the API and (via --run-solver)
# runs the headless Taichi solver. Taichi/trimesh ship native libs + data files, so we
# collect_all() them. Per-OS validation is expected (done in the U20 release CI).
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.getcwd())
BACKEND = os.path.join(ROOT, "backend")
SOLVER = os.path.join(ROOT, "solver")

datas, binaries, hiddenimports = [], [], []
for pkg in ("taichi", "trimesh", "networkx", "scipy"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "app.main", "app.jobs", "app.config_io", "app.results", "app.models",
    "run_headless", "particle_system", "WCSPH", "DFSPH", "sph_base",
    "config_builder", "scan_single_buffer",
]

a = Analysis(
    [os.path.join(BACKEND, "run_server.py")],
    pathex=[BACKEND, SOLVER],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="sph-backend",
    console=True,
    disable_windowed_traceback=False,
    upx=False,
)

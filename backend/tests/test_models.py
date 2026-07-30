"""External .obj loading: SPH_EXTRA_MODELS_DIR listing/serving + upload. CI-safe (no Taichi)."""
import pytest
from fastapi.testclient import TestClient

OBJ = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    ext = tmp_path / "ext_models"
    ext.mkdir()
    (ext / "external_widget.obj").write_text(OBJ, encoding="utf-8")
    monkeypatch.setenv("SPH_EXTRA_MODELS_DIR", str(ext))
    from app.main import app
    return TestClient(app), ext


def test_external_dir_listed(client):
    c, _ = client
    names = c.get("/api/models").json()["models"]
    assert "external_widget.obj" in names          # external dir aggregated
    assert "bunny_sparse.obj" in names             # bundled dir still present


def test_external_obj_served(client):
    c, _ = client
    r = c.get("/api/models/external_widget.obj")
    assert r.status_code == 200
    assert r.text.startswith("v 0 0 0")


def test_info_reports_model_dirs(client):
    c, ext = client
    dirs = c.get("/api/info").json()["modelDirs"]
    assert any(str(ext) == d for d in dirs)


def test_missing_model_404(client):
    c, _ = client
    assert c.get("/api/models/does_not_exist.obj").status_code == 404


def test_upload_registers_model(client, tmp_path):
    c, _ = client
    up = c.post("/api/models", files={"file": ("uploaded_ext.obj", OBJ, "text/plain")})
    assert up.status_code == 200 and up.json()["name"] == "uploaded_ext.obj"
    assert "uploaded_ext.obj" in c.get("/api/models").json()["models"]
    # cleanup the bundled data/models artifact
    from app.main import MODELS_DIR
    (MODELS_DIR / "uploaded_ext.obj").unlink(missing_ok=True)

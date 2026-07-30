// Thin API client for the FastAPI backend (Phase A: http://localhost:8000).
import type { Scene } from "./schema";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch(`${BASE}/api/health`).then((r) => json<{ ok: boolean }>(r)),

  info: () =>
    fetch(`${BASE}/api/info`).then((r) =>
      json<{ repoRoot: string; modelsDir: string; outputsDir: string; python: string; arch: string }>(r)
    ),

  listJobs: () => fetch(`${BASE}/api/jobs`).then((r) => json<{ jobs: any[] }>(r)),

  importConfig: (payload: unknown) =>
    fetch(`${BASE}/api/config/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((r) => json<Scene>(r)),

  validate: (scene: Scene) =>
    fetch(`${BASE}/api/config/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scene),
    }).then((r) => json<{ ok: boolean; issues: any[] }>(r)),

  listModels: () => fetch(`${BASE}/api/models`).then((r) => json<{ models: string[] }>(r)),

  // Raw .obj URL for the 3D preview (react-three-fiber OBJLoader).
  modelUrl: (name: string) => `${BASE}/api/models/${encodeURIComponent(name)}`,

  // Import an external .obj (any path on disk) via the OS file picker -> data/models.
  uploadModel: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`${BASE}/api/models`, { method: "POST", body: fd }).then((r) =>
      json<{ name: string }>(r)
    );
  },

  createJob: (scene: Scene) =>
    fetch(`${BASE}/api/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scene),
    }).then((r) => json<{ id: string; status: string }>(r)),

  getJob: (id: string) => fetch(`${BASE}/api/jobs/${id}`).then((r) => json<any>(r)),

  cancelJob: (id: string) =>
    fetch(`${BASE}/api/jobs/${id}/cancel`, { method: "POST" }).then((r) => json<any>(r)),

  frames: (id: string) => fetch(`${BASE}/api/jobs/${id}/frames`).then((r) => json<any>(r)),

  frame: (id: string, n: number) =>
    fetch(`${BASE}/api/jobs/${id}/frames/${n}`).then((r) => json<any>(r)),

  downloadUrl: (id: string) => `${BASE}/api/jobs/${id}/download`,

  // WebSocket for live progress (⑥).
  jobSocket: (id: string) => {
    const wsBase = BASE.replace(/^http/, "ws");
    return new WebSocket(`${wsBase}/ws/jobs/${id}`);
  },
};

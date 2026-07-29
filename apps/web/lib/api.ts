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

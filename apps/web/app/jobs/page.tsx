"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { ui } from "@/components/fields";
import { api } from "@/lib/api";

type Progress = {
  step?: number;
  totalSteps?: number;
  simTime?: number;
  totalTime?: number;
  elapsed?: number;
  eta?: number;
  particleNum?: number;
};

// U13/U18: S5 progress via WebSocket. Query-param route (/jobs?id=...) so the app
// can be statically exported for the Tauri desktop bundle.
function JobProgress() {
  const id = useSearchParams().get("id") ?? "";
  const [status, setStatus] = useState("connecting");
  const [progress, setProgress] = useState<Progress>({});
  const [log, setLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    const ws = api.jobSocket(id);
    ws.onopen = () => setStatus("running");
    ws.onmessage = (ev) => {
      const e = JSON.parse(ev.data);
      switch (e.type) {
        case "snapshot":
          setStatus(e.status);
          if (e.progress) setProgress(e.progress);
          break;
        case "progress":
          setProgress(e);
          break;
        case "status":
          setStatus(e.status);
          if (e.error) setError(e.error);
          break;
        case "frame":
          setLog((l) => [...l, `frame ${e.frame} @ t=${(e.simTime ?? 0).toFixed(4)}`]);
          break;
        case "log":
          setLog((l) => [...l, e.message]);
          break;
        case "error":
          setError(e.message);
          break;
      }
    };
    ws.onclose = () => setStatus((s) => (s === "running" ? "disconnected" : s));
    return () => ws.close();
  }, [id]);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [log]);

  const pct =
    progress.step && progress.totalSteps
      ? Math.min(100, (progress.step / progress.totalSteps) * 100)
      : status === "completed"
      ? 100
      : 0;
  const done = ["completed", "failed", "canceled"].includes(status);

  return (
    <main style={{ ...ui.page, maxWidth: 820 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: 22 }}>進捗 — job {id}</h1>
        <span style={{ fontSize: 13, opacity: 0.8 }}>状態: {statusLabel(status)}</span>
      </div>

      <div style={{ height: 18, background: "#111725", borderRadius: 9, overflow: "hidden", margin: "12px 0" }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: status === "failed" ? "#e35d5d" : "#1f6feb",
            transition: "width 0.2s",
          }}
        />
      </div>

      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", fontSize: 13 }}>
        <span>step: {progress.step ?? 0}/{progress.totalSteps ?? "?"}</span>
        <span>simTime: {(progress.simTime ?? 0).toFixed(4)}/{progress.totalTime ?? "?"}</span>
        <span>粒子数: {progress.particleNum ?? "?"}</span>
        <span>経過: {(progress.elapsed ?? 0).toFixed(1)}s</span>
        <span>ETA: {(progress.eta ?? 0).toFixed(1)}s</span>
      </div>

      {error && (
        <pre style={{ ...ui.card, borderColor: "#e35d5d", color: "#f2b8b8", whiteSpace: "pre-wrap", fontSize: 12, marginTop: 12 }}>
          {error}
        </pre>
      )}

      <h2 style={ui.h2}>ログ</h2>
      <div
        ref={logRef}
        style={{
          height: 220,
          overflowY: "auto",
          background: "#0b0e14",
          border: "1px solid #263041",
          borderRadius: 8,
          padding: 10,
          fontFamily: "monospace",
          fontSize: 12,
        }}
      >
        {log.map((l, i) => (
          <div key={i} style={{ opacity: 0.85 }}>{l}</div>
        ))}
      </div>

      <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
        {!done && (
          <button onClick={() => api.cancelJob(id)} style={{ ...ui.button, background: "#8b2f2f" }}>
            キャンセル
          </button>
        )}
        {status === "completed" && (
          <Link href={`/results?id=${id}`} style={{ ...ui.button, textDecoration: "none" }}>
            結果を見る →
          </Link>
        )}
        {done && status !== "completed" && (
          <Link href="/run" style={{ ...ui.button, background: "#30363d", textDecoration: "none" }}>
            ← 実行画面へ戻る
          </Link>
        )}
      </div>
    </main>
  );
}

export default function JobProgressPage() {
  return (
    <Suspense fallback={<main style={ui.page}>読み込み中…</main>}>
      <JobProgress />
    </Suspense>
  );
}

function statusLabel(s: string) {
  return (
    { connecting: "接続中", running: "実行中", completed: "完了", failed: "失敗", canceled: "中断", disconnected: "切断" } as Record<
      string,
      string
    >
  )[s] || s;
}

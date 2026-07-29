"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useSceneStore } from "@/lib/store";

// S0 Home (U15): new / import / job list.
export default function Home() {
  const router = useRouter();
  const { resetScene, loadScene } = useSceneStore();
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [jobs, setJobs] = useState<any[]>([]);
  const [importErr, setImportErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      await api.health();
      setHealth("ok");
      setJobs((await api.listJobs()).jobs.reverse());
    } catch {
      setHealth("down");
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, []);

  function newCalc() {
    resetScene();
    router.push("/scene");
  }

  async function onImport(e: React.ChangeEvent<HTMLInputElement>) {
    setImportErr(null);
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const raw = JSON.parse(await file.text());
      const scene = await api.importConfig(raw); // validate + normalize
      loadScene(scene);
      router.push("/scene");
    } catch (err) {
      setImportErr(String(err));
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "48px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1 style={{ fontSize: 28, marginBottom: 4 }}>SPH Studio</h1>
        <Link href="/settings" style={{ fontSize: 13, color: "#9fb0c8" }}>
          ⚙ 環境設定
        </Link>
      </div>
      <p style={{ opacity: 0.75, marginTop: 0 }}>
        Taichi SPH シミュレータの GUI（TypeScript + Next.js + Python）
      </p>

      <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
        <button onClick={newCalc} style={primaryBtn}>＋ 新規計算</button>
        <button onClick={() => fileRef.current?.click()} style={secondaryBtn}>
          ① 設定ファイル（JSON）をインポート
        </button>
        <input ref={fileRef} type="file" accept=".json,application/json" onChange={onImport} style={{ display: "none" }} />
      </div>
      {importErr && (
        <pre style={{ ...card, borderColor: "#e35d5d", color: "#f2b8b8", whiteSpace: "pre-wrap", fontSize: 12 }}>
          インポート失敗: {importErr}
        </pre>
      )}

      <section style={card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>バックエンド</strong>
          <span style={{ fontFamily: "monospace", fontSize: 13, color: health === "ok" ? "#5de38a" : health === "down" ? "#e35d5d" : "#9fb0c8" }}>
            {health === "ok" ? "● 接続 OK" : health === "down" ? "● 未接続（uvicorn :8000 を起動）" : "確認中…"}
          </span>
        </div>
      </section>

      <section style={card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <strong>ジョブ一覧</strong>
          <button onClick={refresh} style={{ ...secondaryBtn, padding: "4px 10px", fontSize: 12 }}>更新</button>
        </div>
        {jobs.length === 0 ? (
          <p style={{ fontSize: 13, opacity: 0.6, margin: 0 }}>ジョブはまだありません。</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: "left", opacity: 0.6 }}>
                <th style={th}>job</th>
                <th style={th}>状態</th>
                <th style={th}>進捗</th>
                <th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} style={{ borderTop: "1px solid #263041" }}>
                  <td style={{ ...td, fontFamily: "monospace" }}>{j.id}</td>
                  <td style={td}>{statusLabel(j.status)}</td>
                  <td style={td}>
                    {j.progress?.step ? `${j.progress.step}/${j.progress.totalSteps ?? "?"}` : "-"}
                  </td>
                  <td style={{ ...td, textAlign: "right" }}>
                    <Link href={`/jobs/${j.id}`} style={linkBtn}>進捗</Link>
                    {j.status === "completed" && (
                      <Link href={`/results/${j.id}`} style={{ ...linkBtn, marginLeft: 8 }}>結果</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

function statusLabel(s: string) {
  return ({ queued: "待機", running: "実行中", completed: "完了", failed: "失敗", canceled: "中断" } as Record<string, string>)[s] || s;
}

const card: React.CSSProperties = { border: "1px solid #263041", borderRadius: 10, padding: 16, marginTop: 20, background: "#111725" };
const primaryBtn: React.CSSProperties = { padding: "10px 18px", background: "#1f6feb", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 14 };
const secondaryBtn: React.CSSProperties = { padding: "10px 16px", background: "#21262d", color: "#e6e6e6", border: "1px solid #30363d", borderRadius: 8, cursor: "pointer", fontSize: 14 };
const th: React.CSSProperties = { padding: "4px 6px", fontWeight: 400 };
const td: React.CSSProperties = { padding: "8px 6px" };
const linkBtn: React.CSSProperties = { fontSize: 12, color: "#4aa3ff", textDecoration: "none" };

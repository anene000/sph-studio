"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

// S0 Home (scaffold). Full screens (S1–S7) are implemented per docs/07 units U7–U15.
export default function Home() {
  const [health, setHealth] = useState<string>("checking...");

  useEffect(() => {
    api
      .health()
      .then(() => setHealth("backend: OK"))
      .catch(() => setHealth("backend: not reachable (start uvicorn on :8000)"));
  }, []);

  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: 28, marginBottom: 8 }}>SPH Studio</h1>
      <p style={{ opacity: 0.8, marginTop: 0 }}>
        Taichi SPH シミュレータの GUI（TypeScript + Next.js + Python）
      </p>

      <section style={card}>
        <strong>ステータス</strong>
        <div style={{ marginTop: 8, fontFamily: "monospace" }}>{health}</div>
        <Link
          href="/scene"
          style={{
            display: "inline-block",
            marginTop: 14,
            padding: "8px 14px",
            background: "#1f6feb",
            color: "white",
            borderRadius: 6,
            textDecoration: "none",
            fontSize: 14,
          }}
        >
          シーン設定（S1）を開く →
        </Link>
      </section>

      <section style={card}>
        <strong>画面（実装ロードマップ / docs/07）</strong>
        <ul style={{ lineHeight: 1.9 }}>
          <li>S1 シーン設定（解析空間・オブジェクト・3Dプレビュー） — U8/U9</li>
          <li>S2 計算パラメータ — U10</li>
          <li>S3 出力設定（流体/オブジェクト別個・時間刻み） — U11</li>
          <li>S4 確認 & 実行（scene.json 自動生成） — U12</li>
          <li>S5 進捗（WebSocket） — U13</li>
          <li>S6 結果（3D再生・CSV出力） — U14</li>
        </ul>
      </section>

      <p style={{ opacity: 0.6, fontSize: 13 }}>
        これは初回スキャフォールドです。各画面は docs/07 のユニット順に実装します。
      </p>
    </main>
  );
}

const card: React.CSSProperties = {
  border: "1px solid #263041",
  borderRadius: 10,
  padding: 16,
  marginTop: 20,
  background: "#111725",
};

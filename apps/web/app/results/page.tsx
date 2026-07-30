"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ui } from "@/components/fields";
import { api } from "@/lib/api";

const ResultViewer3D = dynamic(() => import("@/components/ResultViewer3D"), {
  ssr: false,
  loading: () => <div style={{ padding: 24, opacity: 0.6 }}>3D を初期化中…</div>,
});

type FrameMeta = { frame: number; simTime: number };
type FramePoints = { fluid: number[][]; objects: Record<string, number[][]> };

// U14/U18: S6 results. Query-param route (/results?id=...) for static export.
function Results() {
  const id = useSearchParams().get("id") ?? "";
  const [frames, setFrames] = useState<FrameMeta[]>([]);
  const [idx, setIdx] = useState(0);
  const [points, setPoints] = useState<FramePoints>({ fluid: [], objects: {} });
  const [domain, setDomain] = useState<{ start: number[]; end: number[] } | undefined>();

  useEffect(() => {
    if (!id) return;
    api.frames(id).then((d) => setFrames(d.frames || [])).catch(() => {});
    api
      .jobScene(id)
      .then((s) => setDomain({ start: s.Configuration.domainStart, end: s.Configuration.domainEnd }))
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    if (!id || frames.length === 0) return;
    const f = frames[idx];
    if (!f) return;
    api.frame(id, f.frame).then(setPoints);
  }, [id, frames, idx]);

  const cur = frames[idx];

  return (
    <main style={{ display: "grid", gridTemplateRows: "auto 1fr auto", height: "100vh" }}>
      <header style={{ padding: "12px 16px", borderBottom: "1px solid #263041", display: "flex", gap: 16, alignItems: "center" }}>
        <Link href="/" style={{ fontSize: 12, opacity: 0.7 }}>SPH Studio</Link>
        <h1 style={{ fontSize: 18, margin: 0 }}>結果 — job {id}</h1>
        <span style={{ fontSize: 13, opacity: 0.8 }}>フレーム {frames.length} 件</span>
        <a href={api.downloadUrl(id)} style={{ ...ui.button, marginLeft: "auto", textDecoration: "none", fontSize: 13 }}>
          CSV 一括ダウンロード（zip）
        </a>
      </header>

      <section style={{ position: "relative" }}>
        <ResultViewer3D fluid={points.fluid} objects={points.objects} domain={domain} />
        <div style={{ position: "absolute", top: 10, left: 12, fontSize: 12, opacity: 0.7 }}>
          橙=解析空間グリッド（固定） / 青=流体パーティクル / 白=オブジェクト
        </div>
      </section>

      <footer style={{ padding: "12px 16px", borderTop: "1px solid #263041" }}>
        {frames.length > 0 ? (
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ fontSize: 13, width: 190 }}>
              frame {cur?.frame ?? 0} / t = {(cur?.simTime ?? 0).toFixed(4)}s
            </span>
            <input
              type="range"
              min={0}
              max={frames.length - 1}
              value={idx}
              onChange={(e) => setIdx(Number(e.target.value))}
              style={{ flex: 1 }}
            />
            <span style={{ fontSize: 13 }}>
              流体 {points.fluid.length} 点 / オブジェクト {Object.values(points.objects).reduce((a, b) => a + b.length, 0)} 点
            </span>
          </div>
        ) : (
          <span style={{ fontSize: 13, opacity: 0.6 }}>フレームがありません。</span>
        )}
      </footer>
    </main>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<main style={ui.page}>読み込み中…</main>}>
      <Results />
    </Suspense>
  );
}

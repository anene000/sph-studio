"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import StepNav from "@/components/StepNav";
import { ui } from "@/components/fields";
import { api } from "@/lib/api";
import { useSceneStore } from "@/lib/store";

// U12: S4 review & launch. Creating the job auto-writes scene.json server-side.
export default function RunPage() {
  const { scene } = useSceneStore();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const c = scene.Configuration;
  const steps = c.totalSteps ?? Math.round((c.totalTime ?? 0) / c.timeStepSize);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const job = await api.createJob(scene);
      router.push(`/jobs?id=${job.id}`);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <>
      <StepNav />
      <main style={ui.page}>
        <h1 style={{ fontSize: 22 }}>確認 &amp; 実行</h1>

        <div style={ui.card}>
          <div style={row}>解析空間: [{c.domainStart.join(", ")}] → [{c.domainEnd.join(", ")}]</div>
          <div style={row}>ソルバ: {c.simulationMethod === 4 ? "DFSPH" : "WCSPH"}</div>
          <div style={row}>particleRadius: {c.particleRadius} / dt: {c.timeStepSize}</div>
          <div style={row}>totalTime: {c.totalTime}s（約 {steps} ステップ）</div>
          <div style={row}>剛体: {scene.RigidBodies.length} 個 / 流体ブロック: {scene.FluidBlocks.length} 個</div>
          <div style={row}>
            出力間隔: {scene.Export.interval.value} {scene.Export.interval.mode}
            ／流体: {scene.Export.fluid.enabled ? scene.Export.fluid.fields.join("+") : "off"}
            ／オブジェクト追跡: {scene.Export.objects.map((o) => `#${o.objectId}(${o.mode})`).join(", ") || "なし"}
          </div>
        </div>

        <p style={{ fontSize: 12, opacity: 0.7 }}>
          「実行」で scene.json が自動生成され、ソルバがサブプロセスで起動します。
        </p>

        {error && (
          <pre style={{ ...ui.card, borderColor: "#e35d5d", color: "#f2b8b8", whiteSpace: "pre-wrap", fontSize: 12 }}>
            {error}
          </pre>
        )}

        <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
          <Link href="/export" style={{ ...ui.button, background: "#30363d", textDecoration: "none" }}>
            ← 出力設定
          </Link>
          <button onClick={run} disabled={busy} style={ui.button}>
            {busy ? "起動中…" : "▶ 実行"}
          </button>
        </div>
      </main>
    </>
  );
}

const row: React.CSSProperties = { fontSize: 13, marginBottom: 6 };

"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useSceneStore } from "@/lib/store";

// react-three-fiber must run client-side only.
const Viewer3D = dynamic(() => import("@/components/Viewer3D"), {
  ssr: false,
  loading: () => <div style={{ padding: 24, opacity: 0.6 }}>3D ビューを初期化中…</div>,
});

const AXES = ["x", "y", "z"];

function Vec3Row({
  label,
  value,
  onChange,
  step = 0.01,
}: {
  label: string;
  value: number[];
  onChange: (axis: number, v: number) => void;
  step?: number;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
      <span style={{ width: 92, fontSize: 12, opacity: 0.8 }}>{label}</span>
      {AXES.map((ax, i) => (
        <label key={ax} style={{ display: "flex", alignItems: "center", gap: 2 }}>
          <span style={{ fontSize: 11, opacity: 0.5 }}>{ax}</span>
          <input
            type="number"
            step={step}
            value={value[i]}
            onChange={(e) => onChange(i, parseFloat(e.target.value))}
            style={input}
          />
        </label>
      ))}
    </div>
  );
}

export default function ScenePage() {
  const { scene, setDomain, setRigidVec, updateRigidBody, issues, setIssues } = useSceneStore();
  const [busy, setBusy] = useState(false);

  async function validate() {
    setBusy(true);
    try {
      const res = await api.validate(scene);
      setIssues(res.issues || []);
    } catch (e) {
      setIssues([{ objectId: -1, level: "error", message: String(e) }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ display: "grid", gridTemplateColumns: "320px 1fr 300px", height: "100vh" }}>
      {/* Left: settings */}
      <aside style={{ ...panel, borderRight: "1px solid #263041", overflowY: "auto" }}>
        <Link href="/" style={{ fontSize: 12, opacity: 0.7 }}>
          ← ホーム
        </Link>
        <h2 style={h2}>解析空間</h2>
        <Vec3Row
          label="domainStart"
          value={scene.Configuration.domainStart}
          onChange={(ax, v) => setDomain("domainStart", ax, v)}
        />
        <Vec3Row
          label="domainEnd"
          value={scene.Configuration.domainEnd}
          onChange={(ax, v) => setDomain("domainEnd", ax, v)}
        />

        <h2 style={h2}>オブジェクト（剛体）</h2>
        {scene.RigidBodies.map((rb, i) => (
          <div key={i} style={objCard}>
            <div style={{ fontSize: 12, marginBottom: 6 }}>
              #{rb.objectId} — {rb.geometryFile.split(/[\\/]/).pop()}
            </div>
            <Vec3Row
              label="translation"
              value={rb.translation}
              onChange={(ax, v) => setRigidVec(i, "translation", ax, v)}
            />
            <Vec3Row
              label="scale"
              value={rb.scale}
              step={0.001}
              onChange={(ax, v) => setRigidVec(i, "scale", ax, v)}
            />
          </div>
        ))}

        <button onClick={validate} disabled={busy} style={button}>
          {busy ? "検証中…" : "解析空間フィット検証"}
        </button>
      </aside>

      {/* Center: 3D preview */}
      <section style={{ position: "relative" }}>
        <Viewer3D scene={scene} />
        <div style={overlay}>解析空間（橙枠）／流体ブロック（半透明）／剛体メッシュ</div>
      </section>

      {/* Right: validation / recommended scale */}
      <aside style={{ ...panel, borderLeft: "1px solid #263041", overflowY: "auto" }}>
        <h2 style={h2}>フィット検証結果</h2>
        {issues.length === 0 && (
          <p style={{ fontSize: 12, opacity: 0.6 }}>
            「解析空間フィット検証」を実行してください。
          </p>
        )}
        {issues.map((iss, k) => (
          <div key={k} style={{ ...issueCard, borderColor: levelColor(iss.level) }}>
            <div style={{ fontSize: 12, color: levelColor(iss.level) }}>
              [{iss.level}] object #{iss.objectId}
            </div>
            <div style={{ fontSize: 12, margin: "4px 0" }}>{iss.message}</div>
            {iss.recommendedScalePerAxis && (
              <>
                <div style={{ fontSize: 11, opacity: 0.8 }}>
                  推奨 scale（軸別）: [{iss.recommendedScalePerAxis.map((v) => v.toFixed(4)).join(", ")}]
                </div>
                <div style={{ fontSize: 11, opacity: 0.8 }}>
                  推奨 scale（比保持）: [
                  {iss.recommendedScaleUniform?.map((v) => v.toFixed(4)).join(", ")}]
                </div>
                <button
                  style={{ ...button, marginTop: 6 }}
                  onClick={() => {
                    const idx = scene.RigidBodies.findIndex((r) => r.objectId === iss.objectId);
                    if (idx >= 0 && iss.recommendedScalePerAxis)
                      updateRigidBody(idx, { scale: iss.recommendedScalePerAxis });
                  }}
                >
                  軸別の推奨 scale を適用
                </button>
              </>
            )}
          </div>
        ))}
      </aside>
    </main>
  );
}

function levelColor(level: string) {
  return level === "error" ? "#e35d5d" : level === "warn" ? "#e3b25d" : "#5d9de3";
}

const panel: React.CSSProperties = { padding: 16, background: "#0e1420" };
const h2: React.CSSProperties = { fontSize: 14, margin: "16px 0 8px" };
const input: React.CSSProperties = {
  width: 64,
  background: "#111725",
  border: "1px solid #263041",
  color: "#e6e6e6",
  borderRadius: 4,
  padding: "3px 5px",
  fontSize: 12,
};
const button: React.CSSProperties = {
  width: "100%",
  marginTop: 12,
  padding: "8px 10px",
  background: "#1f6feb",
  color: "white",
  border: "none",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 13,
};
const objCard: React.CSSProperties = {
  border: "1px solid #263041",
  borderRadius: 8,
  padding: 10,
  marginBottom: 10,
  background: "#111725",
};
const issueCard: React.CSSProperties = {
  border: "1px solid",
  borderRadius: 8,
  padding: 10,
  marginBottom: 10,
  background: "#111725",
};
const overlay: React.CSSProperties = {
  position: "absolute",
  bottom: 10,
  left: 12,
  fontSize: 11,
  opacity: 0.6,
  pointerEvents: "none",
};

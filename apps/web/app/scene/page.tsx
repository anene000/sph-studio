"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import StepNav from "@/components/StepNav";
import { Vec3Edit, ColorEdit, ui } from "@/components/fields";
import { api } from "@/lib/api";
import { useSceneStore } from "@/lib/store";

const Viewer3D = dynamic(() => import("@/components/Viewer3D"), {
  ssr: false,
  loading: () => <div style={{ padding: 24, opacity: 0.6 }}>3D ビューを初期化中…</div>,
});

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
      <span style={{ width: 78, fontSize: 11, opacity: 0.75 }}>{label}</span>
      {children}
    </div>
  );
}

export default function ScenePage() {
  const {
    scene,
    setDomain,
    setRigidVec,
    updateRigidBody,
    updateFluidBlock,
    mutate,
    addFluidBlock,
    removeFluidBlock,
    addRigidBody,
    removeRigidBody,
    issues,
    setIssues,
  } = useSceneStore();
  const [busy, setBusy] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [pick, setPick] = useState("");
  const [uploading, setUploading] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);

  function loadModels(select?: string) {
    return api.listModels().then((d) => {
      setModels(d.models);
      setPick(select && d.models.includes(select) ? select : d.models[0] ?? "");
    });
  }

  useEffect(() => {
    loadModels();
  }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const { name } = await api.uploadModel(file); // external .obj -> data/models
      await loadModels(name);
      addRigidBody(`data/models/${name}`); // add it immediately
    } catch (err) {
      setIssues([{ objectId: -1, level: "error", message: `アップロード失敗: ${err}` }]);
    } finally {
      setUploading(false);
      if (uploadRef.current) uploadRef.current.value = "";
    }
  }

  async function validate() {
    setBusy(true);
    try {
      setIssues((await api.validate(scene)).issues || []);
    } catch (e) {
      setIssues([{ objectId: -1, level: "error", message: String(e) }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <StepNav />
      <main style={{ display: "grid", gridTemplateColumns: "360px 1fr 300px", flex: 1, minHeight: 0 }}>
        {/* Left: settings */}
        <aside style={{ ...panel, borderRight: "1px solid #263041", overflowY: "auto" }}>
          <h3 style={h3}>① 解析空間</h3>
          <Field label="start">
            <Vec3Edit value={scene.Configuration.domainStart} onChange={(a, v) => setDomain("domainStart", a, v)} step={0.1} />
          </Field>
          <Field label="end">
            <Vec3Edit value={scene.Configuration.domainEnd} onChange={(a, v) => setDomain("domainEnd", a, v)} step={0.1} />
          </Field>

          {/* ② Fluid blocks (multiple) */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
            <h3 style={h3}>② 流体ブロック</h3>
            <button style={miniBtn} onClick={addFluidBlock}>＋追加</button>
          </div>
          {scene.FluidBlocks.map((b, i) => (
            <div key={i} style={objCard}>
              <div style={cardHead}>
                <span>#{b.objectId} 流体</span>
                <button style={rm} onClick={() => removeFluidBlock(i)}>削除</button>
              </div>
              <Field label="start"><Vec3Edit value={b.start} step={0.05} onChange={(a, v) => mutate((s) => (s.FluidBlocks[i].start[a] = v))} /></Field>
              <Field label="end"><Vec3Edit value={b.end} step={0.05} onChange={(a, v) => mutate((s) => (s.FluidBlocks[i].end[a] = v))} /></Field>
              <Field label="translation"><Vec3Edit value={b.translation} step={0.05} onChange={(a, v) => mutate((s) => (s.FluidBlocks[i].translation[a] = v))} /></Field>
              <Field label="初速 velocity"><Vec3Edit value={b.velocity} step={0.1} onChange={(a, v) => mutate((s) => (s.FluidBlocks[i].velocity[a] = v))} /></Field>
              <Field label="density">
                <input type="number" step={1} value={b.density} onChange={(e) => updateFluidBlock(i, { density: parseFloat(e.target.value) })} style={{ ...ui.input, width: 90 }} />
                <ColorEdit value={b.color} onChange={(c) => updateFluidBlock(i, { color: c })} />
              </Field>
            </div>
          ))}

          {/* ③ Rigid bodies (multiple) */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
            <h3 style={h3}>③ 剛体モデル</h3>
          </div>
          <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
            <select value={pick} onChange={(e) => setPick(e.target.value)} style={{ ...ui.input, width: 190 }}>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <button style={miniBtn} disabled={!pick} onClick={() => addRigidBody(`data/models/${pick}`)}>＋追加</button>
          </div>
          <div style={{ marginBottom: 8 }}>
            <button style={{ ...miniBtn, background: "#21262d", border: "1px solid #30363d", width: "100%" }}
              disabled={uploading} onClick={() => uploadRef.current?.click()}>
              {uploading ? "取り込み中…" : "外部 .obj を取り込む（アップロード）"}
            </button>
            <input ref={uploadRef} type="file" accept=".obj" onChange={onUpload} style={{ display: "none" }} />
          </div>
          {scene.RigidBodies.map((rb, i) => (
            <div key={i} style={objCard}>
              <div style={cardHead}>
                <span>#{rb.objectId} {rb.geometryFile.split(/[\\/]/).pop()}</span>
                <button style={rm} onClick={() => removeRigidBody(i)}>削除</button>
              </div>
              <Field label="translation"><Vec3Edit value={rb.translation} onChange={(a, v) => setRigidVec(i, "translation", a, v)} /></Field>
              <Field label="scale"><Vec3Edit value={rb.scale} step={0.01} onChange={(a, v) => setRigidVec(i, "scale", a, v)} /></Field>
              <Field label="rotate axis"><Vec3Edit value={rb.rotationAxis} step={1} onChange={(a, v) => mutate((s) => (s.RigidBodies[i].rotationAxis[a] = v))} /></Field>
              <Field label="rotate °">
                <input type="number" step={5} value={rb.rotationAngle} onChange={(e) => updateRigidBody(i, { rotationAngle: parseFloat(e.target.value) })} style={{ ...ui.input, width: 70 }} />
              </Field>
              <Field label="初速 velocity"><Vec3Edit value={rb.velocity} step={0.5} onChange={(a, v) => mutate((s) => (s.RigidBodies[i].velocity[a] = v))} /></Field>
              <Field label="density">
                <input type="number" step={1} value={rb.density} onChange={(e) => updateRigidBody(i, { density: parseFloat(e.target.value) })} style={{ ...ui.input, width: 90 }} />
                <ColorEdit value={rb.color} onChange={(c) => updateRigidBody(i, { color: c })} />
              </Field>
              <Field label="isDynamic">
                <input type="checkbox" checked={rb.isDynamic} onChange={(e) => updateRigidBody(i, { isDynamic: e.target.checked })} />
                <span style={{ fontSize: 11, opacity: 0.6 }}>{rb.isDynamic ? "動的（PBD剛体）" : "静的（固定壁）"}</span>
              </Field>
            </div>
          ))}

          <button onClick={validate} disabled={busy} style={{ ...ui.button, width: "100%", marginTop: 14 }}>
            {busy ? "検証中…" : "解析空間フィット検証"}
          </button>
        </aside>

        {/* Center: 3D preview */}
        <section style={{ position: "relative", minHeight: 0 }}>
          <Viewer3D scene={scene} />
          <div style={overlay}>解析空間（橙枠）／流体ブロック（半透明）／剛体メッシュ</div>
        </section>

        {/* Right: validation */}
        <aside style={{ ...panel, borderLeft: "1px solid #263041", overflowY: "auto" }}>
          <h3 style={h3}>フィット検証結果</h3>
          {issues.length === 0 && <p style={{ fontSize: 12, opacity: 0.6 }}>「検証」を実行してください。</p>}
          {issues.map((iss, k) => (
            <div key={k} style={{ ...objCard, borderColor: levelColor(iss.level) }}>
              <div style={{ fontSize: 12, color: levelColor(iss.level) }}>[{iss.level}] object #{iss.objectId}</div>
              <div style={{ fontSize: 12, margin: "4px 0" }}>{iss.message}</div>
              {iss.recommendedScalePerAxis && (
                <>
                  <div style={{ fontSize: 11, opacity: 0.8 }}>推奨(軸別): [{iss.recommendedScalePerAxis.map((v) => v.toFixed(4)).join(", ")}]</div>
                  <div style={{ fontSize: 11, opacity: 0.8 }}>推奨(比保持): [{iss.recommendedScaleUniform?.map((v) => v.toFixed(4)).join(", ")}]</div>
                  <button
                    style={{ ...ui.button, marginTop: 6, fontSize: 12, padding: "6px 10px" }}
                    onClick={() => {
                      const idx = scene.RigidBodies.findIndex((r) => r.objectId === iss.objectId);
                      if (idx >= 0 && iss.recommendedScalePerAxis) updateRigidBody(idx, { scale: iss.recommendedScalePerAxis });
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
    </div>
  );
}

function levelColor(level: string) {
  return level === "error" ? "#e35d5d" : level === "warn" ? "#e3b25d" : "#5d9de3";
}

const panel: React.CSSProperties = { padding: 14, background: "#0e1420" };
const h3: React.CSSProperties = { fontSize: 13, margin: "6px 0" };
const objCard: React.CSSProperties = { border: "1px solid #263041", borderRadius: 8, padding: 10, marginBottom: 8, background: "#111725" };
const cardHead: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, marginBottom: 6 };
const miniBtn: React.CSSProperties = { fontSize: 12, padding: "4px 10px", background: "#1f6feb", color: "white", border: "none", borderRadius: 5, cursor: "pointer" };
const rm: React.CSSProperties = { fontSize: 11, padding: "2px 8px", background: "#8b2f2f", color: "white", border: "none", borderRadius: 4, cursor: "pointer" };
const overlay: React.CSSProperties = { position: "absolute", bottom: 10, left: 12, fontSize: 11, opacity: 0.6, pointerEvents: "none" };

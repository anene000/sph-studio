"use client";

import Link from "next/link";
import StepNav from "@/components/StepNav";
import { Row, Num, ui } from "@/components/fields";
import { estimateScene, feasibilityColor, fmt } from "@/lib/estimate";
import { useSceneStore } from "@/lib/store";

// U10: S2 calculation parameters.
export default function ParamsPage() {
  const { scene, mutate } = useSceneStore();
  const c = scene.Configuration;
  const est = estimateScene(scene);

  return (
    <>
      <StepNav />
      <main style={ui.page}>
        <h1 style={{ fontSize: 22 }}>計算パラメータ設定</h1>

        {/* Static particle-budget guide (updates live with particleRadius / domain / blocks) */}
        <div style={{ ...ui.card, borderColor: feasibilityColor(est.level) }}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "baseline" }}>
            <strong style={{ color: feasibilityColor(est.level) }}>
              推定 流体粒子数: {fmt(est.fluidParticles)}
            </strong>
            <span style={{ fontSize: 12, opacity: 0.7 }}>格子セル: {fmt(est.gridCells)}</span>
            <span style={{ fontSize: 12, opacity: 0.7 }}>radius: {c.particleRadius}</span>
          </div>
          <div style={{ fontSize: 12, marginTop: 6, color: feasibilityColor(est.level) }}>{est.message}</div>
          {est.suggestedRadius && (
            <button
              style={{ ...ui.button, marginTop: 8, fontSize: 13, padding: "6px 12px" }}
              onClick={() => mutate((s) => (s.Configuration.particleRadius = Number(est.suggestedRadius!.toPrecision(3))))}
            >
              推奨 particleRadius ≈ {est.suggestedRadius.toPrecision(3)} を適用（~10万粒子）
            </button>
          )}
          <div style={{ fontSize: 11, opacity: 0.55, marginTop: 6 }}>
            ※ 剛体メッシュの粒子は voxel 化依存のため未計上（通常は流体が支配的）。
          </div>
        </div>

        <h2 style={ui.h2}>ソルバ</h2>
        <Row label="simulationMethod">
          <select
            value={c.simulationMethod}
            onChange={(e) => mutate((s) => (s.Configuration.simulationMethod = Number(e.target.value)))}
            style={ui.input}
          >
            <option value={0}>0: WCSPH</option>
            <option value={4}>4: DFSPH</option>
          </select>
        </Row>
        <Row label="boundaryHandlingMethod">
          <select
            value={c.boundaryHandlingMethod}
            onChange={(e) => mutate((s) => (s.Configuration.boundaryHandlingMethod = Number(e.target.value)))}
            style={ui.input}
          >
            <option value={0}>0: 衝突ベース（現ソルバ固定）</option>
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </Row>

        <h2 style={ui.h2}>基本パラメータ</h2>
        <Row label="particleRadius">
          <Num value={c.particleRadius} step={0.001} onChange={(v) => mutate((s) => (s.Configuration.particleRadius = v))} />
        </Row>
        <Row label="timeStepSize">
          <Num value={c.timeStepSize} step={0.0001} onChange={(v) => mutate((s) => (s.Configuration.timeStepSize = v))} />
        </Row>
        <Row label="density0">
          <Num value={c.density0} step={1} onChange={(v) => mutate((s) => (s.Configuration.density0 = v))} />
        </Row>
        <Row label="gravitation (x,y,z)">
          <div style={{ display: "flex", gap: 6 }}>
            {[0, 1, 2].map((i) => (
              <Num
                key={i}
                width={70}
                value={c.gravitation[i]}
                step={0.1}
                onChange={(v) => mutate((s) => (s.Configuration.gravitation[i] = v))}
              />
            ))}
          </div>
        </Row>

        <h2 style={ui.h2}>場の物理（流体特性）</h2>
        <Row label="viscosity 粘性">
          <Num value={c.viscosity} step={0.001} onChange={(v) => mutate((s) => (s.Configuration.viscosity = v))} />
        </Row>
        <Row label="surfaceTension 表面張力">
          <Num value={c.surfaceTension} step={0.001} onChange={(v) => mutate((s) => (s.Configuration.surfaceTension = v))} />
        </Row>

        <h2 style={ui.h2}>WCSPH 係数</h2>
        <Row label="stiffness">
          <Num value={c.stiffness} step={100} onChange={(v) => mutate((s) => (s.Configuration.stiffness = v))} />
        </Row>
        <Row label="exponent">
          <Num value={c.exponent} step={1} onChange={(v) => mutate((s) => (s.Configuration.exponent = v))} />
        </Row>

        <h2 style={ui.h2}>計算範囲</h2>
        <Row label="totalTime [s]">
          <Num value={c.totalTime ?? 0} step={0.1} onChange={(v) => mutate((s) => (s.Configuration.totalTime = v))} />
        </Row>
        <Row label="enforceDomainFit">
          <input
            type="checkbox"
            checked={c.enforceDomainFit}
            onChange={(e) => mutate((s) => (s.Configuration.enforceDomainFit = e.target.checked))}
          />
        </Row>

        <div style={{ marginTop: 24, display: "flex", gap: 12 }}>
          <Link href="/scene" style={{ ...ui.button, background: "#30363d", textDecoration: "none" }}>
            ← シーン
          </Link>
          <Link href="/export" style={{ ...ui.button, textDecoration: "none" }}>
            出力設定へ →
          </Link>
        </div>
      </main>
    </>
  );
}

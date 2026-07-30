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

  // Boundary opening / periodic flow (guard for scenes saved before this feature).
  const axisLabels = ["X", "Y", "Z"];
  const periodic = c.periodicBoundary ?? [false, false, false];
  const drive = c.drivingForce ?? [0, 0, 0];
  const anyPeriodic = periodic.some(Boolean);

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

        <h2 style={ui.h2}>境界条件（開放・周期境界）</h2>
        <p style={{ fontSize: 12, opacity: 0.7, margin: "0 0 8px" }}>
          軸ごとに壁を開放して<strong>周期境界（周期計算）</strong>に切り替えられます。ONにした軸では、流出した粒子が反対側から流入して連続的に循環し、
          近傍探索も継ぎ目をまたいで連続します（粒子数は一定）。壁のままの軸は従来どおり衝突境界です。
        </p>
        <Row label="周期境界 ON/OFF（軸ごと）">
          <div style={{ display: "flex", gap: 16 }}>
            {periodic.map((on, i) => (
              <label key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={!!on}
                  onChange={(e) =>
                    mutate((s) => {
                      const cfg = s.Configuration;
                      if (!cfg.periodicBoundary) cfg.periodicBoundary = [false, false, false];
                      cfg.periodicBoundary[i] = e.target.checked;
                    })
                  }
                />
                {axisLabels[i] ?? `axis${i}`} 軸
              </label>
            ))}
          </div>
        </Row>
        <Row label="drivingForce 駆動力 (x,y,z) [m/s²]">
          <div style={{ display: "flex", gap: 6 }}>
            {[0, 1, 2].map((i) => (
              <Num
                key={i}
                width={70}
                value={drive[i] ?? 0}
                step={0.1}
                onChange={(v) =>
                  mutate((s) => {
                    const cfg = s.Configuration;
                    if (!cfg.drivingForce) cfg.drivingForce = [0, 0, 0];
                    cfg.drivingForce[i] = v;
                  })
                }
              />
            ))}
          </div>
        </Row>
        <div style={{ fontSize: 11, opacity: 0.6, marginTop: -2, marginBottom: 8 }}>
          {anyPeriodic
            ? "周期軸に沿って一定の駆動力（圧力勾配相当）を与えると、完全発達流を維持できます。重力OFF＋駆動力で周期チャネル流が作れます。"
            : "周期境界がすべてOFFのときは駆動力のみが働きます（通常は0のままでOK）。"}
        </div>

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

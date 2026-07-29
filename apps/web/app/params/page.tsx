"use client";

import Link from "next/link";
import StepNav from "@/components/StepNav";
import { Row, Num, ui } from "@/components/fields";
import { useSceneStore } from "@/lib/store";

// U10: S2 calculation parameters.
export default function ParamsPage() {
  const { scene, mutate } = useSceneStore();
  const c = scene.Configuration;

  return (
    <>
      <StepNav />
      <main style={ui.page}>
        <h1 style={{ fontSize: 22 }}>計算パラメータ設定</h1>

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

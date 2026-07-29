"use client";

import Link from "next/link";
import StepNav from "@/components/StepNav";
import { Row, Num, ui } from "@/components/fields";
import { useSceneStore } from "@/lib/store";

const FLUID_FIELDS = ["position", "velocity", "density", "pressure"];

// U11: S3 output settings — fluid particles vs object models (separate), interval.
export default function ExportPage() {
  const { scene, mutate } = useSceneStore();
  const exp = scene.Export;

  function toggleFluidField(f: string) {
    mutate((s) => {
      const set = new Set(s.Export.fluid.fields);
      if (set.has(f)) set.delete(f);
      else set.add(f);
      s.Export.fluid.fields = FLUID_FIELDS.filter((x) => set.has(x));
    });
  }

  function setObjectMode(objectId: number, mode: "particles" | "meshVertices" | "off") {
    mutate((s) => {
      s.Export.objects = s.Export.objects.filter((o) => o.objectId !== objectId);
      if (mode !== "off") {
        s.Export.objects.push({ objectId, mode, fields: ["position"], format: "csv" });
      }
    });
  }

  return (
    <>
      <StepNav />
      <main style={ui.page}>
        <h1 style={{ fontSize: 22 }}>出力設定</h1>
        <p style={{ opacity: 0.7, fontSize: 13 }}>
          時間刻みごとに CSV を出力します。流体パーティクルとオブジェクトモデルは別個に追跡します。
        </p>

        <h2 style={ui.h2}>出力間隔</h2>
        <Row label="interval mode">
          <select
            value={exp.interval.mode}
            onChange={(e) =>
              mutate((s) => (s.Export.interval.mode = e.target.value as "steps" | "time"))
            }
            style={ui.input}
          >
            <option value="steps">steps（ステップ数ごと）</option>
            <option value="time">time（シミュレーション時間ごと）</option>
          </select>
        </Row>
        <Row label="interval value">
          <Num
            value={exp.interval.value}
            step={exp.interval.mode === "time" ? 0.01 : 1}
            onChange={(v) => mutate((s) => (s.Export.interval.value = v))}
          />
        </Row>

        <h2 style={ui.h2}>流体パーティクル追跡</h2>
        <Row label="enabled">
          <input
            type="checkbox"
            checked={exp.fluid.enabled}
            onChange={(e) => mutate((s) => (s.Export.fluid.enabled = e.target.checked))}
          />
        </Row>
        <Row label="出力フィールド">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {FLUID_FIELDS.map((f) => (
              <label key={f} style={{ fontSize: 13, display: "flex", gap: 4, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={exp.fluid.fields.includes(f)}
                  onChange={() => toggleFluidField(f)}
                />
                {f}
              </label>
            ))}
          </div>
        </Row>

        <h2 style={ui.h2}>オブジェクトモデル追跡（別個・ユーザー指定）</h2>
        {scene.RigidBodies.map((rb) => {
          const current = exp.objects.find((o) => o.objectId === rb.objectId);
          const mode = current?.mode ?? "off";
          return (
            <Row key={rb.objectId} label={`#${rb.objectId} ${rb.geometryFile.split(/[\\/]/).pop()}`}>
              <select
                value={mode}
                onChange={(e) =>
                  setObjectMode(rb.objectId, e.target.value as "particles" | "meshVertices" | "off")
                }
                style={ui.input}
              >
                <option value="off">追跡しない</option>
                <option value="particles">particles（剛体粒子）</option>
                <option value="meshVertices">meshVertices（メッシュ頂点）</option>
              </select>
            </Row>
          );
        })}

        <div style={{ marginTop: 24, display: "flex", gap: 12 }}>
          <Link href="/params" style={{ ...ui.button, background: "#30363d", textDecoration: "none" }}>
            ← パラメータ
          </Link>
          <Link href="/run" style={{ ...ui.button, textDecoration: "none" }}>
            実行確認へ →
          </Link>
        </div>
      </main>
    </>
  );
}

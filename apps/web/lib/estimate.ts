// Static (pre-run) estimate of the particle/grid budget from a scene, so the user can
// pick a feasible particleRadius before hitting a GPU device-loss / out-of-memory crash.
import type { Scene } from "./schema";

export type Feasibility = "ok" | "warn" | "danger";

export interface Estimate {
  fluidParticles: number; // exact (dominant term)
  gridCells: number; // neighbor-grid cells (memory indicator)
  level: Feasibility;
  message: string;
  // particleRadius that brings the fluid count down to ~TARGET (only when over budget)
  suggestedRadius?: number;
}

// Tuned around the observed failure (~512k particles -> Vulkan device lost on a laptop GPU).
const TARGET = 100_000;
const WARN = 120_000;
const DANGER = 300_000;

function fluidCount(scene: Scene): number {
  const d = 2 * scene.Configuration.particleRadius; // particle diameter
  if (d <= 0) return 0;
  let total = 0;
  for (const b of scene.FluidBlocks) {
    let n = 1;
    for (let i = 0; i < 3; i++) {
      const extent = ((b.end[i] ?? 0) - (b.start[i] ?? 0)) * (b.scale[i] ?? 1);
      n *= Math.max(0, Math.floor(extent / d));
    }
    total += n;
  }
  return total;
}

function gridCount(scene: Scene): number {
  const h = 4 * scene.Configuration.particleRadius; // support radius = grid size
  if (h <= 0) return 0;
  const s = scene.Configuration.domainStart;
  const e = scene.Configuration.domainEnd;
  let n = 1;
  for (let i = 0; i < 3; i++) n *= Math.max(1, Math.ceil(((e[i] ?? 0) - (s[i] ?? 0)) / h));
  return n;
}

export function estimateScene(scene: Scene): Estimate {
  const fluidParticles = fluidCount(scene);
  const gridCells = gridCount(scene);

  let level: Feasibility = "ok";
  let message = "快適に実行できます（GPU/CPU）。";
  let suggestedRadius: number | undefined;

  if (fluidParticles > DANGER) {
    level = "danger";
    message =
      "粒子数が多すぎます。GPU がデバイスロスト/メモリ超過でクラッシュする恐れがあります。" +
      "particleRadius を大きくして粒子を減らすか、CPU 実行（低速）を検討してください。";
    suggestedRadius = scene.Configuration.particleRadius * Math.cbrt(fluidParticles / TARGET);
  } else if (fluidParticles > WARN) {
    level = "warn";
    message = "粒子数が多く、計算に時間がかかります（GPU 推奨）。";
    suggestedRadius = scene.Configuration.particleRadius * Math.cbrt(fluidParticles / TARGET);
  }

  return { fluidParticles, gridCells, level, message, suggestedRadius };
}

export function feasibilityColor(level: Feasibility): string {
  return level === "danger" ? "#e35d5d" : level === "warn" ? "#e3b25d" : "#5de38a";
}

export function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

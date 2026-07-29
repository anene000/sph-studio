// Zustand store holding the editable Scene (shared across S1–S4). U8 wires up S1.
import { create } from "zustand";
import type { Scene, RigidBody, Block } from "./schema";

// A complete default scene (mirrors data/scenes/sample_bunny.json) so the 3D
// preview has something to show on first load.
export const defaultScene: Scene = {
  Configuration: {
    domainStart: [0, 0, 0],
    domainEnd: [1, 1, 1],
    particleRadius: 0.02,
    simulationMethod: 0,
    timeStepSize: 4e-4,
    gravitation: [0, -9.8, 0],
    density0: 1000,
    stiffness: 10000,
    exponent: 5,
    boundaryHandlingMethod: 2,
    enforceDomainFit: true,
    numberOfStepsPerRenderUpdate: 1,
    totalTime: 0.5,
    totalSteps: null,
  },
  RigidBodies: [
    {
      objectId: 1,
      geometryFile: "data/models/bunny_sparse.obj",
      translation: [0.52, 0.19, 0.5],
      scale: [1, 1, 1],
      rotationAxis: [0, 1, 0],
      rotationAngle: 0,
      velocity: [0, 0, 0],
      density: 1000,
      color: [230, 230, 230],
      isDynamic: false,
    },
  ],
  FluidBlocks: [
    {
      objectId: 0,
      start: [0.1, 0.55, 0.1],
      end: [0.4, 0.9, 0.4],
      translation: [0, 0, 0],
      scale: [1, 1, 1],
      velocity: [0, 0, 0],
      density: 1000,
      color: [50, 100, 200],
      isDynamic: false,
    },
  ],
  RigidBlocks: [],
  Export: {
    outputDir: null,
    interval: { mode: "steps", value: 40 },
    fluid: {
      enabled: true,
      objectIds: null,
      fields: ["position", "velocity", "density", "pressure"],
      format: "csv",
    },
    objects: [{ objectId: 1, mode: "particles", fields: ["position"], format: "csv" }],
    ply: false,
    obj: false,
  },
};

export type ValidationIssue = {
  objectId: number;
  level: "info" | "warn" | "error";
  message: string;
  recommendedScaleUniform?: number[];
  recommendedScalePerAxis?: number[];
  objectSize?: number[];
  domainSize?: number[];
};

interface SceneStore {
  scene: Scene;
  issues: ValidationIssue[];
  setScene: (scene: Scene) => void;
  setDomain: (which: "domainStart" | "domainEnd", axis: number, value: number) => void;
  updateRigidBody: (index: number, patch: Partial<RigidBody>) => void;
  setRigidVec: (
    index: number,
    key: "translation" | "scale",
    axis: number,
    value: number
  ) => void;
  updateFluidBlock: (index: number, patch: Partial<Block>) => void;
  setIssues: (issues: ValidationIssue[]) => void;
  // Generic draft mutation for the params / export screens.
  mutate: (fn: (scene: Scene) => void) => void;
}

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}

export const useSceneStore = create<SceneStore>((set) => ({
  scene: clone(defaultScene),
  issues: [],
  setScene: (scene) => set({ scene }),
  setDomain: (which, axis, value) =>
    set((s) => {
      const scene = clone(s.scene);
      scene.Configuration[which][axis] = value;
      return { scene };
    }),
  updateRigidBody: (index, patch) =>
    set((s) => {
      const scene = clone(s.scene);
      scene.RigidBodies[index] = { ...scene.RigidBodies[index], ...patch };
      return { scene };
    }),
  setRigidVec: (index, key, axis, value) =>
    set((s) => {
      const scene = clone(s.scene);
      scene.RigidBodies[index][key][axis] = value;
      return { scene };
    }),
  updateFluidBlock: (index, patch) =>
    set((s) => {
      const scene = clone(s.scene);
      scene.FluidBlocks[index] = { ...scene.FluidBlocks[index], ...patch };
      return { scene };
    }),
  setIssues: (issues) => set({ issues }),
  mutate: (fn) =>
    set((s) => {
      const scene = clone(s.scene);
      fn(scene);
      return { scene };
    }),
}));

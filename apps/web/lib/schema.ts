// Zod schema mirroring backend/app/models.py (keep the two in sync).
import { z } from "zod";

const Vec3 = z.array(z.number());

export const ConfigurationSchema = z
  .object({
    domainStart: Vec3,
    domainEnd: Vec3,
    particleRadius: z.number().default(0.01),
    simulationMethod: z.number().int().default(0), // 0=WCSPH, 4=DFSPH
    timeStepSize: z.number().default(4e-4),
    gravitation: Vec3.default([0, -9.81, 0]),
    density0: z.number().default(1000),
    stiffness: z.number().default(50000),
    exponent: z.number().default(7),
    // Field physics (now solver-configurable).
    viscosity: z.number().default(0.01),
    surfaceTension: z.number().default(0.01),
    boundaryHandlingMethod: z.number().int().default(0),
    // Boundary opening / periodic flow (per-axis, length = dim).
    // periodicBoundary[d]=true opens axis d as a periodic boundary (no wall,
    // recirculating flow, minimum-image neighbor wrap). drivingForce[d] is a
    // constant acceleration (m/s^2) added to fluid to drive the periodic flow.
    periodicBoundary: z.array(z.boolean()).default([false, false, false]),
    drivingForce: Vec3.default([0, 0, 0]),
    enforceDomainFit: z.boolean().default(true),
    numberOfStepsPerRenderUpdate: z.number().int().default(1),
    totalTime: z.number().nullable().default(5),
    totalSteps: z.number().int().nullable().default(null),
  })
  .passthrough()
  .refine(
    (c) => c.domainStart.length === c.domainEnd.length,
    { message: "domainStart and domainEnd must have the same length" }
  )
  .refine(
    (c) => c.domainStart.every((a, i) => c.domainEnd[i] > a),
    { message: "domainEnd must be strictly greater than domainStart on every axis" }
  )
  .refine(
    (c) => c.periodicBoundary.length === c.domainStart.length,
    { message: "periodicBoundary must have one flag per axis" }
  )
  .refine(
    (c) => c.drivingForce.length === c.domainStart.length,
    { message: "drivingForce must have one component per axis" }
  );

export const RigidBodySchema = z
  .object({
    objectId: z.number().int(),
    geometryFile: z.string(),
    translation: Vec3.default([0, 0, 0]),
    scale: Vec3.default([1, 1, 1]),
    rotationAxis: Vec3.default([0, 0, 0]),
    rotationAngle: z.number().default(0),
    velocity: Vec3.default([0, 0, 0]),
    density: z.number().default(1000),
    color: z.array(z.number().int()).default([255, 255, 255]),
    isDynamic: z.boolean().default(false),
  })
  .passthrough();

export const BlockSchema = z
  .object({
    objectId: z.number().int(),
    start: Vec3,
    end: Vec3,
    translation: Vec3.default([0, 0, 0]),
    scale: Vec3.default([1, 1, 1]),
    velocity: Vec3.default([0, 0, 0]),
    density: z.number().default(1000),
    color: z.array(z.number().int()).default([50, 100, 200]),
    isDynamic: z.boolean().default(false),
  })
  .passthrough();

export const ExportConfigSchema = z
  .object({
    outputDir: z.string().nullable().optional(),
    interval: z
      .object({
        mode: z.enum(["steps", "time"]).default("steps"),
        value: z.number().default(40),
      })
      .default({ mode: "steps", value: 40 }),
    fluid: z
      .object({
        enabled: z.boolean().default(true),
        objectIds: z.array(z.number().int()).nullable().default(null),
        fields: z.array(z.string()).default(["position", "velocity", "density", "pressure"]),
        format: z.literal("csv").default("csv"),
      })
      .default({}),
    objects: z
      .array(
        z.object({
          objectId: z.number().int(),
          mode: z.enum(["particles", "meshVertices"]).default("particles"),
          fields: z.array(z.string()).default(["position"]),
          format: z.literal("csv").default("csv"),
        })
      )
      .default([]),
    ply: z.boolean().default(false),
    obj: z.boolean().default(false),
  })
  .passthrough();

export const SceneSchema = z
  .object({
    Configuration: ConfigurationSchema,
    RigidBodies: z.array(RigidBodySchema).default([]),
    FluidBlocks: z.array(BlockSchema).default([]),
    RigidBlocks: z.array(BlockSchema).default([]),
    Export: ExportConfigSchema.default({}),
  })
  .passthrough();

export type Scene = z.infer<typeof SceneSchema>;
export type Configuration = z.infer<typeof ConfigurationSchema>;
export type RigidBody = z.infer<typeof RigidBodySchema>;
export type Block = z.infer<typeof BlockSchema>;
export type ExportConfig = z.infer<typeof ExportConfigSchema>;

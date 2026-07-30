"use client";

import { Suspense, useEffect, useMemo } from "react";
import { Canvas, useLoader } from "@react-three/fiber";
import { OrbitControls, Edges, GizmoHelper, GizmoViewport } from "@react-three/drei";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import * as THREE from "three";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { api } from "@/lib/api";
import type { Scene, RigidBody, Block } from "@/lib/schema";

function center(a: number[], b: number[]): [number, number, number] {
  return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2];
}
function size(a: number[], b: number[]): [number, number, number] {
  return [Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]), Math.abs(b[2] - a[2])];
}

function DomainBox({ start, end }: { start: number[]; end: number[] }) {
  return (
    <mesh position={center(start, end)}>
      <boxGeometry args={size(start, end)} />
      <meshBasicMaterial transparent opacity={0.03} color="#88aaff" />
      <Edges color="#f5a742" />
    </mesh>
  );
}

function FluidBox({ block }: { block: Block }) {
  const s = block.start.map((v, i) => v + block.translation[i]);
  const e = block.end.map((v, i) => v + block.translation[i]);
  const col = `rgb(${block.color[0]},${block.color[1]},${block.color[2]})`;
  return (
    <mesh position={center(s, e)}>
      <boxGeometry args={size(s, e)} />
      <meshStandardMaterial transparent opacity={0.28} color={col} />
    </mesh>
  );
}

// Basename so "data/models/bunny_sparse.obj" -> "bunny_sparse.obj" for the API URL.
function basename(p: string): string {
  return p.split(/[\\/]/).pop() || p;
}

function RigidMesh({ rb }: { rb: RigidBody }) {
  const url = api.modelUrl(basename(rb.geometryFile));
  const obj = useLoader(OBJLoader, url);

  // Clone + recolor (useLoader caches the source object).
  const object = useMemo(() => {
    const clone = obj.clone(true);
    const color = new THREE.Color(rb.color[0] / 255, rb.color[1] / 255, rb.color[2] / 255);
    clone.traverse((c) => {
      const m = c as THREE.Mesh;
      if (m.isMesh) m.material = new THREE.MeshStandardMaterial({ color, flatShading: true });
    });
    return clone;
  }, [obj, rb.color]);

  // Solver placement is scale-about-origin then translate (rotation about centroid).
  // For angle=0 this is exact; with rotation it is a close preview approximation.
  const quat = useMemo(() => {
    const axis = new THREE.Vector3(rb.rotationAxis[0], rb.rotationAxis[1], rb.rotationAxis[2]);
    if (axis.lengthSq() < 1e-9 || !rb.rotationAngle) return new THREE.Quaternion();
    return new THREE.Quaternion().setFromAxisAngle(
      axis.normalize(),
      (rb.rotationAngle / 180) * Math.PI
    );
  }, [rb.rotationAxis, rb.rotationAngle]);

  return (
    <primitive
      object={object}
      scale={rb.scale as [number, number, number]}
      position={rb.translation as [number, number, number]}
      quaternion={[quat.x, quat.y, quat.z, quat.w]}
    />
  );
}

export default function Viewer3D({ scene }: { scene: Scene }) {
  const c = center(scene.Configuration.domainStart, scene.Configuration.domainEnd);
  const sz = size(scene.Configuration.domainStart, scene.Configuration.domainEnd);
  const diag = Math.max(0.5, Math.hypot(sz[0], sz[1], sz[2]));
  const camPos: [number, number, number] = [c[0] + diag * 1.1, c[1] + diag * 0.9, c[2] + diag * 1.4];

  // On client-side navigation the r3f Canvas can mount before its container is measured
  // and stick at the default 300x150. Nudge a resize after mount so it fills the panel.
  useEffect(() => {
    const t = setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
    return () => clearTimeout(t);
  }, []);

  return (
    <Canvas camera={{ position: camPos, fov: 45, near: 0.01, far: diag * 50 }}>
      <color attach="background" args={["#0b0e14"]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[c[0] + diag, c[1] + diag * 2, c[2] + diag]} intensity={1.1} />

      <DomainBox
        start={scene.Configuration.domainStart}
        end={scene.Configuration.domainEnd}
      />
      {scene.FluidBlocks.map((b, i) => (
        <FluidBox key={`f${i}`} block={b} />
      ))}
      {scene.RigidBodies.map((rb, i) => (
        // Per-mesh boundary: a missing/failed .obj (e.g. 404) shows nothing instead of
        // throwing out of the Canvas and crashing the app. Suspense handles the pending load.
        <ErrorBoundary key={`r${i}-${rb.geometryFile}`} fallback={null}>
          <Suspense fallback={null}>
            <RigidMesh rb={rb} />
          </Suspense>
        </ErrorBoundary>
      ))}

      <OrbitControls target={c} makeDefault />
      <GizmoHelper alignment="bottom-right" margin={[60, 60]}>
        <GizmoViewport axisColors={["#e35d5d", "#5de35d", "#5d7de3"]} labelColor="white" />
      </GizmoHelper>
    </Canvas>
  );
}

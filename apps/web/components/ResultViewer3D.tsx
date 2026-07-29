"use client";

import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

function pointsObject(pts: number[][], color: string, size: number) {
  const geom = new THREE.BufferGeometry();
  const arr = new Float32Array(pts.length * 3);
  for (let i = 0; i < pts.length; i++) {
    arr[i * 3] = pts[i][0];
    arr[i * 3 + 1] = pts[i][1];
    arr[i * 3 + 2] = pts[i][2];
  }
  geom.setAttribute("position", new THREE.BufferAttribute(arr, 3));
  const mat = new THREE.PointsMaterial({ color, size, sizeAttenuation: true });
  return new THREE.Points(geom, mat);
}

export default function ResultViewer3D({
  fluid,
  objects,
}: {
  fluid: number[][];
  objects: Record<string, number[][]>;
}) {
  const all = useMemo(() => {
    const objPts = Object.values(objects).flat();
    return [...fluid, ...objPts];
  }, [fluid, objects]);

  const { center, diag } = useMemo(() => {
    if (all.length === 0) return { center: [0.5, 0.5, 0.5] as number[], diag: 1 };
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (const p of all)
      for (let d = 0; d < 3; d++) {
        min[d] = Math.min(min[d], p[d]);
        max[d] = Math.max(max[d], p[d]);
      }
    const center = [0, 1, 2].map((d) => (min[d] + max[d]) / 2);
    const diag = Math.max(0.3, Math.hypot(max[0] - min[0], max[1] - min[1], max[2] - min[2]));
    return { center, diag };
  }, [all]);

  const fluidObj = useMemo(() => pointsObject(fluid, "#4aa3ff", diag * 0.012), [fluid, diag]);
  const objObjs = useMemo(
    () => Object.values(objects).map((pts) => pointsObject(pts, "#e6e6e6", diag * 0.014)),
    [objects, diag]
  );

  const cam: [number, number, number] = [center[0] + diag, center[1] + diag * 0.8, center[2] + diag * 1.3];

  return (
    <Canvas camera={{ position: cam, fov: 45, near: 0.01, far: diag * 50 }}>
      <color attach="background" args={["#0b0e14"]} />
      <primitive object={fluidObj} />
      {objObjs.map((o, i) => (
        <primitive key={i} object={o} />
      ))}
      <OrbitControls target={center as [number, number, number]} makeDefault />
    </Canvas>
  );
}

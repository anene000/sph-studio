"use client";

import { useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Edges, Grid, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

type Domain = { start: number[]; end: number[] };

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

// Blue -> cyan -> green -> yellow -> red colormap for a normalized value t in [0,1].
function colormap(t: number): [number, number, number] {
  const c = Math.min(1, Math.max(0, t)) * 4;
  if (c < 1) return [0, c, 1];
  if (c < 2) return [0, 1, 2 - c];
  if (c < 3) return [c - 2, 1, 0];
  return [1, 4 - c, 0];
}

function coloredPointsObject(pts: number[][], scalar: number[], lo: number, hi: number, size: number) {
  const geom = new THREE.BufferGeometry();
  const pos = new Float32Array(pts.length * 3);
  const col = new Float32Array(pts.length * 3);
  const span = hi - lo > 1e-12 ? hi - lo : 1;
  for (let i = 0; i < pts.length; i++) {
    pos[i * 3] = pts[i][0];
    pos[i * 3 + 1] = pts[i][1];
    pos[i * 3 + 2] = pts[i][2];
    const [r, g, b] = colormap((scalar[i] - lo) / span);
    col[i * 3] = r;
    col[i * 3 + 1] = g;
    col[i * 3 + 2] = b;
  }
  geom.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geom.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const mat = new THREE.PointsMaterial({ size, sizeAttenuation: true, vertexColors: true });
  return new THREE.Points(geom, mat);
}

export default function ResultViewer3D({
  fluid,
  objects,
  domain,
  fluidScalar,
  scalarRange,
}: {
  fluid: number[][];
  objects: Record<string, number[][]>;
  domain?: Domain;
  fluidScalar?: number[];
  scalarRange?: [number, number];
}) {
  const all = useMemo(() => [...fluid, ...Object.values(objects).flat()], [fluid, objects]);

  // Frame the view on the FIXED analysis space when known, so the camera/grid stay put
  // across frames instead of tracking the moving point cloud.
  const { center, size, diag } = useMemo(() => {
    let min = [0, 0, 0];
    let max = [1, 1, 1];
    if (domain) {
      min = domain.start;
      max = domain.end;
    } else if (all.length) {
      min = [Infinity, Infinity, Infinity];
      max = [-Infinity, -Infinity, -Infinity];
      for (const p of all)
        for (let d = 0; d < 3; d++) {
          min[d] = Math.min(min[d], p[d]);
          max[d] = Math.max(max[d], p[d]);
        }
    }
    const center = [0, 1, 2].map((d) => (min[d] + max[d]) / 2);
    const size = [0, 1, 2].map((d) => Math.abs(max[d] - min[d]));
    const diag = Math.max(0.3, Math.hypot(size[0], size[1], size[2]));
    return { center, size, diag };
  }, [domain, all]);

  const useColormap = !!fluidScalar && fluidScalar.length === fluid.length && fluid.length > 0;
  const fluidObj = useMemo(() => {
    if (useColormap) {
      const lo = scalarRange ? scalarRange[0] : Math.min(...fluidScalar!);
      const hi = scalarRange ? scalarRange[1] : Math.max(...fluidScalar!);
      return coloredPointsObject(fluid, fluidScalar!, lo, hi, diag * 0.012);
    }
    return pointsObject(fluid, "#4aa3ff", diag * 0.012);
  }, [fluid, fluidScalar, scalarRange, useColormap, diag]);
  const objObjs = useMemo(
    () => Object.values(objects).map((pts) => pointsObject(pts, "#e6e6e6", diag * 0.014)),
    [objects, diag]
  );

  const cam: [number, number, number] = [center[0] + diag, center[1] + diag * 0.8, center[2] + diag * 1.3];

  useEffect(() => {
    const t = setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
    return () => clearTimeout(t);
  }, []);

  return (
    <Canvas camera={{ position: cam, fov: 45, near: 0.01, far: diag * 50 }}>
      <color attach="background" args={["#0b0e14"]} />

      {/* Fixed analysis-space grid + wireframe box (always shown when the domain is known). */}
      {domain && (
        <>
          <mesh position={center as [number, number, number]}>
            <boxGeometry args={size as [number, number, number]} />
            <meshBasicMaterial transparent opacity={0.02} color="#88aaff" />
            <Edges color="#f5a742" />
          </mesh>
          <Grid
            position={[center[0], domain.start[1], center[2]]}
            args={[size[0], size[2]]}
            cellSize={Math.max(size[0], size[2]) / 10}
            sectionSize={Math.max(size[0], size[2]) / 2}
            cellColor="#22303f"
            sectionColor="#3a4a5f"
            infiniteGrid={false}
            fadeDistance={diag * 8}
          />
        </>
      )}

      <primitive object={fluidObj} />
      {objObjs.map((o, i) => (
        <primitive key={i} object={o} />
      ))}
      <OrbitControls target={center as [number, number, number]} makeDefault />
    </Canvas>
  );
}

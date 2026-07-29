"use client";

import type { ReactNode } from "react";

export const ui = {
  page: { maxWidth: 760, margin: "0 auto", padding: "24px" } as React.CSSProperties,
  h2: { fontSize: 15, margin: "20px 0 10px" } as React.CSSProperties,
  input: {
    width: 110,
    background: "#111725",
    border: "1px solid #263041",
    color: "#e6e6e6",
    borderRadius: 4,
    padding: "5px 7px",
    fontSize: 13,
  } as React.CSSProperties,
  button: {
    padding: "9px 16px",
    background: "#1f6feb",
    color: "white",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 14,
  } as React.CSSProperties,
  card: {
    border: "1px solid #263041",
    borderRadius: 8,
    padding: 14,
    marginBottom: 12,
    background: "#111725",
  } as React.CSSProperties,
};

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
      <span style={{ width: 190, fontSize: 13, opacity: 0.85 }}>{label}</span>
      {children}
    </div>
  );
}

const AXES = ["x", "y", "z"];

export function Vec3Edit({
  value,
  onChange,
  step = 0.01,
}: {
  value: number[];
  onChange: (axis: number, v: number) => void;
  step?: number;
}) {
  return (
    <div style={{ display: "flex", gap: 5 }}>
      {AXES.map((ax, i) => (
        <label key={ax} style={{ display: "flex", alignItems: "center", gap: 2 }}>
          <span style={{ fontSize: 10, opacity: 0.5 }}>{ax}</span>
          <input
            type="number"
            step={step}
            value={Number.isFinite(value[i]) ? value[i] : 0}
            onChange={(e) => onChange(i, parseFloat(e.target.value))}
            style={{ ...ui.input, width: 62 }}
          />
        </label>
      ))}
    </div>
  );
}

export function ColorEdit({
  value,
  onChange,
}: {
  value: number[];
  onChange: (rgb: number[]) => void;
}) {
  const hex =
    "#" +
    value
      .slice(0, 3)
      .map((c) => Math.max(0, Math.min(255, Math.round(c))).toString(16).padStart(2, "0"))
      .join("");
  return (
    <input
      type="color"
      value={hex}
      onChange={(e) => {
        const h = e.target.value;
        onChange([parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]);
      }}
      style={{ width: 40, height: 26, background: "transparent", border: "1px solid #263041", borderRadius: 4 }}
    />
  );
}

export function Num({
  value,
  onChange,
  step = 0.01,
  width,
}: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  width?: number;
}) {
  return (
    <input
      type="number"
      step={step}
      value={Number.isFinite(value) ? value : 0}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      style={{ ...ui.input, ...(width ? { width } : null) }}
    />
  );
}

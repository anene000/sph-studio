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

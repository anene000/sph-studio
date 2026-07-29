"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const STEPS = [
  { href: "/scene", label: "S1 シーン" },
  { href: "/params", label: "S2 パラメータ" },
  { href: "/export", label: "S3 出力" },
  { href: "/run", label: "S4 実行" },
];

export default function StepNav() {
  const path = usePathname();
  return (
    <nav
      style={{
        display: "flex",
        gap: 8,
        padding: "10px 16px",
        borderBottom: "1px solid #263041",
        background: "#0e1420",
        alignItems: "center",
      }}
    >
      <Link href="/" style={{ fontSize: 12, opacity: 0.7, marginRight: 8 }}>
        SPH Studio
      </Link>
      {STEPS.map((s) => {
        const active = path === s.href;
        return (
          <Link
            key={s.href}
            href={s.href}
            style={{
              fontSize: 13,
              padding: "5px 12px",
              borderRadius: 6,
              textDecoration: "none",
              color: active ? "white" : "#9fb0c8",
              background: active ? "#1f6feb" : "transparent",
              border: active ? "none" : "1px solid #263041",
            }}
          >
            {s.label}
          </Link>
        );
      })}
    </nav>
  );
}

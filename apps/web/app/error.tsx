"use client";

import Link from "next/link";

// App Router error boundary: any uncaught client-side render error in a route is caught
// here and shown with its message (+ retry) instead of the opaque "Application error".
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: 24 }}>
      <h2 style={{ fontSize: 18 }}>画面の表示中にエラーが発生しました</h2>
      <pre
        style={{
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          color: "#f2b8b8",
          background: "#0b0e14",
          border: "1px solid #263041",
          borderRadius: 8,
          padding: 12,
          fontSize: 12,
        }}
      >
        {error?.message || String(error)}
        {error?.digest ? `\n(digest: ${error.digest})` : ""}
      </pre>
      <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
        <button
          onClick={() => reset()}
          style={{ padding: "8px 14px", background: "#1f6feb", color: "white", border: "none", borderRadius: 6, cursor: "pointer" }}
        >
          再試行
        </button>
        <Link
          href="/"
          style={{ padding: "8px 14px", background: "#30363d", color: "#e6e6e6", borderRadius: 6, textDecoration: "none" }}
        >
          ホームへ
        </Link>
      </div>
    </main>
  );
}

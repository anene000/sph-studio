"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ui } from "@/components/fields";

type Info = { repoRoot: string; modelsDir: string; outputsDir: string; python: string; arch: string };

// S7 environment settings (U15). Read-only in Phase A (separate-process backend).
export default function SettingsPage() {
  const [info, setInfo] = useState<Info | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  useEffect(() => {
    api.info().then(setInfo).catch((e) => setErr(String(e)));
  }, []);

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: 24 }}>
      <Link href="/" style={{ fontSize: 12, opacity: 0.7 }}>← ホーム</Link>
      <h1 style={{ fontSize: 22 }}>環境設定</h1>
      <p style={{ fontSize: 13, opacity: 0.7 }}>
        Phase A（Python 別プロセス起動）では読み取り専用の情報表示です。値の変更は起動時の環境変数／引数で行います。
      </p>

      <section style={card}>
        <Row k="API ベース URL" v={apiBase} />
        <Row k="バックエンド" v={err ? `未接続（${err}）` : info ? "接続 OK" : "確認中…"} />
      </section>

      {info && (
        <section style={card}>
          <Row k="リポジトリルート" v={info.repoRoot} />
          <Row k="モデルディレクトリ" v={info.modelsDir} />
          <Row k="出力ディレクトリ" v={info.outputsDir} />
          <Row k="Python" v={info.python} />
          <Row k="ソルバ arch (SPH_ARCH)" v={info.arch} />
        </section>
      )}

      <section style={card}>
        <strong style={{ fontSize: 13 }}>起動方法（参考）</strong>
        <pre style={pre}>
{`# backend
python -m uvicorn app.main:app --port 8000 --app-dir backend
# CPU 実行を強制する場合
SPH_ARCH=cpu python -m uvicorn app.main:app --port 8000 --app-dir backend

# frontend
pnpm --filter web dev`}
        </pre>
        <p style={{ fontSize: 12, opacity: 0.6, margin: 0 }}>
          フロントの接続先を変えるには <code>NEXT_PUBLIC_API_BASE</code> を設定してビルド／起動します。
        </p>
      </section>
    </main>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "6px 0", borderBottom: "1px solid #1c2534" }}>
      <span style={{ width: 200, fontSize: 13, opacity: 0.75 }}>{k}</span>
      <span style={{ fontSize: 13, fontFamily: "monospace", wordBreak: "break-all" }}>{v}</span>
    </div>
  );
}

const card: React.CSSProperties = { ...ui.card, marginTop: 16 };
const pre: React.CSSProperties = {
  background: "#0b0e14",
  border: "1px solid #263041",
  borderRadius: 6,
  padding: 10,
  fontSize: 12,
  overflowX: "auto",
  margin: "8px 0",
};

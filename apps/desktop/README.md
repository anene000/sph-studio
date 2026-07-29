# SPH Studio — Desktop shell (Tauri v2)

Phase B: bundles the statically-exported Next.js frontend (`apps/web/out`) into a
native window, and (U19) will embed the FastAPI backend as a Tauri **sidecar**.

> Building requires the **Rust toolchain** (not needed for Phase A / web development).

## 前提

- Rust（`rustup`）と各 OS の WebView 依存（Linux: `webkit2gtk`／Windows: WebView2／
  macOS: Xcode CLT）。詳細は https://tauri.app のガイド参照。
- Node.js + pnpm（フロントの静的エクスポート用）。
- アイコン: 初回のみ生成が必要。
  ```bash
  # 任意の 512px 以上 PNG から各サイズを生成（src-tauri/icons/ に出力）
  pnpm --dir apps/desktop exec tauri icon path/to/source.png
  ```

## 開発

```bash
pnpm --dir apps/desktop install          # @tauri-apps/cli
pnpm --dir apps/desktop tauri dev        # devUrl=http://localhost:3000 を WebView 表示
# 別ターミナルでバックエンドを起動しておく（Phase A と同様）
```

## ビルド（配布物）

```bash
# フロントの静的出力を生成 → Tauri が ../../web/out をバンドル
pnpm --filter web build
pnpm --dir apps/desktop tauri build      # OS 別インストーラを生成
```

## 構成

```
apps/desktop/
├─ package.json                 # @tauri-apps/cli
└─ src-tauri/
   ├─ tauri.conf.json           # frontendDist=../../web/out, devUrl, windows
   ├─ Cargo.toml / build.rs
   ├─ src/main.rs, src/lib.rs   # run(): WebView 起動（U19 で sidecar 追加）
   ├─ capabilities/default.json
   └─ icons/                    # `tauri icon` で生成（未コミット）
```

## 次の作業（U19 / U20）

- **U19**: `tauri-plugin-shell` で Python(FastAPI) を PyInstaller 化した `sph-backend`
  をサイドカー起動・終了管理（`bundle.externalBin` + `src/lib.rs` の setup）。
- **U20**: OS 別ビルドを CI マトリクスで生成し、Release に添付。

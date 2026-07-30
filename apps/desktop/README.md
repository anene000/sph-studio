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

## サイドカー（U19: Python バックエンド同梱）

バックエンドは PyInstaller で 1 バイナリ `sph-backend` 化し、Tauri サイドカーとして
起動・終了する（`src/lib.rs` の `tauri-plugin-shell` + `setup`/`ExitRequested`）。
`sph-backend` はサーバ／ソルバの 2 モードを持つ統一エントリ（`backend/run_server.py`、
frozen 時は `--run-solver` で自己再呼び出し）。サイドカー未バンドル時は外部起動した
バックエンドにフォールバックするため、開発時はそのまま動く。

フル同梱ビルド:
```bash
# 1) サイドカー生成（OS 別）
bash scripts/build_sidecar.sh          # Windows: pwsh scripts/build_sidecar.ps1
# → apps/desktop/src-tauri/binaries/sph-backend-<target-triple>[.exe]
# 2) tauri.conf.json の bundle に "externalBin": ["binaries/sph-backend"] を追加
# 3) ビルド
pnpm --dir apps/desktop tauri build
```

## 配布（U20: OS 別 Release CI）

`.github/workflows/release.yml`（`v*` タグ / 手動トリガ）が ubuntu/windows/macos で
サイドカー生成 → `externalBin` 有効化 → `tauri build` を実行し、`tauri-action` で
Release（下書き）に成果物を添付する。通常 push では走らない（`ci.yml` の緑を維持）。

> Taichi の PyInstaller 同梱は環境依存が大きく、各 OS での初回は spec の hidden import /
> データ収集の調整が必要になり得る（`backend/sph-backend.spec`）。

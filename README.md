# SPH Studio

Taichi ベースの SPH（流体・剛体連成）シミュレータに GUI を付けたデスクトップアプリ。
設定（解析空間・オブジェクト・計算パラメータ・出力）を GUI で編集し、ソルバをヘッドレス
実行して進捗表示・3D 再生・CSV 出力を行う。

- フロント: **TypeScript + Next.js**（react-three-fiber で 3D）
- バックエンド: **Python + FastAPI**（ソルバをジョブ単位のサブプロセスで起動）
- ソルバ: **Taichi**（既存コードをヘッドレス化）
- 配布: 初期は Python を別プロセス起動、最終的に **Tauri + PyInstaller** で 1 アプリ同梱

> 開発計画は [`docs/`](docs/) を参照（仕様書・機能一覧・画面遷移図・実装計画）。
> 実装は [`docs/07_実装計画_トークン制限対応.md`](docs/07_実装計画_トークン制限対応.md) のユニット順に進める。

---

## リポジトリ構成

```
sph-studio/
├─ apps/
│  ├─ web/        # Next.js + TypeScript フロント
│  └─ desktop/    # Tauri（Phase B で追加）
├─ backend/       # FastAPI サイドカー（ジョブ管理・API）
├─ solver/        # Taichi ソルバ + run_headless.py
├─ data/          # サンプルシーン / モデル
├─ docs/          # 設計・計画文書
└─ scripts/       # 開発補助スクリプト
```

---

## 必要環境

| 種別 | 推奨 |
|------|------|
| Node.js | 20 以上（開発は 24 で確認） |
| pnpm | 9 以上（`corepack enable` で導入可） |
| Python | 3.10〜3.12 |
| GPU | Vulkan 対応（無ければ CPU フォールバック） |

---

## セットアップと起動（Phase A: 別プロセス起動）

### Linux

```bash
# 1) 取得
git clone https://github.com/anene000/sph-studio.git
cd sph-studio

# 2) フロント依存
corepack enable
pnpm install

# 3) Python 環境（backend + solver）
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r solver/requirements.txt

# 4) バックエンド起動（別ターミナル）
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend

# 5) フロント起動（別ターミナル）
pnpm --filter web dev
# → http://localhost:3000
```

### Windows（PowerShell）

```powershell
git clone https://github.com/anene000/sph-studio.git
cd sph-studio

corepack enable
pnpm install

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt -r solver/requirements.txt

# バックエンド（別ウィンドウ）
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend

# フロント（別ウィンドウ）
pnpm --filter web dev
```

> GPU が無い／Vulkan が使えない環境では、ソルバは自動で CPU にフォールバックします。
> 明示的に CPU 実行したい場合は環境変数 `SPH_ARCH=cpu` を設定してください。

---

## ソルバ単体のヘッドレス実行

```bash
python solver/run_headless.py \
  --scene_file data/scenes/sample_bunny.json \
  --output_dir outputs/sample
```

- 進捗は標準出力に JSON Lines（`{"type":"progress",...}`）で出力。
- `Export` 設定に従い、`outputs/<...>/` に **流体 CSV** と **オブジェクト CSV** を時間刻みごとに出力。
- 解析空間よりオブジェクトが大きい場合は **推奨倍率**を出力して異常終了（`enforceDomainFit`）。

---

## 設定ファイル（scene.json）

`Configuration` / `RigidBodies` / `FluidBlocks` / `RigidBlocks` に加え、出力設定 `Export` を持つ。
詳細は [`docs/03_開発仕様書.md`](docs/03_開発仕様書.md) の §4 を参照。GUI の②〜⑥操作で自動生成される。

---

## モデルデータ（.obj）

サイズの大きい `.obj` はリポジトリに含めていません（`data/models/README.md` 参照）。
`bunny_sparse.obj` のみサンプルとして同梱しています。

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| `taichi` が Vulkan で起動しない | `SPH_ARCH=cpu` で CPU 実行 |
| `OBJECT DOES NOT FIT ANALYSIS SPACE` で停止 | 出力された推奨倍率に `scale` を変更、または `Configuration.enforceDomainFit=false` |
| ボクセル化で粒子 0 個 | `scale` を大きく、または `particleRadius` を小さく |

---

## ライセンス

MIT License（[LICENSE](LICENSE)）。

# SPH Studio

Taichi ベースの SPH（流体・剛体連成）シミュレータに GUI を付けたデスクトップアプリ。
解析空間・流体ブロック・剛体・計算パラメータ・出力を GUI で編集し、ソルバをヘッドレス
実行して進捗表示・3D 再生・時系列 CSV 出力を行う。

- フロント: **TypeScript + Next.js**（react-three-fiber で 3D プレビュー／結果再生）
- バックエンド: **Python + FastAPI**（ソルバをジョブ単位のサブプロセスで起動）
- ソルバ: **Taichi**（WCSPH / DFSPH、ヘッドレス化）
- 配布: 初期は Python を別プロセス起動、最終的に **Tauri + PyInstaller** で 1 アプリ同梱（Phase B）

> 設計・計画・テスト文書は [`docs/`](docs/) 参照（仕様書・機能一覧・画面遷移図・実装計画・
> 非機能/UXテスト計画と結果）。

---

## リポジトリ構成

```
sph-studio/
├─ apps/web/      # Next.js + TypeScript フロント（S0–S7 画面）
├─ backend/       # FastAPI（config/jobs/results API・WebSocket 進捗）
│  ├─ app/        #   main.py, models.py(Pydantic), jobs.py, config_io.py, results.py
│  └─ tests/      #   pytest（schema / samples / e2e）
├─ solver/        # Taichi ソルバ + run_headless.py（GGUI 非依存）
├─ data/          # サンプルシーン(data/scenes) / モデル(data/models)
├─ docs/          # 設計・計画・テスト文書
└─ scripts/       # benchmark.py など補助スクリプト
```

---

## 必要環境

| 種別 | 推奨 |
|------|------|
| Node.js | 20 以上（開発は 24 で確認） |
| pnpm | 9 以上（`corepack enable` で導入可） |
| Python | 3.10〜3.12 |
| GPU | Vulkan 対応（無ければ CPU フォールバック） |

依存は再現性のためバージョン固定（`==`）。フロントは `pnpm-lock.yaml`、Python は
`backend/requirements.txt`・`solver/requirements.txt`・`backend/requirements-dev.txt`。

---

## セットアップと起動（Phase A: 別プロセス起動）

### Linux

```bash
git clone https://github.com/anene000/sph-studio.git
cd sph-studio

# フロント依存
corepack enable
pnpm install

# Python 環境（backend + solver）
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r solver/requirements.txt

# バックエンド（別ターミナル）
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend

# フロント（別ターミナル）
pnpm --filter web dev            # → http://localhost:3000
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

> - GPU が無い／Vulkan 不可の環境ではソルバは自動で CPU にフォールバック。明示するなら
>   `SPH_ARCH=cpu`（PowerShell は `$env:SPH_ARCH="cpu"`）。
> - **`pnpm dev` 稼働中に `pnpm build` を実行しない**（`.next` を壊し dev の JS が 404 になる）。
>   本番確認は dev を止めてから `pnpm --filter web build`。

---

## GUI ワークフロー（S0–S7）

1. **S0 ホーム** — 新規計算 / ① 設定ファイル(JSON)インポート / バックエンド状態 / ジョブ一覧。
2. **S1 シーン** — ①解析空間、②流体ブロック、③剛体を **複数** 追加・編集（3D 即時プレビュー）。
   「解析空間フィット検証」で超過時に**推奨倍率**を提示・ワンクリック適用。
3. **S2 パラメータ** — ソルバ / 境界 / 場の物理（重力・粘性・表面張力）/ WCSPH 係数 / 計算範囲。
4. **S3 出力設定** — 時間刻み間隔、流体フィールド、オブジェクト別個追跡。
5. **S4 実行** — レビュー → 実行で **`scene.json` が自動生成**されソルバ起動。
6. **S5 進捗** — WebSocket で進捗バー・ETA・ライブログ・キャンセル。
7. **S6 結果** — フレームスクラバで 3D 再生、CSV 一括ダウンロード。
8. **S7 環境設定** — API/ディレクトリ/Python/`SPH_ARCH` の情報表示。

---

## ソルバ単体のヘッドレス実行

```bash
python solver/run_headless.py \
  --scene_file data/scenes/sample_bunny.json \
  --output_dir outputs/sample
```

- 進捗は **標準出力に JSON Lines**（`{"type":"progress",...}` / `frame` / `done` / `error`）。
- `Export` 設定に従い `outputs/<...>/` に **流体 CSV** と **オブジェクト CSV** を時間刻みごと出力。
- 解析空間よりオブジェクトが大きい場合は **推奨倍率**を出力して異常終了（`enforceDomainFit`）。

サンプルシーン: `sample_bunny`（流体+剛体）, `sample_dambreak`（流体のみ）,
`sample_two_fluids`（左右2流体+剛体、複数配置の例）。

---

## 設定ファイル（scene.json）リファレンス

`②FluidBlocks` と `③RigidBodies` は **同種を複数** 配置できる（`objectId` は全体で一意）。

### ① `Configuration`（解析空間・ソルバ・場の物理）
| キー | 意味 | ソルバでの使用 |
|------|------|----------------|
| `domainStart` / `domainEnd` | 解析空間の最小/最大座標 | 格子・境界 |
| `particleRadius` | 粒子半径（径=2r, support=4r） | 近傍探索 |
| `simulationMethod` | `0`=WCSPH, `4`=DFSPH | ソルバ選択 |
| `timeStepSize` | 時間刻み dt | 積分 |
| `gravitation` | 重力ベクトル | 体積力 |
| `density0` | 基準密度 | 密度・圧力 |
| `stiffness` / `exponent` | 状態方程式 `P=stiffness((ρ/ρ0)^exponent-1)` | WCSPH 圧力 |
| `viscosity` | 動粘性 | 粘性力（sph_base） |
| `surfaceTension` | 表面張力係数 | 非圧力力（WCSPH/DFSPH） |
| `boundaryHandlingMethod` | 境界方式（現状は衝突ベース固定・将来拡張用） | — |
| `enforceDomainFit` | 超過時に推奨倍率を出しエラー終了 | 事前検証 |
| `totalTime` または `totalSteps` | 総計算時間／総ステップ | ループ長 |

### ② `FluidBlocks[]`（流体・複数可）
`objectId`, `start`, `end`（領域）, `translation`, `scale`, `velocity`（初速）,
`density`, `color`。

### ③ `RigidBodies[]`（剛体メッシュ・複数可）
`objectId`, `geometryFile`（.obj）, `translation`（重心基準）, `scale`（倍率）,
`rotationAxis`, `rotationAngle`, `velocity`（初速）, `density`, `color`,
`isDynamic`（true=PBD 動的剛体 / false=固定壁）。

### `Export`（出力）
`interval{mode:"steps"|"time", value}`、`fluid{enabled, objectIds, fields[]}`、
`objects[]{objectId, mode:"particles"|"meshVertices"}`。

**CSV 出力**: `fluid_<id>_<frame>.csv`（`particle_id,x,y,z,vx,vy,vz,density,pressure` から
`fields` に応じて）、`object_<id>_<frame>.csv`。`frames.json` にフレーム↔時刻↔ファイル対応。

---

## テスト・品質

```bash
# バックエンド（schema/samples は Taichi 不要、e2e は Taichi 有りで実行、無ければ自動 skip）
SPH_ARCH=cpu .venv/Scripts/python -m pytest backend -q      # Windows は .venv\Scripts\python

# Lint（Python / フロント）
.venv/Scripts/python -m ruff check backend solver
pnpm --filter web lint
pnpm --filter web typecheck

# 性能ベンチマーク
SPH_ARCH=cpu .venv/Scripts/python scripts/benchmark.py
```

- 開発ツール一式（pytest / httpx / ruff）: `pip install -r backend/requirements-dev.txt`。
- CI（`.github/workflows/ci.yml`）で ruff・pytest・eslint・typecheck・build を実行。
- 非機能/内部品質/UX の計画と結果は [`docs/08`](docs/08_非機能_内部品質_UXテスト計画.md) /
  [`docs/09`](docs/09_テスト結果報告.md)。

---

## モデルデータ（.obj）

サイズの大きい `.obj` はリポジトリに含めない（`data/models/README.md` 参照）。
`bunny_sparse.obj` のみサンプル同梱。GUI の「③ 剛体を追加」でアップロードすると `data/models/`
へ登録される。

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| `taichi` が Vulkan で起動しない | `SPH_ARCH=cpu` で CPU 実行 |
| `OBJECT DOES NOT FIT ANALYSIS SPACE` で停止 | 出力の推奨倍率に `scale` を変更、または `enforceDomainFit=false` |
| ボクセル化で粒子 0 個 | `scale` を大きく、または `particleRadius` を小さく |
| フロントのボタンが無反応／JS が 404 | `pnpm dev` 中に `pnpm build` した可能性。dev を再起動（`.next` 再生成） |
| ジョブ一覧が空／`job not found` | バックエンド再起動でメモリ上のジョブは消える（`outputs/<id>` は残る） |
| ポート使用中（10048 / EADDRINUSE） | 既存の uvicorn / next を停止してから起動 |
| `trimesh` 由来の import エラー | `networkx` / `scipy` 未導入。`solver/requirements.txt` を導入 |

---

## ライセンス

MIT License（[LICENSE](LICENSE)）。

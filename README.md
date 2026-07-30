# SPH Studio

Taichi ベースの SPH（流体・剛体連成）シミュレータに GUI を付けたデスクトップアプリ。
解析空間・流体ブロック・剛体・計算パラメータ・出力を GUI で編集し、ソルバをヘッドレス
実行して進捗表示・3D 再生・時系列 CSV 出力を行う。

- フロント: **TypeScript + Next.js**（react-three-fiber で 3D プレビュー／結果再生）
- バックエンド: **Python + FastAPI**（ソルバをジョブ単位のサブプロセスで起動）
- ソルバ: **Taichi**（WCSPH / DFSPH、ヘッドレス化）
- 配布: **Tauri + PyInstaller** で 1 アプリ同梱（Phase B 完了）。**exe をクリックするだけで
  バックエンドも自動起動**し、全機能が使える（Python のインストール不要）。

> 設計・計画・テスト文書は [`docs/`](docs/) 参照（仕様書・機能一覧・画面遷移図・実装計画・
> 非機能/UXテスト計画と結果）。

---

## ダウンロード（インストーラ）

OS 別インストーラは [Releases](https://github.com/anene000/sph-studio/releases) から取得できる。

| OS | 形式 |
|----|------|
| Windows | `*_x64-setup.exe`（NSIS）または `*_x64_en-US.msi` |
| macOS (Apple Silicon) | `*_aarch64.dmg` |
| Linux | `*_amd64.AppImage` / `*_amd64.deb` / `*.x86_64.rpm` |

インストール後にアプリを起動するだけで、同梱のバックエンド（`sph-backend`）が自動起動する。
出力（`outputs/`）や取り込んだモデル（`data/models/`）はアプリ実行ファイルと同じ場所に保存される。
**エンドユーザーは Python/Node/Rust を入れる必要はない**（すべて同梱）。ただし OS によっては
下記「外部依存」のランタイムが必要になる場合がある。

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

## 必要環境（開発時）

| 種別 | 推奨 |
|------|------|
| Node.js | 20 以上（開発は 24 で確認） |
| pnpm | 9 以上（`corepack enable` で導入可） |
| Python | 3.10〜3.12 |
| GPU | Vulkan 対応（無ければ CPU フォールバック） |

依存は再現性のためバージョン固定（`==`）。フロントは `pnpm-lock.yaml`、Python は
`backend/requirements.txt`・`solver/requirements.txt`・`backend/requirements-dev.txt`。

---

## 外部依存（パッケージ管理外で手動インストールが必要なもの）

pip / pnpm / cargo で入らない、OS 提供のランタイムやツールチェイン。用途別にまとめる。

### エンドユーザー（配布インストーラを実行するだけの人）

- **Windows**
  - **WebView2 ランタイム** — Tauri アプリの表示に必須。Windows 11 と最近の Windows 10 は
    プリインストール済み。無い場合は Microsoft の
    [Evergreen WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) を導入。
    NSIS インストーラは通常これを自動導入する。
  - **Microsoft Visual C++ 再頒布可能パッケージ（VC++ Redistributable, x64）** — 同梱の Python /
    Taichi ネイティブ DLL が `vcruntime140*.dll` に依存するため、未導入だと起動しないことがある。
    多くの環境で導入済みだが、無ければ
    [最新の VC++ 再頒布可能パッケージ](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist) を入れる。
- **macOS** — 追加ランタイム不要（`.dmg` を開いて Applications へ）。未署名のため初回は
  「開発元を確認できない」警告 → 右クリック→開く、で許可。
- **Linux** — AppImage はほぼ自己完結。deb/rpm や一部環境では **`libwebkit2gtk-4.1-0`** が必要。
  - Debian/Ubuntu: `sudo apt install libwebkit2gtk-4.1-0`
- **GPU 高速化（任意・全 OS 共通）** — Vulkan 対応 GPU とドライバがあれば GPU 実行。無ければ
  自動で CPU 実行にフォールバック（追加インストール不要）。

### 開発者（ソースからビルドする人）

- **Rust ツールチェイン**（`rustup`、Tauri のビルドに必須）。
- **Windows: Visual Studio Build Tools**（「C++ によるデスクトップ開発」ワークロード）
  — Rust の MSVC ターゲットが `link.exe` / Windows SDK を必要とする。
- **macOS: Xcode Command Line Tools**（`xcode-select --install`）。
- **Linux: WebView/ビルド依存** — `libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf`。
- **Node.js + pnpm**、**Python 3.10〜3.12**。
- サイドカー同梱ビルド時のみ **PyInstaller**（`pip install pyinstaller`、`scripts/build_sidecar.*`）。

> CI（`.github/workflows/release.yml`）は上記を各 OS ランナーで自動セットアップして
> インストーラを生成する。ローカルで完全同梱ビルドを作る手順は
> [`apps/desktop/README.md`](apps/desktop/README.md) を参照。

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
3. **S2 パラメータ** — ソルバ / 境界条件（**軸ごとの周期境界 ON/OFF・駆動力**）/ 場の物理（重力・粘性・表面張力）/ WCSPH 係数 / 計算範囲。
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
`sample_two_fluids`（左右2流体+剛体、複数配置の例）,
`sample_periodic_channel`（x 周期境界＋駆動力で流す周期チャネル流の例）。

---

## 扱える物理現象・解法・出典論文

SPH Studio は **SPH（Smoothed Particle Hydrodynamics, 平滑化粒子流体力学）** に基づく
ラグランジュ的（粒子法）な流体・剛体連成ソルバである。粒子ごとに質量・速度・密度を持ち、
平滑化カーネルで近傍粒子から場の量とその勾配を評価して運動方程式を時間積分する。

### 扱える物理現象

| 現象 | 概要 | 実装の要点 |
|------|------|-----------|
| **自由表面流れ（free-surface flow）** | ダムブレイク・落下・飛沫など、気相を陽に解かない非圧縮性液体の流れ | WCSPH の状態方程式による弱圧縮／表面張力項 |
| **弱圧縮・非圧縮流れ** | 密度をほぼ一定に保つ液体（水など）の挙動 | WCSPH（状態方程式）または DFSPH（発散・密度不変を反復修正） |
| **粘性流れ** | 粘性による運動量拡散（層流・チャネル流など） | ラプラシアン近似の粘性力（`viscosity`） |
| **表面張力** | 液滴の凝集・界面のまとまり | 粒子間凝集力（`surfaceTension`） |
| **流体–剛体連成（一方向/双方向）** | 固定壁・動的剛体と流体の相互作用 | 境界粒子の体積補正 + 圧力/粘性の反作用 |
| **剛体運動** | 動的剛体（`isDynamic`）の並進・回転 | 形状マッチング（shape matching）による剛体拘束 |
| **周期境界・完全発達流** | 周期チャネル流・連続流れ（流入口=流出口） | 周期境界（位置ラップ＋minimum-image 近傍探索）＋駆動体積力 |
| **壁境界（衝突）** | 解析空間の壁での反射・すり抜け防止 | `enforce_boundary` による衝突応答（非周期軸） |

### 解法・数値スキーム

- **平滑化カーネル**: 3 次スプライン（cubic spline）カーネルとその勾配（`support = 4r`）。
- **近傍探索**: 一様格子 + カウンティングソート（周期軸は minimum-image 規約でラップ）。
- **時間積分**: シンプレクティック・オイラー（WCSPH）／予測–修正（DFSPH）。
- **境界開放・周期計算**: 軸ごとに壁を外して周期化（粒子数一定で循環）。周期方向へ一定の
  **駆動体積力（圧力勾配相当）** を与えることで完全発達流（例: ポアズイユ流）を維持する。
- **剛体**: 位置ベース（PBD）の形状マッチングで剛体拘束を満たす。

### ソルバと出典論文

| 要素 | ソルバ / 手法 | 出典 |
|------|--------------|------|
| 弱圧縮 SPH（自由表面） | **WCSPH** `simulationMethod=0` | Becker & Teschner, *Weakly compressible SPH for free surface flows*, SCA 2007. |
| 非圧縮 SPH（発散フリー） | **DFSPH** `simulationMethod=4` | Bender & Koschier, *Divergence-Free Smoothed Particle Hydrodynamics*, SCA 2015（拡張: ACM TVCG 2017）. |
| 流体–剛体境界の取り扱い | 境界粒子の体積補正・連成 | Akinci et al., *Versatile rigid-fluid coupling for incompressible SPH*, ACM TOG 31(4), 2012. |
| 剛体（形状マッチング） | Shape Matching / Unified Particle Physics | Müller et al., *Meshless deformations based on shape matching*, ACM TOG 2005 ／ Macklin et al., *Unified particle physics for real-time applications*, ACM TOG 33(4), 2014. |
| SPH 定式化・カーネル | 平滑化・3 次スプライン | Monaghan, *Smoothed particle hydrodynamics*, Annu. Rev. Astron. Astrophys. 30, 1992. |
| 周期境界＋駆動力による流れ | body-force 駆動の周期ポアズイユ流（検証） | Morris, Fox & Zhu, *Modeling low Reynolds number incompressible flows using SPH*, J. Comput. Phys. 136, 1997. |

> 本実装は [SPlisHSPlasH](https://github.com/InteractiveComputerGraphics/SPlisHSPlasH) および
> [erizmr/SPH_Taichi](https://github.com/erizmr/SPH_Taichi) を参考にしている。

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
| `periodicBoundary` | 軸ごとの周期境界フラグ `[x,y,z]`（true=開放/周期, false=壁） | 境界開放・近傍探索（minimum-image） |
| `drivingForce` | 周期流を維持する駆動加速度 `[x,y,z]` [m/s²]（圧力勾配相当） | 流体の体積力 |
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

## デスクトップ版（Phase B / Tauri）— 完了

フロントは静的エクスポート（`next.config.mjs` の `output: "export"`、動的画面は
`/jobs?id=` `/results?id=` のクエリ方式）で `apps/web/out/` を生成し、**Tauri**
（[`apps/desktop`](apps/desktop/README.md)）がバンドルする。**バックエンド（FastAPI＋Taichi
ソルバ）は PyInstaller で `sph-backend` バイナリ化し、Tauri サイドカーとして自動起動／終了**する。

- **U18**: Tauri シェルで静的フロントを WebView 表示。
- **U19**: `sph-backend` サイドカー同梱（`run_server.py` の統一エントリ＝サーバ／`--run-solver`、
  frozen 時は自己再呼び出しでソルバ実行。`app/paths.py` で出力・モデルを exe 隣に解決）。
- **U20**: `.github/workflows/release.yml`（`v*` タグ／手動）が ubuntu/windows/macos で
  サイドカー生成→`tauri build`→インストーラを draft Release に添付。

ローカルで完全同梱ビルドを作る場合（Rust 必須）:
```bash
bash scripts/build_sidecar.sh          # Windows: pwsh scripts/build_sidecar.ps1（要 PyInstaller）
# tauri.conf.json の bundle に "externalBin": ["binaries/sph-backend"] を追加してから
pnpm --dir apps/desktop tauri build
```
> リリース CI は `externalBin` を自動注入するため、コミット済み `tauri.conf.json` には含めない
> （サイドカー未生成でも通常の `tauri build` が通るようにするため）。詳細は
> [`apps/desktop/README.md`](apps/desktop/README.md)。

---

## モデルデータ（.obj）

サイズの大きい `.obj` はリポジトリに含めない（`data/models/README.md` 参照）。
`bunny_sparse.obj` のみサンプル同梱。

**外部 .obj の読み込み** は 2 通り:
- GUI の「③ 剛体モデル → 外部 .obj を取り込む（アップロード）」で、任意の場所の `.obj` を選ぶと
  `data/models/` へ登録され、そのまま剛体として追加される。
- 追加の探索ディレクトリを環境変数 **`SPH_EXTRA_MODELS_DIR`**（`os.pathsep` 区切りで複数）に
  指定すると、その中の `.obj` も一覧・プレビュー対象になる。`geometryFile` に絶対パスを
  書いても解決される。

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
| インストール後アプリが起動しない/白画面（Windows） | **WebView2 ランタイム**未導入。上記「外部依存」を参照 |
| 起動直後に落ちる（Windows, DLL エラー） | **VC++ 再頒布可能パッケージ**未導入。上記「外部依存」を参照 |
| 同梱アプリでジョブが `kernels parameters must be type annotated` | 古いビルド。`v0.0.1-rc3` 以降（Taichi ソース同梱修正済み）を使用 |

---

## ライセンス

MIT License（[LICENSE](LICENSE)）。

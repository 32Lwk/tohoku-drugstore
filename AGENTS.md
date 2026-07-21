# AGENTS.md

## Cursor Cloud specific instructions

このリポジトリは Web サーバーではなく、東北6県のドラッグストア分布を調査・可視化する
Python の CLI データパイプラインです。成果物は各県 `prefectures/<slug>/` 配下の
CSV と folium 製インタラクティブ HTML 地図（`maps/*.html`）、および `report.md` です。
主要コマンドは `README.md` に記載されています。

### 環境と実行

- Python 依存は `requirements.txt`。更新スクリプトが `.venv` を作成し依存をインストールします。
  手動で使う場合は `source .venv/bin/activate` してから実行してください。
- エントリポイントは `run_all.py` と `shared/run_prefecture.py`。これらは `sys.path` に
  リポジトリルートを追加するため、ルートから `python run_all.py` /
  `python shared/run_prefecture.py <slug>` として実行できます。
- **重要（非自明）**: `shared/` 配下の個別スクリプト（例 `shared/create_maps.py`）は
  `import shared.config` を行うため、`python shared/create_maps.py <slug>` と直接実行すると
  `ModuleNotFoundError: No module named 'shared'` になります。個別に動かす場合は
  ルートから `PYTHONPATH=. python -m shared.create_maps <slug>` のようにモジュール実行するか、
  `run_prefecture.py` 経由で呼び出してください。
- slug は `shared/config.py` の `PREFECTURES` キー（例: `01_青森県`, `03_宮城県`）。

### API キー / シークレット（フル実行に必須）

- フルパイプライン（`run_all.py` / `run_prefecture.py`）の店舗収集・座標取得ステップは
  Google Places / Geocoding API を使うため、環境変数 `Google_Place_API`（別名 `GOOGLE_PLACE_API`）が
  必要です。未設定だと `shared/utils.load_api_key()` が `ValueError` を送出します。
  キーは Secrets に登録してください（`.env` はコミットしない。`.gitignore` 済み）。
- API キーなしでも、既存データが揃っている県（例 `01_青森県`）については分析・地図生成・
  検証ステップだけを再実行できます:
  `PYTHONPATH=. python -m shared.analyze_density 01_青森県` →
  `PYTHONPATH=. python -m shared.create_maps 01_青森県`。

### Lint / テスト / ビルド

- Lint 設定・自動テストはリポジトリに存在しません。構文確認は
  `python -m py_compile run_all.py shared/*.py` で行えます。
- 「ビルド」に相当する成果物生成は上記の地図生成コマンドです。生成された HTML は
  `python -m http.server` で配信するとブラウザで確認できます。

# 東北6県 ドラッグストア調査プロジェクト

愛知県プロジェクト（`c:\Users\yutok\Desktop\愛知県内のドラックストア`）をベースに、東北6県のドラッグストア分布を調査・可視化するプロジェクトです。

## 対象地域

| フォルダ | 県 |
|---------|-----|
| `prefectures/01_青森県/` | 青森県 |
| `prefectures/02_岩手県/` | 岩手県 |
| `prefectures/03_宮城県/` | 宮城県 |
| `prefectures/04_秋田県/` | 秋田県 |
| `prefectures/05_山形県/` | 山形県 |
| `prefectures/06_福島県/` | 福島県 |

## 事前準備（Cloud Agent 起動前に必須）

Cursor → Settings → Cloud Agents → Environment Variables:

| 変数名 | 取得方法 |
|--------|---------|
| `Google_Place_API` | Google Cloud Console |
| `ESTAT_APP_ID` | [e-Stat API 無料登録](https://www.e-stat.go.jp/api/)（2分） |

## セットアップ

```bash
cd c:\Users\yutok\Desktop\tohoku-drugstore
pip install -r requirements.txt
```

`.env` に Google Places API キーを設定:

```
Google_Place_API=your_api_key_here
```

### 課金防止（必須）

2026-07-21 の異常課金を受け、Places API (New) + field mask + リクエスト上限に移行済み。
詳細は [`BILLING_PREVENTION.md`](BILLING_PREVENTION.md) を参照。

| 環境変数 | 既定 | 説明 |
|---------|------|------|
| `PLACES_ENABLED` | `1` | `0` で Places 一次調査を停止 |
| `PLACES_MAX_REQUESTS_PER_RUN` | `60` | 1県あたりの最大 API 呼び出し |
| `PLACES_MAX_PAGES_PER_QUERY` | `2` | 1クエリのページネーション上限 |
| `PLACES_MAX_MUNICIPALITIES` | `8` | 市区町村検索の上限 |
| `PLACES_MAX_CHAINS` | `15` | チェーン別検索の上限 |
| `PLACES_SKIP_IF_RAW_EXISTS` | `0` | `1` で既存 CSV を再利用（API なし） |

**Console 側も必須**: API キー制限・日次クォータ・予算アラート（¥3,000 目安）。

## 実行方法

### 6県一括実行

```bash
python run_all.py
```

### 1県のみ実行

```bash
python shared/run_prefecture.py 03_宮城県
```

### 並列実行（3県同時）

```bash
python run_all.py --parallel
```

## 各県の成果物

```
prefectures/03_宮城県/
├── data/
│   ├── raw_stores.csv                          # 生データ
│   ├── 宮城県ドラッグストア_最終版.csv           # クリーニング済
│   ├── 宮城県ドラッグストア_座標付き.csv       # 座標付き
│   ├── 市区町村別ドラッグストア分析.csv
│   ├── 市区町村別人口.csv
│   ├── 市区町村別高齢化率.csv
│   └── municipalities.geojson
├── maps/
│   ├── 宮城県ドラッグストア地図.html
│   ├── 宮城県ドラッグストア密度コロプレスマップ.html
│   └── 宮城県高齢化率コロプレスマップ.html
└── report.md
```

## データ取得方針

- **チェーン**: 東北に存在するチェーンのみ自動判定
- **薬局除外**: 店舗名に「薬局」「調剤」を含むものを除外
- **重複**: 同一住所で薬局/ドラッグストア重複時はドラッグストアのみ残す（異なるチェーンは残す）
- **国勢調査**: 2020年国勢調査
- **座標**: Places API (New) geometry → Geocoding API → 国土地理院API（フォールバック）
- **Places**: レガシー Text Search は使用しない（Data SKU 一括課金を回避）

## GitHub

https://github.com/32Lwk/tohoku-drugstore.git

## 参照

- ベースプロジェクト: `c:\Users\yutok\Desktop\愛知県内のドラックストア`
- [e-Stat 国勢調査2020](https://www.e-stat.go.jp/stat-search/files?page=1&layout=dataset&toukei=00200521)
- [国土地理院 N03 行政区域](https://nlftp.mlit.go.jp/ksj/gml/codelist/N03.html)

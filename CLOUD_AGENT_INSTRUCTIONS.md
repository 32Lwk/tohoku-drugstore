# Cloud Agent 実行指示書

> **このファイルの内容を Cloud Agent にそのまま貼り付けて実行してください。**
> 6県を並列で調査し、朝までに完璧な成果物を GitHub に push すること。

---

## ミッション

東北6県（青森・岩手・宮城・秋田・山形・福島）それぞれについて、ドラッグストア（薬局除外）の全店舗データ収集・座標取得・国勢調査分析・地図生成を行い、GitHub に push する。

---

## 環境

- **作業ディレクトリ**: `c:\Users\yutok\Desktop\tohoku-drugstore`
- **APIキー**: `.env` の `Google_Place_API` を使用（**ハードコード禁止**）
- **ベース参照**: `c:\Users\yutok\Desktop\愛知県内のドラックストア`（愛知県プロジェクト）
- **GitHub**: https://github.com/32Lwk/tohoku-drugstore.git
- **Python**: `pip install -r requirements.txt` を最初に実行

---

## 実行戦略（6県並列）

Multitask / 並列サブエージェントで **6県を同時に** 処理する。各県は独立パイプラインで完結させる。

```
01_青森県 ──┐
02_岩手県 ──┤
03_宮城県 ──┼── 並列実行（6タスク）
04_秋田県 ──┤
05_山形県 ──┤
06_福島県 ──┘
```

---

## 各県のパイプライン（8ステップ）

既存スクリプト `shared/run_prefecture.py` をベースに、不足があれば補完すること。

### Step 1: 境界データ
```bash
python shared/fetch_boundaries.py {slug}
```
- 国土地理院 N03 GeoJSON をダウンロード

### Step 2: 国勢調査2020
```bash
python shared/fetch_census.py {slug}
```
- **重要**: 自動取得失敗時は [e-Stat 国勢調査2020](https://www.e-stat.go.jp/stat-search/files?page=1&layout=dataset&toukei=00200521) から CSV をダウンロード
- `shared/census_cache/{pref_code}_population.csv`（市区町村, 人口）
- `shared/census_cache/{pref_code}_aging.csv`（市区町村, 総数, 65歳以上, 高齢化率）
- 愛知県参考: `FEH_00200521_251020013417.csv` の形式

### Step 3: 店舗収集（一次調査）
```bash
python shared/collect_stores.py {slug}
```
- Google Places API: 市区町村 × 「ドラッグストア」広域検索
- 続けて存在チェーン別に精査検索
- チェーンは東北に存在するもののみ（自動判定）

### Step 4: 二次調査（公式サイト補完）
以下の公式サイトから不足チェーンを補完スクレイピング:
- GENKY: https://www.genky.co.jp/store/
- ウエルシア: https://store.welcia.co.jp/welcia/
- ツルハドラッグ: https://www.tsuruha.co.jp/shop/
- コスモス: https://www.cosmospc.co.jp/shop/
- クスリのアオキ: https://www.aoki-pharm.co.jp/shop/

取得データは `raw_stores.csv` に追記（place_id 重複は除外）

### Step 5: クリーニング
```bash
python shared/clean_data.py {slug}
```
- **薬局除外**: 店舗名に「薬局」「調剤」を含む → 除外
- **同一住所重複**: 薬局/DS混在時はドラッグストアのみ残す
- **異なるチェーン同一住所**: 除外しない
- 出力: `{県名}ドラッグストア_最終版.csv`

### Step 6: 座標取得
```bash
python shared/geocode_stores.py {slug}
```
- Places API geometry → Geocoding API → 国土地理院API
- 座標取得率 **95%以上** を目標

### Step 7: 分析・地図
```bash
python shared/analyze_density.py {slug}
python shared/create_maps.py {slug}
```
生成する HTML（愛知県プロジェクトと同様）:
1. `{県名}ドラッグストア地図.html` — チェーン別マーカー
2. `{県名}ドラッグストア密度コロプレスマップ.html` — 10万人当たり店舗数
3. `{県名}高齢化率コロプレスマップ.html` — 国勢調査2020

### Step 8: 検証・レポート
```bash
python shared/verify_data.py {slug}
python shared/run_prefecture.py {slug}  # レポート生成部分
```

検証項目:
- [ ] 座標取得率 ≥ 95%
- [ ] 薬局漏れ = 0件
- [ ] チェーン別件数が妥当（0件チェーンは除外記載）
- [ ] 3つの HTML 地図が正常生成
- [ ] 市区町村マッチ率 ≥ 80%（GeoJSON と国勢調査）

---

## データ品質基準

| 項目 | 基準 |
|------|------|
| 薬局除外 | 店舗名に「薬局」「調剤」含む → 除外 |
| 同一住所 | DS/薬局混在 → DSのみ。異チェーン → 両方残す |
| 住所形式 | `{県名}` から始まる |
| 座標精度 | 95%以上 |
| 国勢調査 | 2020年 |
| API節約 | place_id キャッシュ、重複検索禁止 |

---

## 完了後の作業

1. `python run_all.py` で全体サマリー `00_実行レポート.md` 生成
2. Git commit & push:

```bash
git init  # 未初期化の場合
git remote add origin https://github.com/32Lwk/tohoku-drugstore.git
git add .
git commit -m "feat: 東北6県ドラッグストア調査完了"
git push -u origin main
```

3. **push 対象外**: `.env`, `*.pkl`, `geocode_cache*`

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| 国勢調査CSV取得失敗 | e-Stat から手動DL → `shared/census_cache/` |
| N03 GeoJSON 404 | [N03一覧](https://nlftp.mlit.go.jp/ksj/gml/codelist/N03.html) から最新URL確認 |
| 座標取得率低 | 国土地理院APIでフォールバック |
| API quota | リクエスト間隔を 0.2秒に増加 |
| チェーン0件 | レポートに「東北未出店」と記載、除外 |

---

## 期待する朝の成果物

```
tohoku-drugstore/
├── 00_実行レポート.md          ← 6県サマリー
├── README.md
├── prefectures/
│   ├── 01_青森県/  (CSV×5 + HTML×3 + report.md)
│   ├── 02_岩手県/
│   ├── 03_宮城県/
│   ├── 04_秋田県/
│   ├── 05_山形県/
│   └── 06_福島県/
└── shared/
```

**GitHub**: https://github.com/32Lwk/tohoku-drugstore.git に全成果物が push されていること。

---

## チェックリスト（Agent自身が完了前に確認）

- [ ] 6県すべて report.md あり
- [ ] 6県すべて HTML 地図 3種あり
- [ ] 00_実行レポート.md に合計店舗数記載
- [ ] .env が git に含まれていない
- [ ] GitHub push 成功

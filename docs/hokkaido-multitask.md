# 北海道ドラッグストア調査 — Multitask Mode 指示文

Places API **不使用・完全無料**。5地域を並列で収集し、最後に1エージェントがマージ・地図生成します。

## 全体フロー

```
[Coordinator] setup（1回）
     ↓
[Agent 1〜5] 地域別収集（並列）
     ↓
[Coordinator] finalize（マージ + 地図）
```

---

## Step 0: Coordinator（最初に1回だけ）

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore

北海道ドラッグストア調査の Multitask セットアップを実行してください。

1. pip install -r requirements.txt && playwright install chromium
2. $env:PYTHONUTF8=1 を設定（Windows）
3. python shared/run_hokkaido_setup.py
   → 境界GeoJSON + 国勢調査2020 を取得
4. prefectures/09_北海道/data/regions/ ディレクトリが作成されていることを確認
5. 変更をコミットしない（収集完了後にまとめてコミット）

完了報告: municipalities.geojson の feature 数、人口CSV行数
```

---

## Agent 1: 道央・石狩（札幌圏）

**地域ID:** `r1_sapporo`

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore
Multitask Mode — 北海道 地域1/5

## 担当
道央・石狩（札幌圏）のドラッグストアを Places API 不使用で収集。

## 実行
$env:PYTHONUTF8=1
pip install -r requirements.txt
playwright install chromium
python shared/collect_hokkaido_region.py r1_sapporo

## 対象市区町村
札幌市、江別市、千歳市、恵庭市、北広島市、石狩市、岩見沢市、美唄市、
三笠市、夕張市、栗山町、南幌町 他（shared/hokkaido_regions.py 参照）

## 収集ソース（無料）
- ツルハ Yext API、ウエルシア API
- サッポロドラッグ、クスリのコダマ、キリン堂、コスモス 公式サイト
- Google Maps ブラウザ検索（Places API 不使用）

## 成果物（必須）
- prefectures/09_北海道/data/regions/r1_sapporo/raw_stores.csv
- prefectures/09_北海道/data/regions/r1_sapporo/report.md
- prefectures/09_北海道/data/regions/r1_sapporo/.done

## 品質目標
- 200件以上（札幌圏は最大規模）
- ツルハ・サツドラ・ウエルシアが主要チェーン
- 他地域のファイルは変更しない
- Google Places API は使わない

## 完了報告
店舗数、チェーン別 TOP5、ソース別件数
```

---

## Agent 2: 道南・渡島（函館圏）

**地域ID:** `r2_hakodate`

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore
Multitask Mode — 北海道 地域2/5

## 担当
道南・渡島（函館・苫小牧・室蘭圏）

## 実行
$env:PYTHONUTF8=1
python shared/collect_hokkaido_region.py r2_hakodate

## 対象市区町村
函館市、北斗市、七飯町、室蘭市、苫小牧市、登別市、伊達市、
浦河町、新ひだか町 他

## 重点チェーン
ツルハドラッグ、サツドラ、サッポロドラッグ、クスリのコダマ、キリン堂

## 成果物
prefectures/09_北海道/data/regions/r2_hakodate/
  raw_stores.csv, report.md, .done

## 品質目標: 80件以上
他地域ファイル変更禁止。Places API 不使用。
```

---

## Agent 3: 後志・胆振（小樽・ニセコ圏）

**地域ID:** `r3_otaru`

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore
Multitask Mode — 北海道 地域3/5

## 担当
後志・胆振（小樽・ニセコ・倶知安圏）

## 実行
$env:PYTHONUTF8=1
python shared/collect_hokkaido_region.py r3_otaru

## 対象市区町村
小樽市、余市町、ニセコ町、倶知安町、喜茂別町 他

## 重点チェーン
ツルハ、サツドラ、サッポロドラッグ、キリン堂（ニセコ）

## 成果物
prefectures/09_北海道/data/regions/r3_otaru/
  raw_stores.csv, report.md, .done

## 品質目標: 40件以上
Places API 不使用。他地域変更禁止。
```

---

## Agent 4: 道東・十勝（釧路・帯広圏）

**地域ID:** `r4_kushiro`

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore
Multitask Mode — 北海道 地域4/5

## 担当
道東・十勝（釧路・帯広・根室圏）

## 実行
$env:PYTHONUTF8=1
python shared/collect_hokkaido_region.py r4_kushiro

## 対象市区町村
釧路市、帯広市、根室市、中標津町、弟子屈町、広尾町 他

## 重点チェーン
ツルハ、サツドラ、サッポロドラッグ、クスリのコダマ、キリン堂

## 成果物
prefectures/09_北海道/data/regions/r4_kushiro/
  raw_stores.csv, report.md, .done

## 品質目標: 60件以上
Places API 不使用。他地域変更禁止。
```

---

## Agent 5: 道北・オホーツク（旭川・北見圏）

**地域ID:** `r5_asahikawa`

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore
Multitask Mode — 北海道 地域5/5

## 担当
道北・オホーツク（旭川・北見・稚内・留萌圏）

## 実行
$env:PYTHONUTF8=1
python shared/collect_hokkaido_region.py r5_asahikawa

## 対象市区町村
旭川市、北見市、網走市、紋別市、稚内市、留萌市、富良野市、
名寄市、士別市 他

## 重点チェーン
ツルハ、サツドラ、ドラッグイレブン、サッポロドラッグ、クスリのコダマ

## 成果物
prefectures/09_北海道/data/regions/r5_asahikawa/
  raw_stores.csv, report.md, .done

## 品質目標: 100件以上
Places API 不使用。他地域変更禁止。
```

---

## Step Final: Coordinator（5地域完了後）

```
リポジトリ: c:\Users\yutok\Desktop\tohoku-drugstore

5地域の収集が完了したら最終処理を実行してください。

1. 進捗確認:
   python shared/collect_hokkaido_region.py --status
   → 5地域すべて [OK] であること

2. マージ + 地図生成（GSI座標のみ・無料）:
   $env:PYTHONUTF8=1
   python shared/run_hokkaido_finalize.py

3. サイトビルド確認:
   python scripts/build_site.py

4. 成果物確認:
   - prefectures/09_北海道/data/北海道ドラッグストア_座標付き.csv
   - prefectures/09_北海道/maps/ HTML 3ファイル
   - prefectures/09_北海道/report.md

5. 座標取得率が90%未満なら geocode 再実行

完了報告: 総店舗数、座標率、チェーン別TOP10、地域別件数
```

---

## 5地域一覧

| ID | 名称 | 主要都市 | 目標件数 |
|----|------|---------|---------|
| r1_sapporo | 道央・石狩 | 札幌、岩見沢 | 200+ |
| r2_hakodate | 道南・渡島 | 函館、苫小牧、室蘭 | 80+ |
| r3_otaru | 後志・胆振 | 小樽、ニセコ | 40+ |
| r4_kushiro | 道東・十勝 | 釧路、帯広 | 60+ |
| r5_asahikawa | 道北・オホーツク | 旭川、北見、稚内 | 100+ |

**合計目標: 480件以上**

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| Python cp932 エラー | `$env:PYTHONUTF8=1` |
| Playwright 未インストール | `playwright install chromium` |
| 件数が少ない | `collect_hokkaido_region.py` を再実行（gmaps 含む） |
| 公式サイト取得失敗 | report.md のソース別を確認し、fetcher を追加 |
| マージ失敗 | 5地域すべて `.done` ファイルがあるか確認 |

## 関連ファイル

- `shared/hokkaido_regions.py` — 5地域定義
- `shared/hokkaido_fetchers.py` — 北海道チェーン fetcher
- `shared/collect_hokkaido_region.py` — 地域別収集
- `shared/merge_hokkaido_regions.py` — マージ
- `shared/run_hokkaido_setup.py` — 初期セットアップ
- `shared/run_hokkaido_finalize.py` — 最終処理

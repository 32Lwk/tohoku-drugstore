# Cloud Agent 起動用プロンプト（6県 + サマリー）

> **使い方**
> 1. Cursor → Settings → Cloud Agents → Environment Variables に `Google_Place_API` を登録
> 2. Cloud Agent を **6回** 起動し、下記プロンプトを **1県1つずつ** 貼り付け
> 3. 6県すべて完了後、最後に「サマリー用プロンプト」を1回実行

---

## 事前準備（1回だけ）

Cloud Agent の Environment Variables に以下を設定:

| 変数名 | 値 |
|--------|-----|
| `Google_Place_API` | `.env` と同じ API キー |

---

## Agent 1: 青森県

```
@c:\Users\yutok\Desktop\tohoku-drugstore\CLOUD_AGENT_INSTRUCTIONS.md に従い、
01_青森県 ONLY を完遂してください。他の県は触らないでください。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

最初に実行:
  pip install -r requirements.txt

メイン実行:
  python shared/run_prefecture.py 01_青森県

各ステップ（run_prefecture.py 内で自動実行）:
  1. 境界GeoJSON取得
  2. 国勢調査2020（人口・高齢化率）
  3. Google Places 一次調査（東北存在チェーン自動判定）
  4. 公式サイト二次調査（GENKY/ウエルシア/ツルハ/コスモス等）
  5. クリーニング（薬局除外・同一住所整理）
  6. 座標取得（Places → Geocoding → 国土地理院）
  7. 密度分析・地図3種生成
  8. 検証・report.md 作成

データ品質:
  - 店舗名に「薬局」「調剤」含む → 除外
  - 同一住所で薬局/DS混在 → DSのみ残す
  - 異なるチェーン同一住所 → 両方残す
  - 座標取得率 95% 以上を目標

APIキー: 環境変数 Google_Place_API のみ使用（ハードコード禁止）
参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

完了後:
  git add prefectures/01_青森県/ shared/census_cache/
  git commit -m "feat: 青森県ドラッグストア調査完了"
  git push origin main
```

---

## Agent 2: 岩手県

```
@c:\Users\yutok\Desktop\tohoku-drugstore\CLOUD_AGENT_INSTRUCTIONS.md に従い、
02_岩手県 ONLY を完遂してください。他の県は触らないでください。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

最初に実行:
  pip install -r requirements.txt

メイン実行:
  python shared/run_prefecture.py 02_岩手県

各ステップ（run_prefecture.py 内で自動実行）:
  1. 境界GeoJSON取得
  2. 国勢調査2020（人口・高齢化率）
  3. Google Places 一次調査（東北存在チェーン自動判定）
  4. 公式サイト二次調査（GENKY/ウエルシア/ツルハ/コスモス等）
  5. クリーニング（薬局除外・同一住所整理）
  6. 座標取得（Places → Geocoding → 国土地理院）
  7. 密度分析・地図3種生成
  8. 検証・report.md 作成

データ品質:
  - 店舗名に「薬局」「調剤」含む → 除外
  - 同一住所で薬局/DS混在 → DSのみ残す
  - 異なるチェーン同一住所 → 両方残す
  - 座標取得率 95% 以上を目標

APIキー: 環境変数 Google_Place_API のみ使用（ハードコード禁止）
参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

完了後:
  git add prefectures/02_岩手県/ shared/census_cache/
  git commit -m "feat: 岩手県ドラッグストア調査完了"
  git push origin main
```

---

## Agent 3: 宮城県

```
@c:\Users\yutok\Desktop\tohoku-drugstore\CLOUD_AGENT_INSTRUCTIONS.md に従い、
03_宮城県 ONLY を完遂してください。他の県は触らないでください。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

最初に実行:
  pip install -r requirements.txt

メイン実行:
  python shared/run_prefecture.py 03_宮城県

各ステップ（run_prefecture.py 内で自動実行）:
  1. 境界GeoJSON取得
  2. 国勢調査2020（人口・高齢化率）
  3. Google Places 一次調査（東北存在チェーン自動判定）
  4. 公式サイト二次調査（GENKY/ウエルシア/ツルハ/コスモス等）
  5. クリーニング（薬局除外・同一住所整理）
  6. 座標取得（Places → Geocoding → 国土地理院）
  7. 密度分析・地図3種生成
  8. 検証・report.md 作成

データ品質:
  - 店舗名に「薬局」「調剤」含む → 除外
  - 同一住所で薬局/DS混在 → DSのみ残す
  - 異なるチェーン同一住所 → 両方残す
  - 座標取得率 95% 以上を目標

APIキー: 環境変数 Google_Place_API のみ使用（ハードコード禁止）
参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

完了後:
  git add prefectures/03_宮城県/ shared/census_cache/
  git commit -m "feat: 宮城県ドラッグストア調査完了"
  git push origin main
```

---

## Agent 4: 秋田県

```
@c:\Users\yutok\Desktop\tohoku-drugstore\CLOUD_AGENT_INSTRUCTIONS.md に従い、
04_秋田県 ONLY を完遂してください。他の県は触らないでください。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

最初に実行:
  pip install -r requirements.txt

メイン実行:
  python shared/run_prefecture.py 04_秋田県

各ステップ（run_prefecture.py 内で自動実行）:
  1. 境界GeoJSON取得
  2. 国勢調査2020（人口・高齢化率）
  3. Google Places 一次調査（東北存在チェーン自動判定）
  4. 公式サイト二次調査（GENKY/ウエルシア/ツルハ/コスモス等）
  5. クリーニング（薬局除外・同一住所整理）
  6. 座標取得（Places → Geocoding → 国土地理院）
  7. 密度分析・地図3種生成
  8. 検証・report.md 作成

データ品質:
  - 店舗名に「薬局」「調剤」含む → 除外
  - 同一住所で薬局/DS混在 → DSのみ残す
  - 異なるチェーン同一住所 → 両方残す
  - 座標取得率 95% 以上を目標

APIキー: 環境変数 Google_Place_API のみ使用（ハードコード禁止）
参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

完了後:
  git add prefectures/04_秋田県/ shared/census_cache/
  git commit -m "feat: 秋田県ドラッグストア調査完了"
  git push origin main
```

---

## Agent 5: 山形県

```
@c:\Users\yutok\Desktop\tohoku-drugstore\CLOUD_AGENT_INSTRUCTIONS.md に従い、
05_山形県 ONLY を完遂してください。他の県は触らないでください。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

最初に実行:
  pip install -r requirements.txt

メイン実行:
  python shared/run_prefecture.py 05_山形県

各ステップ（run_prefecture.py 内で自動実行）:
  1. 境界GeoJSON取得
  2. 国勢調査2020（人口・高齢化率）
  3. Google Places 一次調査（東北存在チェーン自動判定）
  4. 公式サイト二次調査（GENKY/ウエルシア/ツルハ/コスモス等）
  5. クリーニング（薬局除外・同一住所整理）
  6. 座標取得（Places → Geocoding → 国土地理院）
  7. 密度分析・地図3種生成
  8. 検証・report.md 作成

データ品質:
  - 店舗名に「薬局」「調剤」含む → 除外
  - 同一住所で薬局/DS混在 → DSのみ残す
  - 異なるチェーン同一住所 → 両方残す
  - 座標取得率 95% 以上を目標

APIキー: 環境変数 Google_Place_API のみ使用（ハードコード禁止）
参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

完了後:
  git add prefectures/05_山形県/ shared/census_cache/
  git commit -m "feat: 山形県ドラッグストア調査完了"
  git push origin main
```

---

## Agent 6: 福島県

```
@c:\Users\yutok\Desktop\tohoku-drugstore\CLOUD_AGENT_INSTRUCTIONS.md に従い、
06_福島県 ONLY を完遂してください。他の県は触らないでください。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

最初に実行:
  pip install -r requirements.txt

メイン実行:
  python shared/run_prefecture.py 06_福島県

各ステップ（run_prefecture.py 内で自動実行）:
  1. 境界GeoJSON取得
  2. 国勢調査2020（人口・高齢化率）
  3. Google Places 一次調査（東北存在チェーン自動判定）
  4. 公式サイト二次調査（GENKY/ウエルシア/ツルハ/コスモス等）
  5. クリーニング（薬局除外・同一住所整理）
  6. 座標取得（Places → Geocoding → 国土地理院）
  7. 密度分析・地図3種生成
  8. 検証・report.md 作成

データ品質:
  - 店舗名に「薬局」「調剤」含む → 除外
  - 同一住所で薬局/DS混在 → DSのみ残す
  - 異なるチェーン同一住所 → 両方残す
  - 座標取得率 95% 以上を目標

APIキー: 環境変数 Google_Place_API のみ使用（ハードコード禁止）
参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

完了後:
  git add prefectures/06_福島県/ shared/census_cache/
  git commit -m "feat: 福島県ドラッグストア調査完了"
  git push origin main
```

---

## サマリー用（6県完了後に1回だけ実行）

```
6県（01_青森県〜06_福島県）の調査がすべて完了しています。

作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore

以下を実行してください:
  1. git pull origin main  （他Agentの成果を取り込む）
  2. python run_all.py     （00_実行レポート.md を生成）
  3. 6県すべての report.md と maps/ HTML 3種の存在を確認
  4. 不足県があれば python shared/run_prefecture.py {slug} で再実行
  5. git add .
  6. git commit -m "docs: 東北6県調査サマリーレポート追加"
  7. git push origin main

00_実行レポート.md に以下を記載:
  - 6県別店舗数・座標取得率・チェーン数
  - 合計店舗数
  - 未完了・要再調査があれば明記
```

---

## 朝の確認チェックリスト

- [ ] `prefectures/01_青森県/report.md` 〜 `06_福島県/report.md` すべて存在
- [ ] 各県 `maps/` に HTML 3ファイル（マーカー・密度・高齢化率）
- [ ] 各県 `data/` に CSV 5ファイル
- [ ] `00_実行レポート.md` に6県サマリー
- [ ] https://github.com/32Lwk/tohoku-drugstore に push 済み
- [ ] `.env` が GitHub に含まれていない

---

## トラブル時

| 症状 | 対処 |
|------|------|
| API エラー | Environment Variables の `Google_Place_API` を確認 |
| git push 競合 | `git pull --rebase origin main` してから再 push |
| 国勢調査取得失敗 | [e-Stat](https://www.e-stat.go.jp/stat-search/files?page=1&layout=dataset&toukei=00200521) から CSV DL → `shared/census_cache/` |
| 1県だけ失敗 | 該当県の Agent プロンプトだけ再実行 |

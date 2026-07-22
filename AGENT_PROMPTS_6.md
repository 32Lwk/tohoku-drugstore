# Cloud Agent 起動用プロンプト（6県 + サマリー）

> **使い方**
> 1. 下記「事前準備」を完了
> 2. Cloud Agent を **6回** 起動し、Agent 1〜6 のプロンプトを **1県1つずつ** 貼り付け
> 3. **サマリーは自動** — 6県目が完了した Agent が `00_実行レポート.md` を生成（手動不要）

### サマリー自動化の仕組み

各 Agent は push 後に `python shared/auto_summarize.py` を実行します。
- 6県未完了 → スキップ（次の Agent が再チェック）
- **6県すべて完了** → `00_実行レポート.md` 生成 & git push

**PC常時稼働の場合（任意）**: 7体目不要。代わりにローカルで監視も可能:
```bash
python shared/auto_summarize.py --watch
```
5分ごとに完了確認し、6県揃い次第サマリーを自動生成します。

---

## 事前準備（必須・1回だけ）

Cursor → **Settings → Cloud Agents → Environment Variables** に以下を登録:

| 変数名 | 値 | 必須 |
|--------|-----|------|
| `Google_Place_API` | Google Places API キー（**Places API New 用**。レガシー Text Search 禁止） | ✅ 必須 |
| `PLACES_MAX_REQUESTS_PER_RUN` | 1県あたりの最大 Places 呼出（既定 60） | 推奨 |
| `ESTAT_APP_ID` | [e-Stat API](https://www.e-stat.go.jp/api/) 無料登録 | 任意（xlsx自動DLが優先） |

---

## 全 Agent 共通：自律実行ルール（最重要）

**以下をすべての Agent が必ず守ること。エラーで停止しない。**

### 基本方針
- **1回の失敗で諦めない**。最低3回は別手法でリトライする
- **完遂が目的**。中間エラーはログに記録し、代替手段で続行する
- **品質基準を満たすまで改善を繰り返す**（後述チェックリスト参照）
- スクリプトが失敗したら **コードを読んで原因を特定し、修正して再実行**する
- 修正したコードは **git commit & push** する（他 Agent も恩恵を受ける）

### エラー時の対応フロー（自動で実行すること）

```
エラー発生
  ↓
1. エラーメッセージを読み、原因を特定
  ↓
2. 同じコマンドを最大3回リトライ（間隔を空ける）
  ↓
3. それでも失敗 → 代替手法を試す（下表参照）
  ↓
4. 代替も失敗 → スクリプトを修正して再実行
  ↓
5. それでも不可 → report.md に「要手動対応」を明記し、他ステップは続行
  ↓
6. 全ステップ完了後、品質チェック → 未達項目があれば追加実行
```

### エラー別 代替手法

| エラー | 代替手法 |
|--------|---------|
| N03 GeoJSON 404 | `fetch_boundaries.py` が GitHub ミラー（niiyz）に自動フォールバック。それでも失敗なら URL を [国土数値情報 N03](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2024.html) から確認して `fetch_boundaries.py` を修正 |
| 国勢調査取得失敗 | ① `ESTAT_APP_ID` 確認 ② [e-Stat API](https://www.e-stat.go.jp/api/) 登録 ③ `getStatsList` で statsDataId 検索 → `fetch_census.py` の `STATS_DATA_IDS` 更新 ④ CSV を `shared/census_cache/{code}_population.csv` に手動配置 |
| Google API エラー | ① API キー確認 ② リクエスト間隔を 0.3秒に増加 ③ `OVER_QUERY_LIMIT` なら 60秒待機して再開 |
| 座標取得率 < 95% | ① `geocode_stores.py` 再実行 ② 国土地理院APIフォールバック確認 ③ 失敗住所を個別 Geocoding |
| 公式サイトスクレイピング失敗 | Google Places のみで続行（report.md に記載） |
| git push 競合 | `git pull --rebase origin main` → 再 push |
| pip install 失敗 | `pip install --upgrade pip` 後に再試行。個別パッケージを指定インストール |

### 品質基準（未達なら追加実行）

| 項目 | 基準 | 未達時の対応 |
|------|------|-------------|
| 座標取得率 | ≥ 95% | `geocode_stores.py` 再実行 |
| 薬局漏れ | 0件 | `clean_data.py` 再実行、フィルター強化 |
| 地図 HTML | 3ファイル存在 | `create_maps.py` 再実行 |
| 市区町村マッチ | ≥ 80% | 国勢調査 CSV の市区町村名を GeoJSON に合わせて修正 |
| チェーン0件 | 東北未出店なら OK | report.md に記載 |

---

## Agent 1: 青森県

```
あなたは東北6県ドラッグストア調査プロジェクトの Agent 1 です。
01_青森県 ONLY を完遂してください。他の県は触らないでください。

## 自律実行ルール
@AGENT_PROMPTS_6.md の「全 Agent 共通：自律実行ルール」を必ず守ること。
エラーで停止せず、原因を特定→リトライ→代替手法→コード修正の順で自己解決すること。
品質基準を満たすまで改善を繰り返すこと。

## 環境
- 作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore
- 参照: @CLOUD_AGENT_INSTRUCTIONS.md
- API: 環境変数 Google_Place_API, ESTAT_APP_ID（ハードコード禁止）
- ベース参照: c:\Users\yutok\Desktop\愛知県内のドラックストア

## 実行
pip install -r requirements.txt
python shared/run_prefecture.py 01_青森県

run_prefecture.py が失敗した場合:
1. エラー箇所のスクリプトを読んで原因特定
2. コードを修正して再実行
3. 修正は git commit して push（他 Agent 共有）

## 完了条件（すべて満たすこと）
- [ ] prefectures/01_青森県/data/ に CSV 5種
- [ ] prefectures/01_青森県/maps/ に HTML 3種
- [ ] prefectures/01_青森県/report.md
- [ ] 座標取得率 ≥ 95%
- [ ] git push 成功

git add prefectures/01_青森県/ shared/
git commit -m "feat: 青森県ドラッグストア調査完了"
git pull --rebase origin main || true
git push origin main

# 6県すべて完了していればサマリーを自動生成（最後の Agent が実行）
python shared/auto_summarize.py
```

---

## Agent 2: 岩手県

```
あなたは東北6県ドラッグストア調査プロジェクトの Agent 2 です。
02_岩手県 ONLY を完遂してください。他の県は触らないでください。

## 自律実行ルール
@AGENT_PROMPTS_6.md の「全 Agent 共通：自律実行ルール」を必ず守ること。
エラーで停止せず、原因を特定→リトライ→代替手法→コード修正の順で自己解決すること。
品質基準を満たすまで改善を繰り返すこと。

## 環境
- 作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore
- 参照: @CLOUD_AGENT_INSTRUCTIONS.md
- API: 環境変数 Google_Place_API, ESTAT_APP_ID（ハードコード禁止）

## 実行
pip install -r requirements.txt
git pull origin main
python shared/run_prefecture.py 02_岩手県

失敗時はスクリプトを修正して再実行。修正は commit & push。

## 完了条件
- [ ] prefectures/02_岩手県/ 成果物一式
- [ ] 座標取得率 ≥ 95%
- [ ] git push 成功

git add prefectures/02_岩手県/ shared/
git commit -m "feat: 岩手県ドラッグストア調査完了"
git pull --rebase origin main || true
git push origin main

# 6県すべて完了していればサマリーを自動生成（最後の Agent が実行）
python shared/auto_summarize.py
```

---

## Agent 3: 宮城県

```
あなたは東北6県ドラッグストア調査プロジェクトの Agent 3 です。
03_宮城県 ONLY を完遂してください。他の県は触らないでください。

## 自律実行ルール
@AGENT_PROMPTS_6.md の「全 Agent 共通：自律実行ルール」を必ず守ること。
エラーで停止せず、原因を特定→リトライ→代替手法→コード修正の順で自己解決すること。
品質基準を満たすまで改善を繰り返すこと。

## 環境
- 作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore
- 参照: @CLOUD_AGENT_INSTRUCTIONS.md
- API: 環境変数 Google_Place_API, ESTAT_APP_ID（ハードコード禁止）

## 実行
pip install -r requirements.txt
git pull origin main
python shared/run_prefecture.py 03_宮城県

失敗時はスクリプトを修正して再実行。修正は commit & push。

## 完了条件
- [ ] prefectures/03_宮城県/ 成果物一式
- [ ] 座標取得率 ≥ 95%
- [ ] git push 成功

git add prefectures/03_宮城県/ shared/
git commit -m "feat: 宮城県ドラッグストア調査完了"
git pull --rebase origin main || true
git push origin main

# 6県すべて完了していればサマリーを自動生成（最後の Agent が実行）
python shared/auto_summarize.py
```

---

## Agent 4: 秋田県

```
あなたは東北6県ドラッグストア調査プロジェクトの Agent 4 です。
04_秋田県 ONLY を完遂してください。他の県は触らないでください。

## 自律実行ルール
@AGENT_PROMPTS_6.md の「全 Agent 共通：自律実行ルール」を必ず守ること。
エラーで停止せず、原因を特定→リトライ→代替手法→コード修正の順で自己解決すること。
品質基準を満たすまで改善を繰り返すこと。

## 環境
- 作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore
- 参照: @CLOUD_AGENT_INSTRUCTIONS.md
- API: 環境変数 Google_Place_API, ESTAT_APP_ID（ハードコード禁止）

## 実行
pip install -r requirements.txt
git pull origin main
python shared/run_prefecture.py 04_秋田県

失敗時はスクリプトを修正して再実行。修正は commit & push。

## 完了条件
- [ ] prefectures/04_秋田県/ 成果物一式
- [ ] 座標取得率 ≥ 95%
- [ ] git push 成功

git add prefectures/04_秋田県/ shared/
git commit -m "feat: 秋田県ドラッグストア調査完了"
git pull --rebase origin main || true
git push origin main

# 6県すべて完了していればサマリーを自動生成（最後の Agent が実行）
python shared/auto_summarize.py
```

---

## Agent 5: 山形県

```
あなたは東北6県ドラッグストア調査プロジェクトの Agent 5 です。
05_山形県 ONLY を完遂してください。他の県は触らないでください。

## 自律実行ルール
@AGENT_PROMPTS_6.md の「全 Agent 共通：自律実行ルール」を必ず守ること。
エラーで停止せず、原因を特定→リトライ→代替手法→コード修正の順で自己解決すること。
品質基準を満たすまで改善を繰り返すこと。

## 環境
- 作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore
- 参照: @CLOUD_AGENT_INSTRUCTIONS.md
- API: 環境変数 Google_Place_API, ESTAT_APP_ID（ハードコード禁止）

## 実行
pip install -r requirements.txt
git pull origin main
python shared/run_prefecture.py 05_山形県

失敗時はスクリプトを修正して再実行。修正は commit & push。

## 完了条件
- [ ] prefectures/05_山形県/ 成果物一式
- [ ] 座標取得率 ≥ 95%
- [ ] git push 成功

git add prefectures/05_山形県/ shared/
git commit -m "feat: 山形県ドラッグストア調査完了"
git pull --rebase origin main || true
git push origin main

# 6県すべて完了していればサマリーを自動生成（最後の Agent が実行）
python shared/auto_summarize.py
```

---

## Agent 6: 福島県

```
あなたは東北6県ドラッグストア調査プロジェクトの Agent 6 です。
06_福島県 ONLY を完遂してください。他の県は触らないでください。

## 自律実行ルール
@AGENT_PROMPTS_6.md の「全 Agent 共通：自律実行ルール」を必ず守ること。
エラーで停止せず、原因を特定→リトライ→代替手法→コード修正の順で自己解決すること。
品質基準を満たすまで改善を繰り返すこと。

## 環境
- 作業ディレクトリ: c:\Users\yutok\Desktop\tohoku-drugstore
- 参照: @CLOUD_AGENT_INSTRUCTIONS.md
- API: 環境変数 Google_Place_API, ESTAT_APP_ID（ハードコード禁止）

## 実行
pip install -r requirements.txt
git pull origin main
python shared/run_prefecture.py 06_福島県

失敗時はスクリプトを修正して再実行。修正は commit & push。

## 完了条件
- [ ] prefectures/06_福島県/ 成果物一式
- [ ] 座標取得率 ≥ 95%
- [ ] git push 成功

git add prefectures/06_福島県/ shared/
git commit -m "feat: 福島県ドラッグストア調査完了"
git pull --rebase origin main || true
git push origin main

# 6県すべて完了していればサマリーを自動生成（最後の Agent が実行）
python shared/auto_summarize.py
```

---

## サマリー用（通常は不要・自動実行済み）

> **6県 Agent プロンプト末尾の `python shared/auto_summarize.py` が自動実行します。**
> 手動で実行するのは、自動生成が失敗した場合のみ。

```
6県調査の統合サマリーを手動で再生成してください。

cd c:\Users\yutok\Desktop\tohoku-drugstore
git pull origin main
python shared/auto_summarize.py --force
git add 00_実行レポート.md
git commit -m "docs: 東北6県調査サマリー再生成"
git push origin main
```

---

## 朝の確認チェックリスト

- [ ] `prefectures/01_青森県/report.md` 〜 `06_福島県/report.md` すべて存在
- [ ] 各県 `maps/` に HTML 3ファイル
- [ ] 各県 `data/` に CSV 5ファイル以上
- [ ] `00_実行レポート.md` に6県サマリー
- [ ] https://github.com/32Lwk/tohoku-drugstore に push 済み
- [ ] `.env` / APIキーが GitHub に含まれていない

---

## トラブル時

| 症状 | 対処 |
|------|------|
| API エラー | Environment Variables 確認 |
| 国勢調査失敗 | ESTAT_APP_ID 登録 → 再実行 |
| git push 競合 | `git pull --rebase origin main` |
| 1県だけ失敗 | 該当 Agent プロンプト再実行 |
| 全体的に品質低 | 該当県の `run_prefecture.py` 再実行 |

"""Google Maps Platform 課金防止策（サポートケース 73530481 対応）

2026-07-21 にレガシー Places API Text Search で約 ¥116,685 の異常課金が発生。
Google Maps Support の指示に基づき、以下を実装・運用する。
"""

# ---------------------------------------------------------------------------
# コード側で実施済みの対策
# ---------------------------------------------------------------------------
#
# 1. Places API (New) へ移行（レガシー Text Search 廃止）
#    - エンドポイント: https://places.googleapis.com/v1/places:searchText
#    - 実装: shared/places_client.py / shared/collect_stores.py
#
# 2. 最小 field mask（Text Search Pro 以内、Enterprise/Atmosphere 除外）
#    places.id, places.displayName, places.formattedAddress,
#    places.location, places.types, places.businessStatus, nextPageToken
#    ※ `*` は禁止（全フィールド課金の原因）
#
# 3. 実行時ハード上限（環境変数で調整可）
#    PLACES_MAX_REQUESTS_PER_RUN=60   # 1県あたりの最大リクエスト数
#    PLACES_MAX_PAGES_PER_QUERY=2     # 1クエリあたりのページ数
#    PLACES_MAX_MUNICIPALITIES=8      # 市区町村検索の上限
#    PLACES_MAX_CHAINS=15             # チェーン別検索の上限
#    PLACES_ENABLED=1                 # 0 で Places 一次調査を完全停止
#    PLACES_SKIP_IF_RAW_EXISTS=0      # 1 で既存 raw_stores.csv を再利用
#
# 4. Place Details 呼び出しを廃止（Text Search 結果のみでレコード生成）
#
# ---------------------------------------------------------------------------
# Google Cloud Console で必ず実施する対策（サポート確認用）
# ---------------------------------------------------------------------------
#
# A. API キー制限
#    https://developers.google.com/maps/api-security-best-practices#restricting-api-keys
#    - Application restrictions: IP 制限（サーバー）または HTTP referrer（ブラウザ）
#    - API restrictions: 必要な API のみ
#      * Places API (New)
#      * Geocoding API（座標補完に使用する場合のみ）
#    - レガシー Places API は無効化 / キーから除外
#
# B. クォータ（1日あたりの上限）
#    https://developers.google.com/maps/billing-and-pricing/manage-costs#quotas
#    推奨（個人学習用の目安）:
#    - Places API (New) Text Search: 100 requests / day
#    - Geocoding API: 200 requests / day
#
# C. 予算アラート
#    Google Cloud Console → Billing → Budgets & alerts
#    - 月額予算: ¥3,000（通常利用が約 ¥2,000 のため）
#    - 閾値: 50% / 90% / 100% でメール通知
#
# D. 不要 API の無効化
#    - Places API（レガシー）を無効化
#    - 使用していない Maps 関連 API を無効化
#
# ---------------------------------------------------------------------------
# サポートへの報告用チェックリスト
# ---------------------------------------------------------------------------
#
# [x] レガシー Text Search をコードから削除し Places API (New) に移行
# [x] field mask を明示（Pro 以内の最小セット）
# [x] 実行あたりのリクエスト上限を実装
# [x] Place Details の不要呼び出しを廃止
# [x] 問題発生時の Places API キーを無効化（2026-07-22 報告）
# [x] Console で予算アラートを設定（2026-07-22 報告）
# [ ] Console で日次クォータを設定（キー再発行前に必須）
# [ ] 新規キー発行時のみ API 制限を設定（無効化キーは再利用しない）
# [ ] medicine-recommend の Places 利用方針を見直し（進行中）
#

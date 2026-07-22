# Ian 対応: Places API (New) 有効化チェックリスト（ケース 73530481）

Ian の指示: **無効化だけでは監視できない**ため、Places API (New) を有効化し、予防策を入れたうえで少量の利用がある状態にする。

## Console 手順（この順で実施）

### 1. Places API (New) を有効化
- Google Cloud Console → APIs & Services → Library
- **Places API (New)** を Enable
- レガシー **Places API** は無効のまま（または使わない）

### 2. 新しい API キーを作成（旧キーは無効のまま）
- APIs & Services → Credentials → Create credentials → API key
- 旧キーは再有効化しない（無効のまま）

### 3. API キー制限（必須）
- **API restrictions**: Restrict key
  - 許可: **Places API (New)** のみ
  - Geocoding が不要なら入れない
- **Application restrictions**:
  - サーバー用途なら IP 制限
  - ブラウザ用途なら HTTP referrer 制限
  - 可能なら両方とも「制限あり」にする

参考: https://developers.google.com/maps/api-security-best-practices#restricting-api-keys

### 4. 日次クォータ（必須・低め）
- APIs & Services → Places API (New) → Quotas
- 目安（個人学習）:
  - Text Search: **20〜50 requests / day**（監視用に極小で可）
- 参考: https://developers.google.com/maps/billing-and-pricing/manage-costs#quotas

### 5. 予算アラート（済なら確認のみ）
- Billing → Budgets & alerts
- 月額目安 ¥3,000、閾値 50% / 90% / 100%

### 6. 監視用の少量テスト（課金を抑えて実施）
Places API (New) Text Search を **数回だけ** 呼び、field mask を必ず付ける。

例（curl）:

```bash
curl -X POST 'https://places.googleapis.com/v1/places:searchText' \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: YOUR_NEW_API_KEY" \
  -H "X-Goog-FieldMask: places.id,places.displayName,places.formattedAddress,places.location" \
  -d '{
    "textQuery": "pharmacy near Tokyo Station",
    "languageCode": "ja",
    "regionCode": "JP",
    "pageSize": 3
  }'
```

注意:
- `X-Goog-FieldMask: *` は絶対に使わない
- ループ・ページネーション・並列実行はしない
- テストは **5回以内** を目安

### 7. Ian に再連絡
チェックリスト完了後、`SUPPORT_EMAIL_DRAFT.md` の「完了報告」文面で返信し、24–48時間モニタリング開始を依頼する。

## 完了報告前の確認

- [ ] Places API (New) 有効
- [ ] 新 API キー作成
- [ ] API 制限・アプリ制限設定
- [ ] 日次クォータ設定（低め）
- [ ] 予算アラート確認
- [ ] 少量テスト実行（field mask 付き）
- [ ] 旧キーは無効のまま

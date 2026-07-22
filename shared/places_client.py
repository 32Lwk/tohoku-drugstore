"""Places API (New) Text Search クライアント

レガシー Places Text Search は Data SKU をまとめて課金するため使わない。
Places API (New) + 最小 field mask で Text Search Pro のみに抑える。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import requests

# Text Search Pro 以内の最小フィールド（Enterprise / Atmosphere は含めない）
# 参照: https://developers.google.com/maps/documentation/places/web-service/data-fields
DEFAULT_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.types",
        "places.businessStatus",
        "nextPageToken",
    ]
)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


class PlacesBudgetExceeded(RuntimeError):
    """1回の実行あたりのリクエスト上限に達した"""


@dataclass
class PlacesClient:
    """Places API (New) の安全なラッパー。

    - 常に明示的な field mask を付与（`*` 禁止）
    - 実行あたりのリクエスト上限で暴走を防止
    - 呼び出し間隔を空けてバースト課金を緩和
    """

    api_key: str
    field_mask: str = DEFAULT_FIELD_MASK
    max_requests: int = 60
    max_pages_per_query: int = 2
    request_interval_sec: float = 0.25
    page_token_wait_sec: float = 2.0
    timeout_sec: float = 30.0
    request_count: int = 0
    query_log: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, api_key: str) -> PlacesClient:
        return cls(
            api_key=api_key,
            max_requests=int(os.getenv("PLACES_MAX_REQUESTS_PER_RUN", "60")),
            max_pages_per_query=int(os.getenv("PLACES_MAX_PAGES_PER_QUERY", "2")),
            request_interval_sec=float(os.getenv("PLACES_REQUEST_INTERVAL_SEC", "0.25")),
        )

    def remaining_budget(self) -> int:
        return max(0, self.max_requests - self.request_count)

    def search_text(self, query: str, *, page_size: int = 20) -> list[dict]:
        """Text Search (New) を実行し、place オブジェクトのリストを返す。"""
        if self.request_count >= self.max_requests:
            raise PlacesBudgetExceeded(
                f"Places API リクエスト上限に到達 "
                f"({self.request_count}/{self.max_requests})。以降の検索を中断します。"
            )

        places: list[dict] = []
        page_token: str | None = None

        for page_idx in range(self.max_pages_per_query):
            # ページネーション途中で予算切れなら、取得済み結果を返して終了
            if page_idx > 0 and self.request_count >= self.max_requests:
                print(
                    f"    リクエスト予算不足のためページネーション中断 "
                    f"({self.request_count}/{self.max_requests})"
                )
                break

            body: dict = {
                "textQuery": query,
                "languageCode": "ja",
                "regionCode": "JP",
                "pageSize": min(page_size, 20),
            }
            if page_token:
                body["pageToken"] = page_token
                time.sleep(self.page_token_wait_sec)

            resp = self._post(body)
            self.request_count += 1
            self.query_log.append(f"[page{page_idx + 1}] {query}")

            batch = resp.get("places") or []
            places.extend(batch)

            page_token = resp.get("nextPageToken")
            if not page_token or not batch:
                break

            time.sleep(self.request_interval_sec)

        return places
    def _post(self, body: dict) -> dict:
        if "*" in self.field_mask:
            raise ValueError("field mask に '*' は使用禁止です（全SKU課金の原因）")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": self.field_mask,
        }
        try:
            r = requests.post(
                TEXT_SEARCH_URL,
                headers=headers,
                json=body,
                timeout=self.timeout_sec,
            )
        except requests.RequestException as e:
            print(f"    Places API 通信エラー: {e}")
            return {}

        if r.status_code != 200:
            # レスポンス本文は短くだけ表示（キー漏洩防止）
            detail = (r.text or "")[:300]
            print(f"    Places API HTTP {r.status_code}: {detail}")
            return {}

        time.sleep(self.request_interval_sec)
        return r.json()

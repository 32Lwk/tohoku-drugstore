"""Places API (New) クライアントの単体テスト（外部 API 呼び出しなし）"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from shared.places_client import DEFAULT_FIELD_MASK, PlacesBudgetExceeded, PlacesClient


class PlacesClientTests(unittest.TestCase):
    def test_field_mask_stays_within_pro_sku(self):
        # Enterprise / Atmosphere フィールドを絶対に含めない
        forbidden = (
            "reviews",
            "rating",
            "priceLevel",
            "websiteUri",
            "nationalPhoneNumber",
            "regularOpeningHours",
            "photos",
            "*",
        )
        for token in forbidden:
            self.assertNotIn(token, DEFAULT_FIELD_MASK)

        for required in (
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.location",
            "places.types",
            "places.businessStatus",
            "nextPageToken",
        ):
            self.assertIn(required, DEFAULT_FIELD_MASK)

    def test_star_field_mask_rejected(self):
        client = PlacesClient(api_key="dummy", field_mask="*", max_requests=1)
        with self.assertRaises(ValueError):
            client._post({"textQuery": "x"})

    def test_budget_stops_extra_requests(self):
        client = PlacesClient(
            api_key="dummy",
            max_requests=1,
            max_pages_per_query=3,
            request_interval_sec=0,
            page_token_wait_sec=0,
        )
        payload = {
            "places": [{"id": "a", "displayName": {"text": "店"}}],
            "nextPageToken": "token-1",
        }
        with patch.object(client, "_post", return_value=payload) as mocked:
            # 1ページ目は成功
            places = client.search_text("ドラッグストア 宮城県")
            self.assertEqual(len(places), 1)
            self.assertEqual(client.request_count, 1)
            # 予算切れ
            with self.assertRaises(PlacesBudgetExceeded):
                client.search_text("ドラッグストア 仙台市")
            self.assertEqual(mocked.call_count, 1)

    def test_headers_include_api_key_and_field_mask(self):
        client = PlacesClient(
            api_key="test-key",
            request_interval_sec=0,
            page_token_wait_sec=0,
            max_requests=5,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"places": []}

        with patch("shared.places_client.requests.post", return_value=mock_resp) as post:
            client.search_text("ツルハドラッグ 青森県")
            self.assertEqual(post.call_count, 1)
            kwargs = post.call_args.kwargs["headers"]
            self.assertEqual(kwargs["X-Goog-Api-Key"], "test-key")
            self.assertEqual(kwargs["X-Goog-FieldMask"], DEFAULT_FIELD_MASK)
            self.assertNotIn("*", kwargs["X-Goog-FieldMask"])


if __name__ == "__main__":
    unittest.main()

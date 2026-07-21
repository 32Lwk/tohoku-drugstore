"""公式サイトからの店舗データ補完（二次調査）"""

import hashlib
import re
import time

import pandas as pd
import requests

from shared.config import PREFECTURES
from shared.utils import ensure_dirs, normalize_address, normalize_chain_name

TSURUHA_YEXT_KEY = "6f3d5119d849cfdb44094409f825f542"
TSURUHA_YEXT_URL = "https://prod-cdn.us.yextapis.com/v2/accounts/me/search/vertical/query"
WELCIA_LIST_URL = "https://store.welcia.co.jp/welcia/api/proxy2/shop/list"


def _make_place_id(source: str, company: str, address: str) -> str:
    raw = f"{source}:{company}:{address}"
    return f"official_{hashlib.md5(raw.encode()).hexdigest()[:16]}"


def _parse_city_name(code_name: str) -> str:
    m = re.search(r"_(.+)$", code_name or "")
    return m.group(1) if m else code_name


def fetch_tsuruha_yext(prefecture: str, center: tuple[float, float]) -> list[dict]:
    stores: list[dict] = []
    offset = 0
    total = None
    while total is None or offset < total:
        params = {
            "experienceKey": "shop-search",
            "api_key": TSURUHA_YEXT_KEY,
            "v": "20220511",
            "version": "PRODUCTION",
            "locale": "ja",
            "input": prefecture,
            "location": f"{center[0]},{center[1]}",
            "verticalKey": "locations",
            "limit": "50",
            "offset": str(offset),
        }
        resp = requests.get(TSURUHA_YEXT_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json().get("response", {})
        results = payload.get("results", [])
        if not results:
            break
        total = payload.get("resultsCount", len(results))
        for item in results:
            data = item.get("data", {})
            addr = data.get("address", {})
            if addr.get("region") != prefecture:
                continue
            line = addr.get("line1", "")
            city = addr.get("city", "")
            address = normalize_address(f"{prefecture}{city}{line}", prefecture)
            chain = data.get("c_brandFilter") or data.get("c_name_GBP") or "ツルハドラッグ"
            chain = normalize_chain_name(chain)
            coord = data.get("yextDisplayCoordinate") or {}
            stores.append(
                {
                    "company": chain,
                    "store_name": data.get("name", chain),
                    "address": address,
                    "place_id": _make_place_id("yext", chain, address),
                    "latitude": coord.get("latitude"),
                    "longitude": coord.get("longitude"),
                    "source": "official_tsuruha",
                }
            )
        offset += 50
        time.sleep(0.1)
    return stores


def fetch_welcia(prefecture: str) -> list[dict]:
    stores: list[dict] = []
    offset = 0
    while True:
        params = {
            "c_d00283": "1",
            "offset": str(offset),
            "limit": "100",
            "ex-code": "only.prior",
            "ignore-i18n": "true",
        }
        resp = requests.get(WELCIA_LIST_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("items", [])
        if not items:
            break
        for item in items:
            address_name = item.get("address_name", "")
            if prefecture not in address_name:
                continue
            address = normalize_address(address_name, prefecture)
            cats = item.get("categories") or []
            chain = cats[0]["name"] if cats else "ウエルシア"
            chain = normalize_chain_name(chain)
            coord = item.get("coord") or {}
            stores.append(
                {
                    "company": chain,
                    "store_name": item.get("name", chain),
                    "address": address,
                    "place_id": _make_place_id("welcia", chain, address),
                    "latitude": coord.get("lat"),
                    "longitude": coord.get("lon"),
                    "source": "official_welcia",
                }
            )
        total = payload.get("count", {}).get("total", 0)
        offset += 100
        if offset >= total:
            break
        time.sleep(0.1)
    return stores


def fetch_official_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    paths = ensure_dirs(slug)

    existing = pd.DataFrame()
    if paths["raw_csv"].exists():
        existing = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")

    print("\n[二次調査] 公式サイトから店舗補完")
    new_stores: list[dict] = []

    try:
        tsuruha = fetch_tsuruha_yext(prefecture, cfg["center"])
        print(f"  ツルハグループ(Yext): {len(tsuruha)}件")
        new_stores.extend(tsuruha)
    except Exception as e:
        print(f"  ツルハグループ取得失敗: {e}")

    try:
        welcia = fetch_welcia(prefecture)
        print(f"  ウエルシアAPI: {len(welcia)}件")
        new_stores.extend(welcia)
    except Exception as e:
        print(f"  ウエルシア取得失敗: {e}")

    if not new_stores:
        print("  公式サイトからの追加データなし")
        return existing

    new_df = pd.DataFrame(new_stores)
    if existing.empty:
        merged = new_df
    else:
        merged = pd.concat([existing, new_df], ignore_index=True)

    if "place_id" in merged.columns:
        merged = merged.drop_duplicates(subset=["place_id"], keep="first")
    merged = merged.drop_duplicates(subset=["company", "address"], keep="first")

    merged.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
    added = len(merged) - len(existing)
    print(f"  raw_stores.csv 更新: +{added}件 (合計{len(merged)}件)")
    return merged


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "01_青森県"
    fetch_official_for_prefecture(target)

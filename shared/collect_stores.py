"""Google Places API による店舗収集"""

import json
import time
from pathlib import Path

import googlemaps
import pandas as pd

from shared.config import CHAIN_NORMALIZE, KNOWN_CHAINS, PREFECTURES
from shared.utils import ensure_dirs, load_api_key, normalize_address, normalize_chain_name

# Place Details で有効な fields（types は無効 → 検索結果から取得）
DETAIL_FIELDS = ["name", "formatted_address", "geometry", "business_status"]

KNOWN_CHAIN_NAMES = set(KNOWN_CHAINS) | set(CHAIN_NORMALIZE.values())


def get_municipalities_from_geojson(geojson_path: Path) -> list[str]:
    if not geojson_path.exists():
        return []
    with open(geojson_path, encoding="utf-8") as f:
        geo = json.load(f)
    cities = set()
    for feature in geo.get("features", []):
        props = feature.get("properties", {})
        gun = props.get("N03_003") or ""
        city = props.get("N03_004") or ""
        ward = props.get("N03_005") or ""
        # 政令市は区単位で検索（Text Search の20件制限対策）
        if city and ward:
            cities.add(f"{city}{ward}")
        elif gun and city:
            cities.add(f"{gun}{city}")
        elif city:
            cities.add(city)
    return sorted(cities)


def _chain_aliases(company: str) -> set[str]:
    aliases = {company}
    for src, dst in CHAIN_NORMALIZE.items():
        if dst == company or src == company:
            aliases.add(src)
            aliases.add(dst)
    return {a for a in aliases if a}


def _assign_company(store_name: str, company: str, query: str) -> str | None:
    """チェーン精査時は店舗名一致必須。不一致なら None（スキップ）。"""
    derived = normalize_chain_name(store_name, query)
    if not company:
        return derived
    aliases = _chain_aliases(company)
    if any(a in store_name for a in aliases) or derived == company:
        return company
    return None


def _place_from_search_result(place: dict, prefecture: str, company: str, query: str) -> dict | None:
    """Text Search 結果から直接レコード生成（geometry があれば Details 省略）"""
    geom = place.get("geometry", {}).get("location")
    address = place.get("formatted_address") or place.get("vicinity") or ""
    if not address:
        return None

    address = normalize_address(address, prefecture)
    if not address.startswith(prefecture):
        return None

    store_name = place.get("name", "")
    chain = _assign_company(store_name, company, query)
    if chain is None:
        return None

    return {
        "company": chain,
        "store_name": store_name,
        "address": address,
        "place_id": place.get("place_id", ""),
        "latitude": geom.get("lat") if geom else None,
        "longitude": geom.get("lng") if geom else None,
        "source": "google_places",
    }


def _fetch_place_details(gmaps, place_id: str) -> dict | None:
    try:
        details = gmaps.place(place_id=place_id, language="ja", fields=DETAIL_FIELDS)
    except Exception as e:
        print(f"      Details API error: {e}")
        return None
    if details.get("status") != "OK":
        return None
    return details.get("result")


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set) -> list[dict]:
    results = []
    page_token = None

    while True:
        try:
            if page_token:
                time.sleep(2.0)  # next_page_token 使用前の必須待機
                resp = gmaps.places(query=query, language="ja", region="jp", page_token=page_token)
            else:
                resp = gmaps.places(query=query, language="ja", region="jp")
        except Exception as e:
            print(f"    検索エラー: {query} -> {e}")
            break

        status = resp.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            if status:
                print(f"    API status: {status} ({query})")
            break
        if status != "OK":
            break

        for place in resp.get("results", []):
            pid = place.get("place_id")
            if not pid or pid in seen_ids:
                continue

            types = place.get("types", [])
            if "pharmacy" in types and "drugstore" not in types and "store" not in types:
                continue

            # geometry + address が検索結果にあれば Details 省略
            if place.get("geometry", {}).get("location"):
                record = _place_from_search_result(place, prefecture, company, query)
                if record and record.get("latitude"):
                    if place.get("business_status") == "CLOSED_PERMANENTLY":
                        continue
                    seen_ids.add(pid)
                    results.append(record)
                    time.sleep(0.05)
                    continue

            # Details が必要な場合
            r = _fetch_place_details(gmaps, pid)
            if not r or r.get("business_status") == "CLOSED_PERMANENTLY":
                continue

            address = normalize_address(r.get("formatted_address", ""), prefecture)
            if not address.startswith(prefecture):
                continue

            store_name = r.get("name", "")
            chain = _assign_company(store_name, company, query)
            if chain is None:
                continue

            geom = r.get("geometry", {}).get("location", {})
            seen_ids.add(pid)
            results.append({
                "company": chain,
                "store_name": store_name,
                "address": address,
                "place_id": pid,
                "latitude": geom.get("lat"),
                "longitude": geom.get("lng"),
                "source": "google_places",
            })
            time.sleep(0.12)

        page_token = resp.get("next_page_token")
        if not page_token:
            break

    return results


def collect_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    paths = ensure_dirs(slug)

    try:
        api_key = load_api_key()
    except ValueError:
        print("  Google_Place_API 未設定 → Places一次調査をスキップ（二次調査で補完）")
        cols = ["company", "store_name", "address", "place_id", "latitude", "longitude", "source"]
        df = pd.DataFrame(columns=cols)
        if paths["raw_csv"].exists():
            return pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
        df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
        return df

    gmaps = googlemaps.Client(key=api_key)
    seen_ids: set[str] = set()
    all_stores: list[dict] = []

    # [1] 県単位広域検索（ページネーション対応）
    print(f"\n[1/3] 県単位検索: ドラッグストア × {prefecture}")
    batch = search_places(gmaps, f"ドラッグストア {prefecture}", prefecture, "", seen_ids)
    all_stores.extend(batch)
    print(f"    +{len(batch)}件 (累計{len(all_stores)})")
    time.sleep(0.3)

    # [2] 主要市区町村検索（政令市区を優先、最大25）
    municipalities = get_municipalities_from_geojson(paths["geojson"])
    priority = [c for c in municipalities if c.endswith(("市", "区"))]
    other = [c for c in municipalities if c not in priority]
    municipalities = (priority + other)[:25]
    if municipalities:
        print(f"\n[2/3] 市区町村検索: {len(municipalities)}件")
        for city in municipalities:
            batch = search_places(gmaps, f"ドラッグストア {city} {prefecture}", prefecture, "", seen_ids)
            all_stores.extend(batch)
            if batch:
                print(f"    {city}: +{len(batch)}件")
            time.sleep(0.2)

    # [3] チェーン別 × 県単位（既知チェーンのみ）
    discovered = {
        normalize_chain_name(s["store_name"]) for s in all_stores
    } & KNOWN_CHAIN_NAMES
    chains_to_search = sorted(KNOWN_CHAIN_NAMES | discovered)
    print(f"\n[3/3] チェーン別県単位検索: {len(chains_to_search)}チェーン（既知のみ）")
    for chain in chains_to_search:
        before = len(all_stores)
        q = f"{chain} {prefecture}"
        batch = search_places(gmaps, q, prefecture, normalize_chain_name(chain), seen_ids)
        all_stores.extend(batch)
        added = len(all_stores) - before
        if added:
            print(f"    {chain}: +{added}件")
        time.sleep(0.2)

    df = pd.DataFrame(all_stores)
    if df.empty:
        df = pd.DataFrame(columns=["company", "store_name", "address", "place_id", "latitude", "longitude", "source"])

    df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
    print(f"\n生データ保存: {paths['raw_csv']} ({len(df)}件)")
    return df


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    collect_for_prefecture(slug)

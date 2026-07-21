"""Google Places API による店舗収集"""

import json
import time
from pathlib import Path

import googlemaps
import pandas as pd

from shared.config import KNOWN_CHAINS, PREFECTURES
from shared.utils import ensure_dirs, load_api_key, normalize_address, normalize_chain_name


def get_municipalities_from_geojson(geojson_path: Path) -> list[str]:
    if not geojson_path.exists():
        return []
    with open(geojson_path, encoding="utf-8") as f:
        geo = json.load(f)
    cities = set()
    for feature in geo.get("features", []):
        props = feature.get("properties", {})
        # N03_003=郡・政令市名, N03_004=市区町村名（N03_001=都道府県は付けない）
        prefix = props.get("N03_003") or ""
        name = props.get("N03_004") or ""
        if not name or name in ("所属未定地",):
            continue
        if prefix and name:
            cities.add(f"{prefix}{name}")
        else:
            cities.add(name)
    return sorted(cities)


def _place_from_result(place: dict, prefecture: str, company: str, query: str) -> dict | None:
    """Text Search / Place Details の結果から店舗レコードを組み立てる。"""
    if place.get("business_status") == "CLOSED_PERMANENTLY":
        return None

    address = normalize_address(place.get("formatted_address", ""), prefecture)
    if prefecture not in address:
        return None

    store_name = place.get("name", "")
    chain = company or normalize_chain_name(store_name, query)
    geom = place.get("geometry", {}).get("location", {})

    return {
        "company": chain,
        "store_name": store_name,
        "address": address,
        "place_id": place.get("place_id"),
        "latitude": geom.get("lat"),
        "longitude": geom.get("lng"),
        "source": "google_places",
    }


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set) -> list[dict]:
    results = []
    next_page_token = None

    for page in range(3):  # Text Search は最大3ページ（60件）
        try:
            if next_page_token:
                time.sleep(2.0)  # next_page_token は発行直後は無効
                resp = gmaps.places(query=query, language="ja", region="jp", page_token=next_page_token)
            else:
                resp = gmaps.places(query=query, language="ja", region="jp")
        except Exception as e:
            print(f"    検索エラー: {query} -> {e}")
            return results

        status = resp.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"    検索status異常: {query} -> {status} {resp.get('error_message', '')}")
            return results
        if status == "ZERO_RESULTS":
            return results

        for place in resp.get("results", []):
            pid = place.get("place_id")
            if not pid or pid in seen_ids:
                continue

            types = place.get("types", [])
            if "pharmacy" in types and "drugstore" not in types and "store" not in types:
                continue

            seen_ids.add(pid)

            # Place Details（types は invalid field のため含めない）
            detail_place = None
            try:
                details = gmaps.place(
                    place_id=pid,
                    language="ja",
                    fields=["name", "formatted_address", "geometry", "business_status"],
                )
                if details.get("status") == "OK":
                    detail_place = details["result"]
                    detail_place["place_id"] = pid
            except Exception as e:
                print(f"    Place Details失敗(フォールバック): {pid[:12]}... -> {e}")

            # Details失敗時は Text Search の結果を使う
            record = _place_from_result(detail_place or place, prefecture, company, query)
            if record:
                results.append(record)
            time.sleep(0.12)

        next_page_token = resp.get("next_page_token")
        if not next_page_token:
            break

    return results


def collect_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    paths = ensure_dirs(slug)
    api_key = load_api_key(required=False)
    if not api_key:
        print("  Google_Place_API 未設定 → Places一次調査をスキップ（二次調査で補完）")
        df = pd.DataFrame(columns=["company", "store_name", "address", "place_id", "latitude", "longitude", "source"])
        if paths["raw_csv"].exists():
            return pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
        df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
        return df

    gmaps = googlemaps.Client(key=api_key)

    municipalities = get_municipalities_from_geojson(paths["geojson"])
    if not municipalities:
        municipalities = [prefecture]
        print(f"  GeoJSON未設定のため県名のみで検索: {prefecture}")

    seen_ids: set[str] = set()
    all_stores: list[dict] = []

    print(f"\n[1/2] 広域検索: ドラッグストア × {len(municipalities)}市区町村")
    for city in municipalities:
        q = f"ドラッグストア {city} {prefecture}"
        batch = search_places(gmaps, q, prefecture, "", seen_ids)
        all_stores.extend(batch)
        if batch:
            print(f"    {city}: +{len(batch)}件 (累計{len(all_stores)})")
        time.sleep(0.2)

    discovered_chains = set()
    for s in all_stores:
        chain = normalize_chain_name(s["store_name"])
        if chain != "不明":
            discovered_chains.add(chain)

    chains_to_search = sorted(set(KNOWN_CHAINS) | discovered_chains)
    print(f"\n[2/2] チェーン別検索: {len(chains_to_search)}チェーン")
    for chain in chains_to_search:
        before = len(all_stores)
        for city in municipalities:
            q = f"{chain} {city} {prefecture}"
            batch = search_places(gmaps, q, prefecture, normalize_chain_name(chain), seen_ids)
            all_stores.extend(batch)
            time.sleep(0.15)
        added = len(all_stores) - before
        if added:
            print(f"    {chain}: +{added}件")

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

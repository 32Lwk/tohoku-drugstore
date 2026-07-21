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


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set) -> list[dict]:
    results = []
    try:
        resp = gmaps.places(query=query, language="ja", region="jp")
    except Exception as e:
        print(f"    検索エラー: {query} -> {e}")
        return results

    status = resp.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        print(f"    検索status異常: {query} -> {status} {resp.get('error_message', '')}")
        return results
    if status != "OK":
        return results

    for place in resp.get("results", []):
        pid = place.get("place_id")
        if not pid or pid in seen_ids:
            continue

        types = place.get("types", [])
        if "pharmacy" in types and "drugstore" not in types and "store" not in types:
            continue

        # Text Search の結果を優先利用（Place Details の fields 不整合を回避し API 節約）
        store_name = place.get("name", "")
        formatted = place.get("formatted_address", "")
        geom = place.get("geometry", {}).get("location", {})

        if not formatted or not geom:
            try:
                details = gmaps.place(
                    place_id=pid,
                    language="ja",
                    fields=["name", "formatted_address", "geometry", "business_status"],
                )
            except Exception as e:
                print(f"    detailsエラー: {pid} -> {e}")
                continue
            if details.get("status") != "OK":
                continue
            r = details["result"]
            if r.get("business_status") == "CLOSED_PERMANENTLY":
                continue
            store_name = r.get("name", store_name)
            formatted = r.get("formatted_address", formatted)
            geom = r.get("geometry", {}).get("location", {}) or geom
            time.sleep(0.12)

        address = normalize_address(formatted, prefecture)
        if prefecture not in address:
            continue

        seen_ids.add(pid)
        chain = company or normalize_chain_name(store_name, query)
        results.append(
            {
                "company": chain,
                "store_name": store_name,
                "address": address,
                "place_id": pid,
                "latitude": geom.get("lat"),
                "longitude": geom.get("lng"),
                "source": "google_places",
            }
        )

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
    # 県全体 + 主要市区町村（全市区町村×全チェーンは過多のため）
    chain_locations = [prefecture] + [c for c in municipalities if c.endswith(("市", "区"))][:25]
    for chain in chains_to_search:
        before = len(all_stores)
        for loc in chain_locations:
            q = f"{chain} {loc}" if loc != prefecture else f"{chain} {prefecture}"
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

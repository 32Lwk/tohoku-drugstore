"""Google Places API による店舗収集"""

import json
import time
from pathlib import Path

import googlemaps
import pandas as pd

from shared.config import KNOWN_CHAINS, PREFECTURES
from shared.utils import ensure_dirs, load_api_key, normalize_address, normalize_chain_name, address_in_prefecture


def get_municipalities_from_geojson(geojson_path: Path) -> list[str]:
    if not geojson_path.exists():
        return []
    with open(geojson_path, encoding="utf-8") as f:
        geo = json.load(f)
    cities = set()
    for feature in geo.get("features", []):
        props = feature.get("properties", {})
        prefix = props.get("N03_003") or props.get("N03_001") or ""
        name = props.get("N03_004") or props.get("N03_002") or ""
        if prefix and name:
            cities.add(f"{prefix}{name}")
        elif name:
            cities.add(name)
    return sorted(cities)


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set) -> list[dict]:
    results = []
    try:
        resp = gmaps.places(query=query, language="ja", region="jp")
    except Exception as e:
        print(f"    検索エラー: {query} -> {e}")
        return results

    if resp.get("status") != "OK":
        return results

    for place in resp.get("results", []):
        pid = place.get("place_id")
        if not pid or pid in seen_ids:
            continue

        types = place.get("types", [])
        if "pharmacy" in types and "drugstore" not in types and "store" not in types:
            continue

        seen_ids.add(pid)
        try:
            # Place Details の fields に "types" は不可（"type" も非推奨）。types は Text Search 結果を使用。
            details = gmaps.place(
                place_id=pid,
                language="ja",
                fields=["name", "formatted_address", "geometry", "business_status"],
            )
        except Exception as e:
            print(f"    place details エラー: {pid} -> {e}")
            continue

        if details.get("status") != "OK":
            continue

        r = details["result"]
        if r.get("business_status") == "CLOSED_PERMANENTLY":
            continue

        raw_address = r.get("formatted_address", "") or ""
        if not address_in_prefecture(raw_address, prefecture):
            continue
        address = normalize_address(raw_address, prefecture)

        store_name = r.get("name", "")
        # チェーン指定検索では店舗名にキーワードが含まれるものだけ採用（誤ヒット防止）
        if company:
            if not _store_matches_chain(store_name, company):
                continue
            chain = company
        else:
            chain = normalize_chain_name(store_name, query)
        geom = r.get("geometry", {}).get("location", {})

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
        time.sleep(0.12)

    return results


def _store_matches_chain(store_name: str, company: str) -> bool:
    """曖昧なチェーン名の誤マッチを防ぐ"""
    name = store_name or ""
    name_l = name.lower()
    if company in ("コスモス",):
        return any(
            k in name
            for k in ("ドラッグストアコスモス", "コスモス薬品", "コスモスドラッグ", "cosmos")
        ) or (name.startswith("コスモス") and "ドラッグ" in name)
    if company in ("クリエイト", "クリエイトSD", "クリエイトエス・ディー"):
        return any(k in name for k in ("クリエイトエス", "クリエイトSD", "create sd", "Create SD")) or (
            "クリエイト" in name and "ドラッグ" in name
        )
    if company == "キョーリン" or company == "キョーリン堂":
        return "キョーリン堂" in name or ("キョーリン" in name and "ドラッグ" in name)
    keys = [company]
    if company == "GENKY":
        keys.append("ゲンキー")
    if company == "マツモトキヨシ":
        keys.extend(["マツキヨ", "matsukiyo"])
    if company == "カワチ薬品":
        keys.append("カワチ")
    if company == "セイムス":
        keys.extend(["ドラッグセイムス", "ドラッグストアセイムス"])
    return any(k.lower() in name_l for k in keys if k)


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

    # 既知チェーンのみ精査（発見名の先頭語検索は誤ヒット・件数爆発の原因）
    discovered = {
        normalize_chain_name(s["store_name"])
        for s in all_stores
        if normalize_chain_name(s["store_name"]) != "不明"
    }
    chains_to_search = sorted(set(KNOWN_CHAINS) | discovered)
    print(f"\n[2/2] チェーン別検索: {len(chains_to_search)}チェーン (発見済{len(discovered)})")
    for chain in chains_to_search:
        before = len(all_stores)
        # 広域で見つかったチェーンは市区町村単位、未発見は県単位で補完
        targets = municipalities if chain in discovered else [prefecture]
        for city in targets:
            q = f"{chain} {city}" if city == prefecture else f"{chain} {city} {prefecture}"
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

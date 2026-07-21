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
        # N03_003=郡名, N03_004=市区町村名（N03_001は県名なので prefix に使わない）
        gun = props.get("N03_003") or ""
        name = props.get("N03_004") or ""
        if not name or name == "所属未定地":
            continue
        cities.add(f"{gun}{name}" if gun else name)
    return sorted(cities)


def _chain_aliases(company: str) -> list[str]:
    aliases = {
        "GENKY": ["GENKY", "ゲンキー"],
        "マツモトキヨシ": ["マツモトキヨシ", "マツキヨ"],
        "スギ薬局": ["スギ薬局", "スギドラッグ", "スギ"],
        "カワチ薬品": ["カワチ薬品", "カワチ", "カワachi"],
        "ツルハドラッグ": ["ツルハ", "ツルハドラッグ"],
        "ウエルシア": ["ウエルシア", "ウェルシア"],
        "サンドラック": ["サンドラッグ", "サンドラック"],
        "ココカラファイン": ["ココカラ", "ココカラファイン"],
        "クスリのアオキ": ["クスリのアオキ", "アオキ"],
        "コスモス": ["コスモス"],
        "セイムス": ["セイムス"],
        "Vドラッグ": ["Vドラッグ", "Ｖドラッグ"],
        "ZIPドラッグ": ["ZIPドラッグ", "ジップドラッグ"],
    }
    return aliases.get(company, [company])


def _parse_place(place: dict, prefecture: str, company: str, query: str, seen_ids: set) -> dict | None:
    pid = place.get("place_id")
    if not pid or pid in seen_ids:
        return None

    types = place.get("types", [])
    if "pharmacy" in types and "drugstore" not in types and "store" not in types:
        return None

    if place.get("business_status") == "CLOSED_PERMANENTLY":
        return None

    address = normalize_address(place.get("formatted_address", ""), prefecture)
    if prefecture not in address:
        return None

    store_name = place.get("name", "")
    # チェーン指定検索時は店舗名にチェーン名が含まれるものだけ採用（誤ヒット防止）
    if company and company not in ("その他", "不明", ""):
        if not any(a.lower() in store_name.lower() for a in _chain_aliases(company)):
            return None

    seen_ids.add(pid)
    chain = company or normalize_chain_name(store_name, query)
    geom = place.get("geometry", {}).get("location", {})

    return {
        "company": chain,
        "store_name": store_name,
        "address": address,
        "place_id": pid,
        "latitude": geom.get("lat"),
        "longitude": geom.get("lng"),
        "source": "google_places",
    }


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set, max_pages: int = 3) -> list[dict]:
    """Text Search のみで収集（Place Details 不要・ページネーション対応）"""
    results = []
    page_token = None

    for _ in range(max_pages):
        try:
            if page_token:
                time.sleep(2.0)  # next_page_token 有効化待ち
                resp = gmaps.places(query=query, language="ja", region="jp", page_token=page_token)
            else:
                resp = gmaps.places(query=query, language="ja", region="jp")
        except Exception as e:
            print(f"    検索エラー: {query} -> {e}")
            break

        status = resp.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            if status:
                print(f"    検索 status={status}: {query} {resp.get('error_message', '')}")
            break

        for place in resp.get("results", []):
            parsed = _parse_place(place, prefecture, company, query, seen_ids)
            if parsed:
                results.append(parsed)

        page_token = resp.get("next_page_token")
        if not page_token:
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
    cities_with_hits: set[str] = set()

    print(f"\n[1/2] 広域検索: ドラッグストア × {len(municipalities)}市区町村")
    for city in municipalities:
        q = f"ドラッグストア {city} {prefecture}"
        batch = search_places(gmaps, q, prefecture, "", seen_ids, max_pages=3)
        all_stores.extend(batch)
        if batch:
            cities_with_hits.add(city)
            print(f"    {city}: +{len(batch)}件 (累計{len(all_stores)})")
        time.sleep(0.2)

    discovered_chains = set()
    for s in all_stores:
        chain = normalize_chain_name(s["store_name"])
        if chain != "その他" and chain != "不明":
            discovered_chains.add(chain)

    # 既知チェーンのみ精査（発見済みを優先、未知店舗名はチェーン化しない）
    chains_to_search = sorted(set(KNOWN_CHAINS) | discovered_chains)
    # ヒットのあった市区町村を優先。なければ全市区町村
    target_cities = sorted(cities_with_hits) if cities_with_hits else municipalities

    print(f"\n[2/2] チェーン別検索: {len(chains_to_search)}チェーン（先に県単位、ヒット時のみ市区町村精査）")
    for chain in chains_to_search:
        before = len(all_stores)
        norm = normalize_chain_name(chain)

        # 県単位で存在確認（最大60件）
        pref_batch = search_places(
            gmaps, f"{chain} {prefecture}", prefecture, norm, seen_ids, max_pages=3
        )
        all_stores.extend(pref_batch)
        time.sleep(0.2)

        # 県内に存在するチェーンのみ市区町村精査（網羅性向上）
        if pref_batch or norm in discovered_chains:
            for city in target_cities:
                q = f"{chain} {city} {prefecture}"
                batch = search_places(gmaps, q, prefecture, norm, seen_ids, max_pages=2)
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

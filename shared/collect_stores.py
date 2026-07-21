"""Google Places API による店舗収集"""

import json
import time
from pathlib import Path

import googlemaps
import pandas as pd

from shared.config import KNOWN_CHAINS, NON_DRUGSTORE_KEYWORDS, PREFECTURES
from shared.utils import ensure_dirs, load_api_key, normalize_address, normalize_chain_name


DRUGSTORE_NAME_HINTS = (
    "ドラッグ",
    "Drug",
    "DRUG",
    "ウエルシア",
    "ウェルシア",
    "マツモトキヨシ",
    "ツルハ",
    "コスモス",
    "ゲンキー",
    "GENKY",
    "薬王堂",
    "カワチ",
    "サンドラッグ",
    "サンドラック",
    "ココカラ",
    "セイムス",
    "サツドラ",
    "アオキ",
    "スギ",
    "クリエイト",
    "杏林堂",
    "トモズ",
    "キリン堂",
    "ハック",
    "セキ薬品",
    "よどや",
    "なの花",
    "コクミン",
    "ダイコク",
    "ハッピー",
    "くすり",
    "クスリ",
)


def _looks_like_drugstore(store_name: str, types: list[str]) -> bool:
    name = store_name or ""
    if any(kw in name for kw in NON_DRUGSTORE_KEYWORDS):
        return False
    if "drugstore" in types:
        return True
    if any(h in name for h in DRUGSTORE_NAME_HINTS):
        return True
    # pharmacy 単体は調剤薬局の可能性が高いので名前ヒント必須
    return False


def get_municipalities_from_geojson(geojson_path: Path) -> list[str]:
    if not geojson_path.exists():
        return []
    with open(geojson_path, encoding="utf-8") as f:
        geo = json.load(f)
    cities = set()
    for feature in geo.get("features", []):
        props = feature.get("properties", {})
        # N03_003=郡・政令市区名, N03_004=市区町村名（空の場合は都道府県名を付けない）
        gun = props.get("N03_003") or ""
        name = props.get("N03_004") or ""
        if not name or name == "所属未定":
            continue
        cities.add(f"{gun}{name}" if gun else name)
    return sorted(cities)


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set, max_pages: int = 3) -> list[dict]:
    results = []
    page_token = None

    for _page in range(max_pages):
        try:
            kwargs = {"query": query, "language": "ja", "region": "jp"}
            if page_token:
                kwargs["page_token"] = page_token
                time.sleep(2.0)  # next_page_token は発行直後は無効
            resp = gmaps.places(**kwargs)
        except Exception as e:
            print(f"    検索エラー: {query} -> {e}")
            break

        status = resp.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"    検索status異常: {query} -> {status} {resp.get('error_message', '')}")
            break
        if status == "ZERO_RESULTS":
            break

        for place in resp.get("results", []):
            pid = place.get("place_id")
            if not pid or pid in seen_ids:
                continue

            types = place.get("types", [])
            if "pharmacy" in types and "drugstore" not in types and "store" not in types:
                continue

            # Text Search 結果に geometry / address があれば Place Details を省略
            store_name = place.get("name", "")
            if not _looks_like_drugstore(store_name, types):
                continue
            raw_addr = place.get("formatted_address") or place.get("vicinity") or ""
            geom = place.get("geometry", {}).get("location", {})
            business_status = place.get("business_status")

            if not raw_addr or not geom:
                try:
                    details = gmaps.place(
                        place_id=pid,
                        language="ja",
                        # Place Details の fields は 'types' ではなく 'type'（単数）
                        fields=["name", "formatted_address", "geometry", "type", "business_status"],
                    )
                except Exception as e:
                    print(f"    place details エラー: {pid} -> {e}")
                    continue

                if details.get("status") != "OK":
                    continue

                r = details["result"]
                store_name = r.get("name", store_name)
                raw_addr = r.get("formatted_address", raw_addr)
                geom = r.get("geometry", {}).get("location", {}) or geom
                business_status = r.get("business_status", business_status)
                time.sleep(0.12)

            if business_status == "CLOSED_PERMANENTLY":
                continue

            address = normalize_address(raw_addr, prefecture)
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
        # 既知チェーンのみ二次検索対象（店舗名先頭語の汚染を防止）
        if chain in KNOWN_CHAINS or chain in ("スギ薬局", "薬王堂", "ハッピードラッグ", "GENKY"):
            discovered_chains.add(chain)

    chains_to_search = sorted(set(KNOWN_CHAINS) | discovered_chains)
    print(f"\n[2/2] チェーン別検索: {len(chains_to_search)}チェーン（県単位→存在確認後に市区町村精査）")
    present_chains: set[str] = set()
    for chain in chains_to_search:
        before = len(all_stores)
        q = f"{chain} ドラッグストア {prefecture}"
        batch = search_places(gmaps, q, prefecture, normalize_chain_name(chain), seen_ids)
        all_stores.extend(batch)
        time.sleep(0.2)
        added = len(all_stores) - before
        if added:
            present_chains.add(chain)
            print(f"    {chain}: 県単位 +{added}件")

    if present_chains:
        print(f"\n[2b] 存在チェーンの市区町村精査: {len(present_chains)}チェーン × {len(municipalities)}市区町村")
        for chain in sorted(present_chains):
            before = len(all_stores)
            for city in municipalities:
                q = f"{chain} {city} {prefecture}"
                batch = search_places(gmaps, q, prefecture, normalize_chain_name(chain), seen_ids, max_pages=1)
                all_stores.extend(batch)
                time.sleep(0.12)
            added = len(all_stores) - before
            if added:
                print(f"    {chain}: 市区町村精査 +{added}件")

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

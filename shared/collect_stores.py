"""Google Places API (New) による店舗収集

課金対策:
- レガシー Text Search (`maps.googleapis.com/.../place/textsearch`) は使わない
- Places API (New) + 最小 field mask（Text Search Pro 以内）
- 1実行あたりのリクエスト上限 / ページ上限 / 市区町村数上限
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from shared.config import KNOWN_CHAINS, PREFECTURES
from shared.places_client import PlacesBudgetExceeded, PlacesClient
from shared.utils import ensure_dirs, load_api_key, normalize_address, normalize_chain_name

RAW_COLUMNS = [
    "company",
    "store_name",
    "address",
    "place_id",
    "latitude",
    "longitude",
    "source",
]


def get_municipalities_from_geojson(geojson_path: Path) -> list[str]:
    if not geojson_path.exists():
        return []
    import json

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


def _place_id(place: dict) -> str:
    pid = place.get("id") or ""
    if not pid and isinstance(place.get("name"), str):
        # name 形式: "places/ChIJ..."
        pid = place["name"].rsplit("/", 1)[-1]
    return pid


def _display_name(place: dict) -> str:
    dn = place.get("displayName") or {}
    if isinstance(dn, dict):
        return dn.get("text") or ""
    return str(dn or "")


def _record_from_place(place: dict, prefecture: str, company: str, query: str) -> dict | None:
    address = place.get("formattedAddress") or ""
    if not address:
        return None

    address = normalize_address(address, prefecture)
    if prefecture not in address:
        return None

    if place.get("businessStatus") == "CLOSED_PERMANENTLY":
        return None

    loc = place.get("location") or {}
    store_name = _display_name(place)
    chain = company or normalize_chain_name(store_name, query)

    return {
        "company": chain,
        "store_name": store_name,
        "address": address,
        "place_id": _place_id(place),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
        "source": "google_places_new",
    }


def _is_pharmacy_only_types(types: list) -> bool:
    """薬局のみ（ドラッグストアでない）を除外"""
    types = types or []
    if "pharmacy" in types and "drugstore" not in types and "store" not in types:
        return True
    return False


def search_places(
    client: PlacesClient,
    query: str,
    prefecture: str,
    company: str,
    seen_ids: set[str],
) -> list[dict]:
    results: list[dict] = []
    try:
        places = client.search_text(query)
    except PlacesBudgetExceeded as e:
        print(f"    {e}")
        return results

    for place in places:
        pid = _place_id(place)
        if not pid or pid in seen_ids:
            continue
        if _is_pharmacy_only_types(place.get("types") or []):
            continue

        record = _record_from_place(place, prefecture, company, query)
        if not record or record.get("latitude") is None:
            continue

        seen_ids.add(pid)
        results.append(record)

    return results


def _places_enabled() -> bool:
    return os.getenv("PLACES_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def _skip_if_raw_exists(raw_csv: Path) -> bool:
    flag = os.getenv("PLACES_SKIP_IF_RAW_EXISTS", "0").strip().lower()
    if flag not in {"1", "true", "yes", "on"}:
        return False
    if not raw_csv.exists():
        return False
    try:
        df = pd.read_csv(raw_csv, encoding="utf-8-sig")
    except Exception:
        return False
    return len(df) > 0


def collect_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    paths = ensure_dirs(slug)

    if not _places_enabled():
        print("  PLACES_ENABLED=0 → Places一次調査をスキップ")
        if paths["raw_csv"].exists():
            return pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
        df = pd.DataFrame(columns=RAW_COLUMNS)
        df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
        return df

    if _skip_if_raw_exists(paths["raw_csv"]):
        print(f"  既存 raw_stores.csv を再利用（API呼び出しなし）: {paths['raw_csv']}")
        return pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")

    try:
        api_key = load_api_key()
    except ValueError:
        print("  Google_Place_API 未設定 → Places一次調査をスキップ（二次調査で補完）")
        df = pd.DataFrame(columns=RAW_COLUMNS)
        if paths["raw_csv"].exists():
            return pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
        df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
        return df

    client = PlacesClient.from_env(api_key)
    max_municipalities = int(os.getenv("PLACES_MAX_MUNICIPALITIES", "8"))
    max_chains = int(os.getenv("PLACES_MAX_CHAINS", "15"))

    print(
        f"  Places API (New) 予算: max_requests={client.max_requests}, "
        f"max_pages={client.max_pages_per_query}, "
        f"municipalities≤{max_municipalities}, chains≤{max_chains}"
    )
    print(f"  field mask: {client.field_mask}")

    seen_ids: set[str] = set()
    all_stores: list[dict] = []

    # [1] 県単位広域検索
    print(f"\n[1/3] 県単位検索: ドラッグストア × {prefecture}")
    batch = search_places(client, f"ドラッグストア {prefecture}", prefecture, "", seen_ids)
    all_stores.extend(batch)
    print(f"    +{len(batch)}件 (累計{len(all_stores)}, API {client.request_count}回)")

    # [2] 主要市区町村検索（件数制限で API 節約）
    municipalities = get_municipalities_from_geojson(paths["geojson"])[:max_municipalities]
    if municipalities and client.remaining_budget() > 0:
        print(f"\n[2/3] 市区町村検索: {len(municipalities)}件")
        for city in municipalities:
            if client.remaining_budget() <= 0:
                print("    リクエスト予算不足のため市区町村検索を中断")
                break
            batch = search_places(
                client, f"ドラッグストア {city} {prefecture}", prefecture, "", seen_ids
            )
            all_stores.extend(batch)
            if batch:
                print(f"    {city}: +{len(batch)}件")
            time.sleep(0.1)

    # [3] チェーン別 × 県単位（既知チェーン優先・件数上限）
    discovered = {normalize_chain_name(s["store_name"]) for s in all_stores} - {"不明"}
    # 既知チェーンを優先し、発見チェーンは予算内で追加
    prioritized = list(dict.fromkeys([*KNOWN_CHAINS, *sorted(discovered)]))
    chains_to_search = prioritized[:max_chains]
    print(f"\n[3/3] チェーン別県単位検索: {len(chains_to_search)}チェーン")
    for chain in chains_to_search:
        if client.remaining_budget() <= 0:
            print("    リクエスト予算不足のためチェーン検索を中断")
            break
        before = len(all_stores)
        q = f"{chain} {prefecture}"
        batch = search_places(client, q, prefecture, normalize_chain_name(chain), seen_ids)
        all_stores.extend(batch)
        added = len(all_stores) - before
        if added:
            print(f"    {chain}: +{added}件")
        time.sleep(0.1)

    df = pd.DataFrame(all_stores)
    if df.empty:
        df = pd.DataFrame(columns=RAW_COLUMNS)

    df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
    print(
        f"\n生データ保存: {paths['raw_csv']} ({len(df)}件, "
        f"Places API呼出 {client.request_count}/{client.max_requests}回)"
    )
    return df


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    collect_for_prefecture(slug)

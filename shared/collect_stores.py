"""Google Places API による店舗収集"""

import json
import time
from pathlib import Path

import googlemaps
import pandas as pd

from shared.config import KNOWN_CHAINS, PREFECTURES
from shared.utils import ensure_dirs, load_api_key, normalize_address, normalize_chain_name


def get_municipalities_from_geojson(geojson_path: Path) -> list[str]:
    """市区町村名を返す。郡部は「郡+町村」、市は市名のみ（県名は付けない）。"""
    if not geojson_path.exists():
        return []
    with open(geojson_path, encoding="utf-8") as f:
        geo = json.load(f)
    cities = set()
    for feature in geo.get("features", []):
        props = feature.get("properties", {})
        name = (props.get("N03_004") or "").strip()
        if not name or name == "所属未定地":
            continue
        gun = (props.get("N03_003") or "").strip()
        if gun:
            cities.add(f"{gun}{name}")
        else:
            cities.add(name)
    return sorted(cities)


def search_places(gmaps, query: str, prefecture: str, company: str, seen_ids: set) -> list[dict]:
    """Text Search（ページネーション対応）。Details不要（検索結果に住所・座標あり）。"""
    results = []
    page_token = None

    for _page in range(3):  # 最大60件（20×3）
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
            if status in ("OVER_QUERY_LIMIT", "RESOURCE_EXHAUSTED"):
                print(f"    API制限: {status} — 60秒待機")
                time.sleep(60)
                continue
            break

        for place in resp.get("results", []):
            pid = place.get("place_id")
            if not pid or pid in seen_ids:
                continue

            if place.get("business_status") == "CLOSED_PERMANENTLY":
                continue

            store_name = place.get("name", "")
            types = place.get("types", [])
            if "pharmacy" in types and "drugstore" not in types and "store" not in types:
                from_name_pre = normalize_chain_name(store_name)
                if from_name_pre in ("不明",) or from_name_pre == store_name.split(" ")[0]:
                    continue

            address = normalize_address(place.get("formatted_address", ""), prefecture)
            if prefecture not in address:
                continue

            from_name = normalize_chain_name(store_name)
            if from_name and from_name != "不明":
                chain = from_name
            elif company and company != "不明":
                # チェーン検索: 店舗名にそのチェーンを示す語が必要
                aliases = {
                    "GENKY": ["GENKY", "ゲンキー"],
                    "ハッピードラッグ": ["ハッピー", "ハッピードラッグ"],
                    "マツモトキヨシ": ["マツモトキヨシ", "マツモト", "マツキヨ"],
                    "ツルハドラッグ": ["ツルハ"],
                    "ウエルシア": ["ウエルシア", "ウェルシア"],
                    "サンドラッグ": ["サンドラッグ", "サンド"],
                    "コスモス": ["コスモス"],
                    "クスリのアオキ": ["アオキ"],
                    "カワチ薬品": ["カワチ"],
                    "スギ薬局": ["スギ"],
                    "セイムス": ["セイムス"],
                    "ココカラファイン": ["ココカラ"],
                    "サツドラ": ["サツドラ"],
                }
                terms = aliases.get(company, [company])
                if not any(t in store_name for t in terms):
                    continue
                # コスモスは誤ヒットが多いのでドラッグ系に限定
                # コスモスは誤ヒットが多いのでドラッグ系に限定
                if company == "コスモス" and not any(
                    k in store_name for k in ("ドラッグ", "Drug", "薬局", "コスモス薬品", "ドラッグストア")
                ):
                    continue
                chain = company
            else:
                # 広域検索の不明店舗はドラッグストアらしい名前のみ残す
                if not any(k in store_name for k in ("ドラッグ", "Drug", "DRUG")):
                    continue
                chain = "その他"

            geom = place.get("geometry", {}).get("location", {})
            seen_ids.add(pid)
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
        time.sleep(0.15)

    return results


def collect_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    paths = ensure_dirs(slug)
    api_key = load_api_key(required=False)
    if not api_key:
        print("  Google_Place_API 未設定 → Places一次調査をスキップ（二次調査で補完）")
        df = pd.DataFrame(
            columns=["company", "store_name", "address", "place_id", "latitude", "longitude", "source"]
        )
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

    # 既存 raw があれば place_id を引き継ぎ（増分マージ用）
    if paths["raw_csv"].exists():
        try:
            prev = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
            if "place_id" in prev.columns:
                seen_ids.update(prev["place_id"].dropna().astype(str).tolist())
                all_stores.extend(prev.to_dict("records"))
                print(f"  既存 raw を読み込み: {len(prev)}件（増分収集）")
        except Exception:
            pass

    print(f"\n[1/3] 広域検索: ドラッグストア × {len(municipalities)}市区町村")
    for city in municipalities:
        q = f"ドラッグストア {city} {prefecture}"
        before = len(all_stores)
        batch = search_places(gmaps, q, prefecture, "", seen_ids)
        all_stores.extend(batch)
        added = len(all_stores) - before
        if added:
            print(f"    {city}: +{added}件 (累計{len(all_stores)})")
        time.sleep(0.2)

    discovered_chains = set()
    for s in all_stores:
        chain = normalize_chain_name(str(s.get("store_name", "")))
        # 既知チェーンに正規化されたものだけを二次検索対象にする
        from shared.config import CHAIN_NORMALIZE, KNOWN_CHAINS

        known_set = set(KNOWN_CHAINS) | set(CHAIN_NORMALIZE.values()) | set(CHAIN_NORMALIZE.keys())
        if chain in known_set:
            discovered_chains.add(CHAIN_NORMALIZE.get(chain, chain))

    # 正規化後のチェーン名で検索（別名は CHAIN_NORMALIZE で統一）
    from shared.config import CHAIN_NORMALIZE

    raw_chains = set(KNOWN_CHAINS) | discovered_chains
    chains_to_search = sorted(
        {
            CHAIN_NORMALIZE.get(c, c)
            for c in raw_chains
            if c not in ("スギドラッグ", "ゲンキー", "マツキヨ", "カワachi", "ハッピー・ドラッグ", "サンドラック")
        }
    )

    print(f"\n[2/3] 県全体チェーン検索: {len(chains_to_search)}チェーン")
    for chain in chains_to_search:
        before = len(all_stores)
        q = f"{chain} {prefecture}"
        batch = search_places(gmaps, q, prefecture, chain, seen_ids)
        all_stores.extend(batch)
        added = len(all_stores) - before
        if added:
            print(f"    {chain}（県全体）: +{added}件")
        time.sleep(0.2)

    # 主要市のみチェーン×市区町村（取りこぼし防止）
    major_cities = [c for c in municipalities if c.endswith("市")]
    print(f"\n[3/3] 市×チェーン精査: {len(major_cities)}市 × {len(chains_to_search)}チェーン")
    for chain in chains_to_search:
        before = len(all_stores)
        for city in major_cities:
            q = f"{chain} {city} {prefecture}"
            batch = search_places(gmaps, q, prefecture, chain, seen_ids)
            all_stores.extend(batch)
            time.sleep(0.15)
        added = len(all_stores) - before
        if added:
            print(f"    {chain}: +{added}件")

    df = pd.DataFrame(all_stores)
    if df.empty:
        df = pd.DataFrame(
            columns=["company", "store_name", "address", "place_id", "latitude", "longitude", "source"]
        )
    else:
        # 店舗名からチェーン再判定
        def _fix_company(row):
            from_name = normalize_chain_name(str(row.get("store_name", "")))
            if from_name and from_name != "不明":
                return from_name
            return CHAIN_NORMALIZE.get(str(row.get("company", "")), row.get("company"))

        df["company"] = df.apply(_fix_company, axis=1)
        df = df.drop_duplicates(subset=["place_id"], keep="first")

    df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
    print(f"\n生データ保存: {paths['raw_csv']} ({len(df)}件)")
    return df


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    collect_for_prefecture(slug)

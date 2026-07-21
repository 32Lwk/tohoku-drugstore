"""国勢調査2020 市区町村別 人口・高齢化率 取得"""

import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from shared.config import PREFECTURES
from shared.utils import ensure_dirs

CACHE_DIR = Path(__file__).resolve().parent / "census_cache"
CACHE_DIR.mkdir(exist_ok=True)

# 令和2年国勢調査 都道府県・市区町村別の主な結果（xlsx）
ESTAT_MUNICIPAL_XLSX = {
    "url": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032143614&fileKind=0",
    "referer": "https://www.e-stat.go.jp/stat-search/files?stat_infid=000032143614",
}


def _download_estat_xlsx() -> bytes:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 tohoku-drugstore/1.0"})
    session.get(ESTAT_MUNICIPAL_XLSX["referer"], timeout=60)
    resp = session.get(ESTAT_MUNICIPAL_XLSX["url"], timeout=180)
    resp.raise_for_status()
    return resp.content


def _parse_estat_xlsx(content: bytes, prefecture: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_excel(BytesIO(content), sheet_name="第１面事項_2020年", header=None)
    pref_code = next(v["code"] for v in PREFECTURES.values() if v["name"] == prefecture)
    rows = df[df[0].astype(str).str.startswith(f"{pref_code}_")]

    pop_rows = []
    aging_rows = []
    for _, row in rows.iterrows():
        code_name = str(row[1])
        if pd.isna(code_name) or code_name == "nan":
            continue
        city = _parse_city_name(code_name)
        if not city or city == prefecture:
            continue
        total = _to_float(row[4])
        elderly = _to_float(row[16])
        aging_rate = _to_float(row[19])
        if total:
            pop_rows.append({"市区町村": city, "人口": total})
        if elderly and total:
            aging_rows.append(
                {
                    "市区町村": city,
                    "総数": total,
                    "65歳以上": elderly,
                    "高齢化率": aging_rate if aging_rate else round(elderly / total * 100, 2),
                }
            )

    pop_df = pd.DataFrame(pop_rows).drop_duplicates("市区町村")
    aging_df = pd.DataFrame(aging_rows).drop_duplicates("市区町村")
    return pop_df, aging_df


def _parse_city_name(code_name: str) -> str:
    m = re.search(r"_(.+)$", code_name)
    return m.group(1) if m else code_name


def _to_float(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def _build_from_geojson(slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """フォールバック: GeoJSON から市区町村名のみ抽出（人口は後で手動補完）"""
    paths = ensure_dirs(slug)
    import json

    with open(paths["geojson"], encoding="utf-8") as f:
        geo = json.load(f)

    cities = []
    for feat in geo.get("features", []):
        p = feat.get("properties", {})
        prefix = p.get("N03_003") or ""
        name = p.get("N03_004") or ""
        if prefix and name:
            cities.append(f"{prefix}{name}")
        elif name:
            cities.append(name)

    pop_df = pd.DataFrame({"市区町村": sorted(set(cities)), "人口": None})
    aging_df = pd.DataFrame({"市区町村": sorted(set(cities)), "高齢化率": None})
    return pop_df, aging_df


def fetch_for_prefecture(slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    prefecture = cfg["name"]
    pref_cache_pop = CACHE_DIR / f"{cfg['code']}_population.csv"
    pref_cache_aging = CACHE_DIR / f"{cfg['code']}_aging.csv"

    if pref_cache_pop.exists() and pref_cache_aging.exists():
        pop_df = pd.read_csv(pref_cache_pop, encoding="utf-8-sig")
        aging_df = pd.read_csv(pref_cache_aging, encoding="utf-8-sig")
    else:
        try:
            xlsx_cache = CACHE_DIR / "estat_municipal_2020.xlsx"
            if not xlsx_cache.exists():
                print("  国勢調査xlsxをダウンロード中...")
                xlsx_cache.write_bytes(_download_estat_xlsx())
            pop_df, aging_df = _parse_estat_xlsx(xlsx_cache.read_bytes(), prefecture)
            if pop_df.empty:
                raise ValueError("該当県データなし")
            pop_df.to_csv(pref_cache_pop, index=False, encoding="utf-8-sig")
            aging_df.to_csv(pref_cache_aging, index=False, encoding="utf-8-sig")
        except Exception as e:
            print(f"  国勢調査自動取得失敗 ({e}) → GeoJSONフォールバック")
            pop_df, aging_df = _build_from_geojson(slug)

    pop_df.to_csv(paths["population_csv"], index=False, encoding="utf-8-sig")
    aging_df.to_csv(paths["aging_csv"], index=False, encoding="utf-8-sig")
    print(f"  人口: {len(pop_df)}市区町村 / 高齢化率: {len(aging_df)}市区町村")
    return pop_df, aging_df


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    fetch_for_prefecture(slug)

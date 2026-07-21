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

# 国勢調査2020 人口等基本集計 市区町村（全国一括CSV）
NATIONAL_CENSUS_URL = (
    "https://www.e-stat.go.jp/stat-search/file-download?"
    "statInfId=000032143617&fileKind=1"
)


def _download_national_census() -> Path:
    national_cache = CACHE_DIR / "national_census_2020.csv"
    if national_cache.exists():
        return national_cache

    print("  全国国勢調査CSVをダウンロード中...")
    resp = requests.get(NATIONAL_CENSUS_URL, timeout=180, allow_redirects=True)
    resp.raise_for_status()

    for enc in ["cp932", "shift_jis", "utf-8-sig", "utf-8"]:
        try:
            text = resp.content.decode(enc)
            national_cache.write_text(text, encoding="utf-8-sig")
            return national_cache
        except UnicodeDecodeError:
            continue

    national_cache.write_bytes(resp.content)
    return national_cache


def _parse_national_csv(path: Path, prefecture: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    for enc in ["utf-8-sig", "cp932", "shift_jis"]:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            break
        except Exception:
            continue
    else:
        raise ValueError(f"CSV読込失敗: {path}")

    cols = df.columns.tolist()
    area_col = next((c for c in cols if "地域" in str(c) or "市区町村" in str(c)), cols[0])
    df_pref = df[df[area_col].astype(str).str.contains(prefecture.replace("県", ""), na=False)].copy()

    if df_pref.empty:
        df_pref = df[df.astype(str).apply(lambda r: r.str.contains(prefecture, na=False).any(), axis=1)]

    pop_col = next((c for c in cols if "人口" in str(c) and "密度" not in str(c)), None)
    elderly_col = next((c for c in cols if "65" in str(c) or "高齢" in str(c)), None)
    total_col = next((c for c in cols if "総数" in str(c) or "人口" in str(c)), None)

    pop_rows = []
    aging_rows = []

    for _, row in df_pref.iterrows():
        city_raw = str(row[area_col])
        city = _normalize_city_name(city_raw, prefecture)
        if not city or city == prefecture:
            continue

        pop = _to_float(row.get(pop_col)) if pop_col else None
        elderly = _to_float(row.get(elderly_col)) if elderly_col else None
        total = _to_float(row.get(total_col)) if total_col else pop

        if pop:
            pop_rows.append({"市区町村": city, "人口": pop})
        if elderly and total and total > 0:
            aging_rows.append({
                "市区町村": city,
                "総数": total,
                "65歳以上": elderly,
                "高齢化率": round(elderly / total * 100, 2),
            })

    pop_df = pd.DataFrame(pop_rows).drop_duplicates("市区町村")
    aging_df = pd.DataFrame(aging_rows).drop_duplicates("市区町村")
    return pop_df, aging_df


def _normalize_city_name(raw: str, prefecture: str) -> str:
    s = raw.replace(prefecture, "").strip()
    m = re.search(r"(.+?(?:市|区|町|村))", s)
    return m.group(1) if m else s


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
            national = _download_national_census()
            pop_df, aging_df = _parse_national_csv(national, prefecture)
            if pop_df.empty:
                raise ValueError("該当県データなし")
            pop_df.to_csv(pref_cache_pop, index=False, encoding="utf-8-sig")
            aging_df.to_csv(pref_cache_aging, index=False, encoding="utf-8-sig")
        except Exception as e:
            print(f"  国勢調査自動取得失敗 ({e}) → e-Stat手動DLを試行")
            pop_df, aging_df = _fetch_estat_manual(cfg["code"], prefecture)

    pop_df.to_csv(paths["population_csv"], index=False, encoding="utf-8-sig")
    aging_df.to_csv(paths["aging_csv"], index=False, encoding="utf-8-sig")
    print(f"  人口: {len(pop_df)}市区町村 / 高齢化率: {len(aging_df)}市区町村")
    return pop_df, aging_df


def _fetch_estat_manual(pref_code: str, prefecture: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    e-Stat 統計ダッシュボードから都道府県別CSVを取得。
    https://www.e-stat.go.jp/stat-search/files?page=1&layout=dataset&toukei=00200521
    """
    alt_urls = [
        f"https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032143617&fileKind=1",
    ]
    for url in alt_urls:
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                tmp = CACHE_DIR / "tmp_census.csv"
                tmp.write_bytes(r.content)
                pop_df, aging_df = _parse_national_csv(tmp, prefecture)
                if not pop_df.empty:
                    return pop_df, aging_df
        except Exception:
            continue

    raise RuntimeError(
        f"{prefecture} の国勢調査データ取得に失敗。"
        " Cloud Agent: e-Stat から2020国勢調査CSVをDLし "
        f"shared/census_cache/{pref_code}_population.csv に配置してください。"
    )


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    fetch_for_prefecture(slug)

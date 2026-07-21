"""市区町村別 店舗密度分析"""

import re

import pandas as pd

from shared.config import PREFECTURES
from shared.utils import ensure_dirs


def extract_municipality(address: str, prefecture: str, city_keys: list[str] | None = None) -> str:
    addr = (address or "").replace(prefecture, "")
    # GeoJSON キー（郡付き）で最長一致
    if city_keys:
        for key in sorted(city_keys, key=len, reverse=True):
            if key and key in (address or ""):
                return key
    parts = re.findall(r"(.+?(?:市|区|町|村))", addr)
    if not parts:
        return "不明"
    if len(parts) >= 2 and parts[0].endswith("郡"):
        return f"{parts[0]}{parts[1]}"
    if len(parts) >= 2 and parts[0].endswith("市") and parts[1].endswith("区"):
        return f"{parts[0]}{parts[1]}"
    return parts[0]


def analyze_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)

    stores = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")
    pop = pd.read_csv(paths["population_csv"], encoding="utf-8-sig")
    city_keys = pop["市区町村"].dropna().astype(str).tolist()

    stores["市区町村"] = stores["address"].apply(
        lambda a: extract_municipality(a, cfg["name"], city_keys)
    )
    store_counts = stores.groupby("市区町村").size().reset_index(name="店舗数")

    merged = pop.merge(store_counts, on="市区町村", how="left")
    merged["店舗数"] = merged["店舗数"].fillna(0).astype(int)
    merged["人口10万人当たり店舗数"] = merged.apply(
        lambda r: round(r["店舗数"] / r["人口"] * 100000, 2)
        if pd.notna(r["人口"]) and r["人口"] > 0
        else None,
        axis=1,
    )

    matched = merged["店舗数"].notna().sum()  # all have store counts after fillna
    # マッチ率: 店舗側市区町村が人口表に存在するもの
    store_cities = set(stores["市区町村"])
    pop_cities = set(pop["市区町村"].astype(str))
    rate = round(len(store_cities & pop_cities) / max(len(store_cities), 1) * 100, 1)
    print(f"  市区町村マッチ率: {rate}% ({len(store_cities & pop_cities)}/{len(store_cities)})")

    merged.to_csv(paths["density_csv"], index=False, encoding="utf-8-sig")
    print(f"  密度分析: {paths['density_csv']} ({len(merged)}件)")
    return merged


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    analyze_for_prefecture(slug)

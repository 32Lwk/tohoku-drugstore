"""市区町村別 店舗密度分析"""

import re

import pandas as pd

from shared.config import PREFECTURES
from shared.utils import ensure_dirs


def extract_municipality(
    address: str,
    prefecture: str,
    known_municipalities: list[str] | None = None,
) -> str:
    """住所から市区町村名を抽出。known_municipalities があれば最長一致で照合。"""
    addr = address.replace(prefecture, "")

    if known_municipalities:
        matched = [m for m in known_municipalities if m in addr]
        if matched:
            return max(matched, key=lambda m: (len(m), -addr.index(m)))

    parts = re.findall(r"(.+?(?:市|区|町|村))", addr)
    if not parts:
        return "不明"
    if len(parts) >= 2 and parts[0].endswith("市") and parts[1].endswith("区"):
        return f"{parts[0]}{parts[1]}"
    name = parts[0]
    # 郡付き表記（例: 上北郡おいらせ町）→ 郡名を除去
    if "郡" in name:
        name = re.sub(r"^.+郡", "", name)
    return name


def analyze_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)

    stores = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")
    pop = pd.read_csv(paths["population_csv"], encoding="utf-8-sig")

    known = pop["市区町村"].tolist()
    stores["市区町村"] = stores["address"].apply(
        lambda a: extract_municipality(a, cfg["name"], known)
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

    merged.to_csv(paths["density_csv"], index=False, encoding="utf-8-sig")
    print(f"  密度分析: {paths['density_csv']} ({len(merged)}件)")
    return merged


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    analyze_for_prefecture(slug)

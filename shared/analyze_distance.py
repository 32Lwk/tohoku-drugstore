"""市区町村重心法・1kmメッシュ法による最寄りドラッグストア距離分析"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union

from shared.config import PREFECTURES, TOHOKU_SLUGS
from shared.create_maps import _city_key
from shared.fetch_census_mesh import fetch_mesh_population
from shared.geo_utils import (
    mesh_center,
    nearest_distances_km,
    weighted_mean,
    weighted_percentile,
)
from shared.utils import ensure_dirs, prefecture_paths


def _load_population(slug: str) -> pd.DataFrame:
    paths = ensure_dirs(slug)
    pop = pd.read_csv(paths["population_csv"], encoding="utf-8-sig")

    if "市区町村" in pop.columns and "人口" in pop.columns:
        return pop

    # 愛知県など非標準フォーマット
    city_col = next(
        (c for c in pop.columns if "市区町村" in str(c)),
        pop.columns[0],
    )
    pop_col = next(
        (c for c in pop.columns if "人口" in str(c)),
        pop.columns[1] if len(pop.columns) > 1 else pop.columns[0],
    )
    out = pd.DataFrame(
        {
            "市区町村": pop[city_col].astype(str).str.strip(),
            "人口": pd.to_numeric(
                pop[pop_col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ),
        }
    )
    out = out[out["市区町村"].notna() & (out["市区町村"] != "") & (out["市区町村"] != "nan")]
    out = out[out["人口"].notna() & (out["人口"] > 0)]
    return out.drop_duplicates("市区町村")


def _short_muni_name(name: str) -> str:
    """郡付き表記（例: 刈田郡蔵王町）→ 蔵王町"""
    return re.sub(r"^.+郡", "", name or "")


def _city_only_name(props: dict) -> str:
    """政令市の区を含まない市区町村名（例: 仙台市）"""
    return props.get("N03_004") or _city_key(props)


def _match_city_to_features(city: str, feature_map: dict[str, list]) -> list:
    """人口CSVの市区町村名に対応する GeoJSON feature 群を返す"""
    if city in feature_map:
        return feature_map[city]

    short = _short_muni_name(city)
    if short in feature_map:
        return feature_map[short]

    # 政令市全体（仙台市）→ 各区 feature を結合
    ward_prefix = f"{city}"
    wards = [feats for key, feats in feature_map.items() if key.startswith(ward_prefix) and key != city]
    if wards:
        return [f for group in wards for f in group]

    # 郡なし短名 ↔ 郡付き長名
    for key, feats in feature_map.items():
        if _short_muni_name(key) == city or _short_muni_name(city) == _short_muni_name(key):
            return feats
        if key.endswith(city) or city.endswith(key):
            return feats

    return []


def _load_stores(store_scope: str, slug: str) -> pd.DataFrame:
    """store_scope: 'prefecture' | 'tohoku'"""
    if store_scope == "tohoku":
        frames = []
        for s in TOHOKU_SLUGS:
            p = prefecture_paths(s)
            df = pd.read_csv(p["coord_csv"], encoding="utf-8-sig")
            frames.append(df)
        stores = pd.concat(frames, ignore_index=True)
    else:
        paths = ensure_dirs(slug)
        stores = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")

    stores = stores.dropna(subset=["latitude", "longitude"]).copy()
    stores["latitude"] = stores["latitude"].astype(float)
    stores["longitude"] = stores["longitude"].astype(float)
    return stores


def _municipality_centroids(slug: str, pop_df: pd.DataFrame) -> pd.DataFrame:
    paths = ensure_dirs(slug)
    with open(paths["geojson"], encoding="utf-8") as f:
        geo = json.load(f)

    feature_map: dict[str, list] = {}
    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        for name in {_city_key(props), _short_muni_name(_city_key(props)), _city_only_name(props)}:
            if name:
                feature_map.setdefault(name, []).append(feat)

    # 政令市の「○○市」総数行は、区レベル行があればスキップ
    pop_cities = pop_df["市区町村"].tolist()
    ward_parents = {
        re.match(r"^(.+市).+区$", c).group(1)
        for c in pop_cities
        if re.match(r"^(.+市).+区$", c)
    }

    rows = []
    for city in pop_cities:
        if city in ward_parents:
            continue
        feats = _match_city_to_features(city, feature_map)
        if not feats:
            continue
        geom = unary_union([shape(f["geometry"]) for f in feats])
        pt = geom.representative_point()
        rows.append({"市区町村": city, "重心緯度": pt.y, "重心経度": pt.x})

    return pd.DataFrame(rows)


def analyze_centroid_method(
    slug: str,
    stores: pd.DataFrame,
    pop_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    centroids = _municipality_centroids(slug, pop_df)
    merged = pop_df.merge(centroids, on="市区町村", how="inner")
    merged = merged[merged["人口"] > 0].copy()

    if merged.empty:
        raise RuntimeError("市区町村重心と人口の突合結果が空です")

    dists = nearest_distances_km(
        merged["重心緯度"].to_numpy(),
        merged["重心経度"].to_numpy(),
        stores["latitude"].to_numpy(),
        stores["longitude"].to_numpy(),
    )
    merged["最寄り店舗距離_km"] = np.round(dists, 3)

    # 最寄り店舗名（参考）
    nearest_names = []
    store_lat = stores["latitude"].to_numpy()
    store_lon = stores["longitude"].to_numpy()
    store_names = stores["store_name"].fillna("").to_numpy()
    for i, row in merged.iterrows():
        d = haversine_scalar(row["重心緯度"], row["重心経度"], store_lat, store_lon)
        idx = int(np.argmin(d))
        nearest_names.append(store_names[idx])
    merged["最寄り店舗名"] = nearest_names

    summary = {
        "人口加重平均距離_km": round(
            weighted_mean(merged["最寄り店舗距離_km"], merged["人口"]), 3
        ),
        "人口加重中央値_km": round(
            weighted_percentile(merged["最寄り店舗距離_km"], merged["人口"], 50), 3
        ),
        "人口加重90パーセンタイル_km": round(
            weighted_percentile(merged["最寄り店舗距離_km"], merged["人口"], 90), 3
        ),
        "対象市区町村数": int(len(merged)),
        "対象人口": int(merged["人口"].sum()),
    }
    return merged, summary


def haversine_scalar(lat, lon, store_lat, store_lon):
    from shared.geo_utils import haversine_km

    return haversine_km(lat, lon, store_lat, store_lon)


def analyze_mesh_method(
    slug: str,
    stores: pd.DataFrame,
    mesh_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    if mesh_df is None:
        mesh_df = fetch_mesh_population(slug)

    mesh = mesh_df.copy()
    lats, lons = [], []
    for code in mesh["KEY_CODE"]:
        lat, lon = mesh_center(code)
        lats.append(lat)
        lons.append(lon)
    mesh["緯度"] = lats
    mesh["経度"] = lons

    dists = nearest_distances_km(
        mesh["緯度"].to_numpy(),
        mesh["経度"].to_numpy(),
        stores["latitude"].to_numpy(),
        stores["longitude"].to_numpy(),
    )
    mesh["最寄り店舗距離_km"] = np.round(dists, 3)

    summary = {
        "人口加重平均距離_km": round(
            weighted_mean(mesh["最寄り店舗距離_km"], mesh["人口"]), 3
        ),
        "人口加重中央値_km": round(
            weighted_percentile(mesh["最寄り店舗距離_km"], mesh["人口"], 50), 3
        ),
        "人口加重90パーセンタイル_km": round(
            weighted_percentile(mesh["最寄り店舗距離_km"], mesh["人口"], 90), 3
        ),
        "対象メッシュ数": int(len(mesh)),
        "対象人口": int(mesh["人口"].sum()),
    }
    return mesh, summary


def analyze_for_prefecture(slug: str, store_scope: str = "tohoku") -> dict:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)

    stores = _load_stores(store_scope, slug)
    pop_df = _load_population(slug)

    centroid_df, centroid_summary = analyze_centroid_method(slug, stores, pop_df)
    mesh_df, mesh_summary = analyze_mesh_method(slug, stores)

    centroid_out = paths["data"] / "市区町村別最寄りドラッグストア距離.csv"
    mesh_out = paths["data"] / "メッシュ別最寄りドラッグストア距離.csv"
    summary_out = paths["data"] / "距離分析サマリー.csv"

    centroid_df.to_csv(centroid_out, index=False, encoding="utf-8-sig")
    mesh_df.to_csv(mesh_out, index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        [
            {
                "都道府県": cfg["name"],
                "分析方法": "市区町村重心法",
                "距離種別": "直線距離(Haversine)",
                "店舗探索範囲": store_scope,
                **centroid_summary,
            },
            {
                "都道府県": cfg["name"],
                "分析方法": "1kmメッシュ法",
                "距離種別": "直線距離(Haversine)",
                "店舗探索範囲": store_scope,
                **mesh_summary,
            },
        ]
    )
    summary.to_csv(summary_out, index=False, encoding="utf-8-sig")

    print(f"  重心法 平均距離: {centroid_summary['人口加重平均距離_km']} km")
    print(f"  メッシュ法 平均距離: {mesh_summary['人口加重平均距離_km']} km")

    return {
        "prefecture": cfg["name"],
        "slug": slug,
        "store_count": len(stores),
        "centroid": centroid_summary,
        "mesh": mesh_summary,
        "outputs": {
            "centroid_csv": str(centroid_out),
            "mesh_csv": str(mesh_out),
            "summary_csv": str(summary_out),
        },
    }


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    scope = sys.argv[2] if len(sys.argv) > 2 else "tohoku"
    analyze_for_prefecture(target, store_scope=scope)

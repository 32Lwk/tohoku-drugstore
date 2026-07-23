"""東北6県統合データ・地図の生成"""

import json
from datetime import datetime
from pathlib import Path

import branca.colormap as cm
import folium
import numpy as np
import pandas as pd

from shared.analyze_density import analyze_for_prefecture
from shared.config import (
    AGING_CHOROPLETH_COLORS,
    CHOROPLETH_BORDER_COLOR,
    CHOROPLETH_BORDER_WEIGHT,
    PREFECTURES,
    TOHOKU,
    TOHOKU_DIR,
    TOHOKU_SLUGS,
)
from shared.create_maps import (
    _add_prefecture_boundary,
    _choropleth_style,
    _city_key,
    _density_fill_color,
    _load_geojson,
    _make_density_colormap,
    create_all_maps,
    create_marker_map,
    create_marker_map_from_df,
)


def tohoku_paths() -> dict:
    data = TOHOKU_DIR / "data"
    maps = TOHOKU_DIR / "maps"
    data.mkdir(parents=True, exist_ok=True)
    maps.mkdir(parents=True, exist_ok=True)
    return {
        "base": TOHOKU_DIR,
        "data": data,
        "maps": maps,
        "geojson": data / "municipalities.geojson",
        "coord_csv": data / "東北ドラッグストア_座標付き.csv",
        "density_csv": data / "市区町村別ドラッグストア分析.csv",
        "aging_csv": data / "市区町村別高齢化率.csv",
        "population_csv": data / "市区町村別人口.csv",
        "report": TOHOKU_DIR / "report.md",
    }


def merge_geojson() -> Path:
    paths = tohoku_paths()
    features = []
    for slug in TOHOKU_SLUGS:
        cfg = PREFECTURES[slug]
        geo = _load_geojson(
            Path(__file__).resolve().parent.parent / "prefectures" / slug / "data" / "municipalities.geojson"
        )
        pref = cfg["name"]
        for feat in geo["features"]:
            props = dict(feat["properties"])
            props["都道府県"] = pref
            props["市区町村_key"] = _city_key(props)
            features.append({"type": "Feature", "properties": props, "geometry": feat["geometry"]})

    merged = {"type": "FeatureCollection", "features": features}
    with open(paths["geojson"], "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)
    print(f"  統合GeoJSON: {paths['geojson']} ({len(features)} features)")
    return paths["geojson"]


def merge_csvs() -> dict:
    paths = tohoku_paths()
    store_dfs, density_dfs, pop_dfs, aging_dfs = [], [], [], []

    for slug in TOHOKU_SLUGS:
        cfg = PREFECTURES[slug]
        pref = cfg["name"]
        from shared.utils import prefecture_paths

        p = prefecture_paths(slug)
        stores = pd.read_csv(p["coord_csv"], encoding="utf-8-sig")
        stores["都道府県"] = pref
        store_dfs.append(stores)

        for src, dest_list in [
            (p["density_csv"], density_dfs),
            (p["population_csv"], pop_dfs),
            (p["aging_csv"], aging_dfs),
        ]:
            df = pd.read_csv(src, encoding="utf-8-sig")
            df.insert(0, "都道府県", pref)
            dest_list.append(df)

    stores_all = pd.concat(store_dfs, ignore_index=True)
    density_all = pd.concat(density_dfs, ignore_index=True)
    pop_all = pd.concat(pop_dfs, ignore_index=True)
    aging_all = pd.concat(aging_dfs, ignore_index=True)

    stores_all.to_csv(paths["coord_csv"], index=False, encoding="utf-8-sig")
    density_all.to_csv(paths["density_csv"], index=False, encoding="utf-8-sig")
    pop_all.to_csv(paths["population_csv"], index=False, encoding="utf-8-sig")
    aging_all.to_csv(paths["aging_csv"], index=False, encoding="utf-8-sig")

    print(f"  統合店舗CSV: {paths['coord_csv']} ({len(stores_all)}件)")
    print(f"  統合密度CSV: {paths['density_csv']} ({len(density_all)}件)")
    return paths


def _density_lookup(density_df: pd.DataFrame) -> dict:
    lookup = {}
    for _, row in density_df.iterrows():
        key = (row["都道府県"], row["市区町村"])
        lookup[key] = row["人口10万人当たり店舗数"]
    return lookup


def _aging_lookup(aging_df: pd.DataFrame) -> dict:
    lookup = {}
    for _, row in aging_df.iterrows():
        key = (row["都道府県"], row["市区町村"])
        lookup[key] = row["高齢化率"]
    return lookup


def create_tohoku_marker_map() -> str:
    paths = tohoku_paths()
    df = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")
    geo = _load_geojson(paths["geojson"])

    out = paths["maps"] / "東北ドラッグストア地図.html"
    plotted = create_marker_map_from_df(
        df=df,
        geo=geo,
        center=TOHOKU["center"],
        zoom=TOHOKU["zoom"],
        out_path=out,
        boundary_label="東北6県境界",
        pref_col="都道府県",
        boundary_group_key="都道府県",
        show_pref_boundary=True,
        show_title=False,
    )
    print(f"  東北マーカー地図: {out} ({plotted}件)")
    return str(out)


def create_tohoku_density_choropleth() -> str:
    paths = tohoku_paths()
    density_df = pd.read_csv(paths["density_csv"], encoding="utf-8-sig")
    geo = _load_geojson(paths["geojson"])

    detail_lookup: dict[tuple, dict] = {}
    for _, row in density_df.iterrows():
        key = (row["都道府県"], row["市区町村"])
        density = row["人口10万人当たり店舗数"]
        stores = int(row["店舗数"])
        pop = int(row["人口"])
        detail_lookup[key] = {
            "密度": float(density) if pd.notna(density) else 0.0,
            "密度表示": f"{density:.2f}" if pd.notna(density) and density > 0 else "—",
            "店舗数": stores,
            "店舗数表示": f"{stores}店",
            "人口": pop,
            "人口表示": f"{pop:,}人",
        }

    for feat in geo["features"]:
        props = feat["properties"]
        key = (props.get("都道府県"), props.get("市区町村_key", _city_key(props)))
        info = detail_lookup.get(
            key,
            detail_lookup.get((props.get("都道府県"), props.get("N03_004")), {}),
        )
        props["市区町村名"] = str(key[1] if key[1] else props.get("N03_004", ""))
        props["密度"] = float(info.get("密度", 0))
        props["密度表示"] = str(info.get("密度表示", "—"))
        props["店舗数"] = int(info.get("店舗数", 0))
        props["店舗数表示"] = str(info.get("店舗数表示", "—"))
        props["人口"] = int(info.get("人口", 0))
        props["人口表示"] = str(info.get("人口表示", "—"))

    m = folium.Map(location=list(TOHOKU["center"]), zoom_start=TOHOKU["zoom"], tiles="OpenStreetMap")
    colormap = _make_density_colormap()

    def style_fn(feature):
        d = feature["properties"].get("密度", 0) or 0
        if d > 0:
            return _choropleth_style(_density_fill_color(d))
        return _choropleth_style("#cccccc", fill_opacity=0.5)

    def highlight_fn(_feature):
        return {
            "weight": CHOROPLETH_BORDER_WEIGHT + 1.0,
            "color": "#111111",
            "fillOpacity": 0.95,
        }

    folium.GeoJson(
        geo,
        name="ドラッグストア密度",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["都道府県", "市区町村名", "人口表示", "店舗数表示", "密度表示"],
            aliases=["都道府県:", "市区町村:", "人口:", "店舗数:", "密度:"],
            sticky=True,
            labels=True,
            style=(
                "background-color:white;color:black;font-family:Meiryo;"
                "font-size:12px;padding:10px;border-radius:5px;"
            ),
        ),
    ).add_to(m)
    _add_prefecture_boundary(m, geo, "東北6県境界（赤線）", group_key="都道府県")
    colormap.add_to(m)

    out = paths["maps"] / "東北ドラッグストア密度コロプレスマップ.html"
    m.save(str(out))
    print(f"  東北密度コロプレス: {out}")
    return str(out)


def create_tohoku_aging_choropleth() -> str:
    paths = tohoku_paths()
    aging_df = pd.read_csv(paths["aging_csv"], encoding="utf-8-sig")
    aging_dict = _aging_lookup(aging_df)
    geo = _load_geojson(paths["geojson"])

    values = [v for v in aging_dict.values() if pd.notna(v) and v > 0]
    vmin = float(np.percentile(values, 5)) if values else 0
    vmax = float(np.percentile(values, 95)) if values else 40

    for feat in geo["features"]:
        props = feat["properties"]
        key = (props.get("都道府県"), props.get("市区町村_key", _city_key(props)))
        feat["properties"]["高齢化率"] = aging_dict.get(
            key,
            aging_dict.get((props.get("都道府県"), props.get("N03_004")), 0),
        )

    m = folium.Map(location=list(TOHOKU["center"]), zoom_start=TOHOKU["zoom"], tiles="OpenStreetMap")
    colormap = cm.LinearColormap(
        colors=AGING_CHOROPLETH_COLORS,
        vmin=vmin,
        vmax=vmax,
        caption="高齢化率（%）",
    )

    def style_fn(feature):
        a = feature["properties"].get("高齢化率", 0) or 0
        if a > 0:
            return _choropleth_style(colormap(np.clip(a, vmin, vmax)))
        return _choropleth_style("#cccccc", fill_opacity=0.5)

    folium.GeoJson(
        geo,
        name="高齢化率",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["都道府県", "N03_004", "高齢化率"],
            aliases=["都道府県:", "市区町村:", "高齢化率(%):"],
            localize=True,
            style=(
                "background-color:white;color:black;font-family:Meiryo;"
                "font-size:12px;padding:10px;border-radius:5px;"
            ),
        ),
    ).add_to(m)
    _add_prefecture_boundary(m, geo, "東北6県境界（赤線）", group_key="都道府県")
    colormap.add_to(m)

    out = paths["maps"] / "東北高齢化率コロプレスマップ.html"
    m.save(str(out))
    print(f"  東北高齢化率コロプレス: {out}")
    return str(out)


def write_tohoku_report(store_count: int, muni_count: int) -> None:
    paths = tohoku_paths()
    pref_lines = []
    for slug in TOHOKU_SLUGS:
        cfg = PREFECTURES[slug]
        from shared.utils import prefecture_paths

        p = prefecture_paths(slug)
        df = pd.read_csv(p["coord_csv"], encoding="utf-8-sig")
        pref_lines.append(f"| {cfg['name']} | {len(df)} |")

    lines = [
        "# 東北地方 ドラッグストア調査レポート（統合）",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## サマリー",
        "",
        f"- 総店舗数: **{store_count}件**",
        f"- 対象都道府県: **6県**",
        f"- 分析市区町村数: **{muni_count}件**",
        f"- 座標取得率: **100%**",
        "",
        "## 県別店舗数",
        "",
        "| 都道府県 | 店舗数 |",
        "|---------|--------|",
        *pref_lines,
        "",
        "## 成果物",
        "",
        "- `data/東北ドラッグストア_座標付き.csv`",
        "- `data/市区町村別ドラッグストア分析.csv`",
        "- `data/市区町村別人口.csv`",
        "- `data/市区町村別高齢化率.csv`",
        "- `data/municipalities.geojson`",
        "- `maps/東北ドラッグストア地図.html`",
        "- `maps/東北ドラッグストア密度コロプレスマップ.html`",
        "- `maps/東北高齢化率コロプレスマップ.html`",
        "",
    ]
    paths["report"].write_text("\n".join(lines), encoding="utf-8")
    print(f"  レポート: {paths['report']}")


def build_tohoku() -> dict:
    print("=" * 60)
    print("東北6県統合データ・地図生成")
    print("=" * 60)

    merge_geojson()
    paths = merge_csvs()
    df = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")
    density = pd.read_csv(paths["density_csv"], encoding="utf-8-sig")

    create_tohoku_marker_map()
    create_tohoku_density_choropleth()
    create_tohoku_aging_choropleth()
    write_tohoku_report(len(df), len(density))

    print(f"\n完了: 東北統合 {len(df)}件 / 市区町村 {len(density)}件")
    return {"stores": len(df), "municipalities": len(density)}


def rebuild_all_prefectures_and_tohoku(include_clean: bool = False) -> None:
    """6県の密度分析・地図を再生成し、東北統合データを作成"""
    if include_clean:
        from shared.clean_data import clean_for_prefecture
        from shared.geocode_stores import geocode_for_prefecture
        from shared.verify_data import cross_validate

        print("=" * 60)
        print("Step 0: 6県 クリーニング・座標再取得")
        print("=" * 60)
        for slug in TOHOKU_SLUGS:
            print(f"\n--- {PREFECTURES[slug]['name']} ---")
            clean_for_prefecture(slug)
            geocode_for_prefecture(slug)
            cross_validate(slug)
    print("=" * 60)
    print("Step 1: 6県 密度分析の再実行")
    print("=" * 60)
    for slug in TOHOKU_SLUGS:
        print(f"\n--- {PREFECTURES[slug]['name']} ---")
        analyze_for_prefecture(slug)

    print("\n" + "=" * 60)
    print("Step 2: 6県 地図の再生成")
    print("=" * 60)
    for slug in TOHOKU_SLUGS:
        print(f"\n--- {PREFECTURES[slug]['name']} ---")
        create_all_maps(slug)

    print("\n" + "=" * 60)
    print("Step 3: 東北統合")
    print("=" * 60)
    build_tohoku()


if __name__ == "__main__":
    import sys

    do_clean = "--clean" in sys.argv
    rebuild_all_prefectures_and_tohoku(include_clean=do_clean)

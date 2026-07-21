"""Folium 地図生成（マーカー・密度コロプレス・高齢化率コロプレス）"""

import json

import branca.colormap as cm
import folium
import numpy as np
import pandas as pd

from shared.config import CHAIN_COLORS, PREFECTURES
from shared.utils import ensure_dirs


def _load_geojson(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _city_key(props) -> str:
    prefix = props.get("N03_003") or ""
    name = props.get("N03_004") or ""
    if prefix and name:
        return f"{prefix}{name}"
    return name or prefix


def create_marker_map(slug: str) -> str:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    pref_name = cfg["name"]

    df = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")
    geo = _load_geojson(paths["geojson"])

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
    folium.GeoJson(
        geo,
        name=f"{pref_name}境界",
        style_function=lambda x: {
            "fillColor": "#ffffff",
            "color": "#666666",
            "weight": 2,
            "fillOpacity": 0.03,
        },
    ).add_to(m)

    groups = {}
    for chain in df["company"].unique():
        groups[chain] = folium.FeatureGroup(name=chain, show=True)

    plotted = 0
    for _, row in df.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            continue
        chain = row["company"]
        color = CHAIN_COLORS.get(chain, "#808080")
        popup = f"<b>{chain}</b><br>{row['store_name']}<br>{row['address']}"
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            popup=folium.Popup(popup, max_width=280),
            tooltip=chain,
            color="#000",
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            weight=1,
        ).add_to(groups.get(chain, m))
        plotted += 1

    for fg in groups.values():
        fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    out = paths["maps"] / f"{pref_name}ドラッグストア地図.html"
    m.save(str(out))
    print(f"  マーカー地図: {out} ({plotted}件)")
    return str(out)


def create_density_choropleth(slug: str) -> str:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    pref_name = cfg["name"]

    df = pd.read_csv(paths["density_csv"], encoding="utf-8-sig")
    df = df.dropna(subset=["市区町村", "人口10万人当たり店舗数"])
    density_dict = dict(zip(df["市区町村"], df["人口10万人当たり店舗数"]))

    geo = _load_geojson(paths["geojson"])
    values = list(density_dict.values())
    vmin = np.percentile(values, 5) if values else 0
    vmax = np.percentile(values, 95) if values else 1

    for feat in geo["features"]:
        key = _city_key(feat["properties"])
        feat["properties"]["密度"] = density_dict.get(key, density_dict.get(feat["properties"].get("N03_004"), 0))

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
    colormap = cm.LinearColormap(
        colors=["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
        vmin=vmin,
        vmax=vmax,
        caption="人口10万人当たり店舗数",
    )

    def style_fn(feature):
        d = feature["properties"].get("密度", 0) or 0
        if d > 0:
            return {
                "fillColor": colormap(np.clip(d, vmin, vmax)),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.75,
            }
        return {"fillColor": "#cccccc", "color": "black", "weight": 0.5, "fillOpacity": 0.5}

    folium.GeoJson(
        geo,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["N03_004", "密度"],
            aliases=["市区町村:", "10万人当たり:"],
        ),
    ).add_to(m)
    colormap.add_to(m)

    out = paths["maps"] / f"{pref_name}ドラッグストア密度コロプレスマップ.html"
    m.save(str(out))
    print(f"  密度コロプレス: {out}")
    return str(out)


def create_aging_choropleth(slug: str) -> str:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    pref_name = cfg["name"]

    aging = pd.read_csv(paths["aging_csv"], encoding="utf-8-sig")
    aging_dict = dict(zip(aging["市区町村"], aging["高齢化率"]))

    geo = _load_geojson(paths["geojson"])
    values = [v for v in aging_dict.values() if pd.notna(v)]
    vmin = np.percentile(values, 5) if values else 0
    vmax = np.percentile(values, 95) if values else 40

    for feat in geo["features"]:
        key = _city_key(feat["properties"])
        feat["properties"]["高齢化率"] = aging_dict.get(key, aging_dict.get(feat["properties"].get("N03_004"), 0))

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
    colormap = cm.LinearColormap(
        colors=["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
        vmin=vmin,
        vmax=vmax,
        caption="高齢化率（%）",
    )

    def style_fn(feature):
        a = feature["properties"].get("高齢化率", 0) or 0
        if a > 0:
            return {
                "fillColor": colormap(np.clip(a, vmin, vmax)),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.75,
            }
        return {"fillColor": "#cccccc", "color": "black", "weight": 0.5, "fillOpacity": 0.5}

    folium.GeoJson(
        geo,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["N03_004", "高齢化率"],
            aliases=["市区町村:", "高齢化率(%):"],
        ),
    ).add_to(m)
    colormap.add_to(m)

    out = paths["maps"] / f"{pref_name}高齢化率コロプレスマップ.html"
    m.save(str(out))
    print(f"  高齢化率コロプレス: {out}")
    return str(out)


def create_all_maps(slug: str) -> dict:
    return {
        "marker": create_marker_map(slug),
        "density": create_density_choropleth(slug),
        "aging": create_aging_choropleth(slug),
    }


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    create_all_maps(slug)

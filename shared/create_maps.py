"""Folium 地図生成（マーカー・密度コロプレス・高齢化率コロプレス）"""

import json
from pathlib import Path

import branca.colormap as cm
import folium
import numpy as np
import pandas as pd

from shared.config import (
    CHAIN_CATEGORIES,
    CHAIN_COLORS,
    MUNI_BORDER_COLOR,
    MUNI_BORDER_WEIGHT,
    PREF_BOUNDARY_COLOR,
    PREF_BOUNDARY_WEIGHT,
    PREFECTURES,
)
from shared.utils import ensure_dirs


def _load_geojson(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _city_key(props) -> str:
    prefix = props.get("N03_003") or ""
    name = props.get("N03_004") or ""
    ward = props.get("N03_005") or ""
    if ward and name:
        return f"{name}{ward}"
    if prefix and name:
        return f"{prefix}{name}"
    return name or prefix


def _dissolve_outlines(geo: dict, group_key: str | None = None) -> dict:
    """市区町村ポリゴンを統合し、県境界などの外周輪郭のみを抽出"""
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    groups: dict[str, list] = {}
    for feat in geo["features"]:
        key = feat["properties"].get(group_key, "_all") if group_key else "_all"
        groups.setdefault(key, []).append(shape(feat["geometry"]))

    features = []
    for key, shapes in groups.items():
        if not shapes:
            continue
        merged = unary_union(shapes)
        props = {"name": key} if group_key else {"name": "boundary"}
        features.append({"type": "Feature", "properties": props, "geometry": mapping(merged)})

    return {"type": "FeatureCollection", "features": features}


def _pref_boundary_style() -> dict:
    return {
        "fillColor": "#ffffff",
        "color": PREF_BOUNDARY_COLOR,
        "weight": PREF_BOUNDARY_WEIGHT,
        "fillOpacity": 0.0,
    }


def _add_prefecture_boundary(
    map_obj,
    geo: dict,
    label: str,
    group_key: str | None = None,
) -> folium.GeoJson:
    """県境界を赤線で描画（コロプレスの上に重ねて表示）"""
    outline = _dissolve_outlines(geo, group_key=group_key)
    layer = folium.GeoJson(
        outline,
        name=label,
        style_function=lambda x: _pref_boundary_style(),
        interactive=False,
    )
    layer.add_to(map_obj)
    return layer


# 密度コロプレス用グラデーション（薄黄 → 橙 → 赤 → 深紅）
DENSITY_GRADIENT_COLORS = [
    "#ffffe5",
    "#fff7bc",
    "#fee391",
    "#fec44f",
    "#fe9929",
    "#ec7014",
    "#cc4c02",
    "#993404",
    "#662506",
]


def _density_colormap(vmin: float, vmax: float):
    return cm.LinearColormap(colors=DENSITY_GRADIENT_COLORS, vmin=vmin, vmax=vmax)


def _add_continuous_gradient_legend(
    map_obj, colormap, title: str, unit: str, steps: int = 12
) -> None:
    """連続グラデーション凡例"""
    vmin, vmax = colormap.vmin, colormap.vmax
    values = np.linspace(vmin, vmax, steps)
    swatches = "".join(
        f'<span style="flex:1;background:{colormap(v)};"></span>' for v in values
    )
    html = f"""
    <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
         background:white;padding:10px 14px;border-radius:8px;
         border:2px solid #bbb;font-family:'Meiryo','Yu Gothic',sans-serif;
         font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,0.25);min-width:200px;">
      <div style="font-weight:bold;font-size:13px;margin-bottom:6px;">{title}</div>
      <div style="display:flex;height:20px;border:1px solid #666;border-radius:2px;
           overflow:hidden;">{swatches}</div>
      <div style="display:flex;justify-content:space-between;margin-top:3px;
           font-size:11px;color:#555;">
        <span>{vmin:.1f}{unit}</span>
        <span>{vmax:.1f}{unit}</span>
      </div>
      <div style="margin-top:6px;color:#888;font-size:11px;">灰色 = 店舗なし/データなし</div>
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(html))


def _chain_color(chain: str) -> str:
    return CHAIN_COLORS.get(chain, "#78909C")


def _chain_counts(df: pd.DataFrame) -> dict[str, int]:
    return df["company"].value_counts().to_dict()


def _add_chain_legend(map_obj, chain_counts: dict[str, int], title: str) -> None:
    """チェーン別カラー凡例（店舗数付き）を地図左下に追加"""
    categorized: dict[str, list[tuple[str, int]]] = {cat: [] for cat in CHAIN_CATEGORIES}
    categorized["その他のチェーン"] = []
    seen: set[str] = set()

    for cat, chains in CHAIN_CATEGORIES.items():
        for chain in chains:
            if chain in chain_counts:
                categorized[cat].append((chain, chain_counts[chain]))
                seen.add(chain)

    for chain, count in sorted(chain_counts.items(), key=lambda x: (-x[1], x[0])):
        if chain not in seen:
            categorized["その他のチェーン"].append((chain, count))

    sections = []
    for cat, items in categorized.items():
        if not items:
            continue
        rows = []
        for chain, count in sorted(items, key=lambda x: (-x[1], x[0])):
            color = _chain_color(chain)
            rows.append(
                f'<div style="display:flex;align-items:center;margin:2px 0;">'
                f'<span style="background:{color};width:12px;height:12px;'
                f'border-radius:50%;display:inline-block;margin-right:7px;'
                f'border:1px solid #555;flex-shrink:0;"></span>'
                f"<span>{chain} ({count}店)</span></div>"
            )
        sections.append(
            f'<div style="margin-top:6px;">'
            f'<div style="font-weight:600;color:#444;margin-bottom:2px;">{cat}</div>'
            f'{"".join(rows)}</div>'
        )

    total = sum(chain_counts.values())
    html = f"""
    <div style="position:fixed;bottom:30px;left:10px;z-index:9999;
         background:white;padding:10px 14px;border-radius:8px;
         border:2px solid #bbb;max-height:380px;overflow-y:auto;
         font-family:'Meiryo','Yu Gothic',sans-serif;font-size:12px;
         line-height:1.5;box-shadow:0 2px 8px rgba(0,0,0,0.25);min-width:210px;">
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;
           border-bottom:1px solid #ddd;padding-bottom:4px;">
        {title} (全{total}店)
      </div>
      {''.join(sections)}
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(html))


def create_marker_map_from_df(
    df: pd.DataFrame,
    geo: dict,
    center: tuple,
    zoom: int,
    out_path: Path,
    boundary_label: str,
    legend_title: str,
    pref_col: str | None = None,
    boundary_group_key: str | None = None,
) -> int:
    counts = _chain_counts(df)
    chains_sorted = sorted(counts.keys(), key=lambda c: (-counts[c], c))

    m = folium.Map(location=list(center), zoom_start=zoom, tiles="OpenStreetMap")
    folium.GeoJson(
        geo,
        name=boundary_label,
        style_function=lambda x: {
            "fillColor": "#ffffff",
            "color": MUNI_BORDER_COLOR,
            "weight": MUNI_BORDER_WEIGHT,
            "fillOpacity": 0.03,
        },
    ).add_to(m)
    _add_prefecture_boundary(m, geo, f"{boundary_label}（赤線）", group_key=boundary_group_key)

    groups: dict[str, folium.FeatureGroup] = {}
    for chain in chains_sorted:
        label = f"● {_chain_color(chain)} {chain} ({counts[chain]})"
        # LayerControl には色が出ないので名前先頭に記号のみ
        groups[chain] = folium.FeatureGroup(name=f"{chain} ({counts[chain]}店)", show=True)

    plotted = 0
    for _, row in df.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            continue
        chain = row["company"]
        color = _chain_color(chain)
        popup_parts = [f"<b>{chain}</b>", str(row["store_name"]), str(row["address"])]
        if pref_col and pref_col in row and pd.notna(row[pref_col]):
            popup_parts.append(f"（{row[pref_col]}）")
        popup = "<br>".join(popup_parts)
        tooltip = f"{chain} — {row['store_name']}"
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=6,
            popup=folium.Popup(popup, max_width=300),
            tooltip=tooltip,
            color="#333333",
            fill=True,
            fillColor=color,
            fillOpacity=0.85,
            weight=1.5,
        ).add_to(groups[chain])
        plotted += 1

    for chain in chains_sorted:
        groups[chain].add_to(m)

    _add_chain_legend(m, counts, legend_title)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_path))
    return plotted


def create_marker_map(slug: str) -> str:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    pref_name = cfg["name"]

    df = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")
    geo = _load_geojson(paths["geojson"])

    out = paths["maps"] / f"{pref_name}ドラッグストア地図.html"
    plotted = create_marker_map_from_df(
        df=df,
        geo=geo,
        center=cfg["center"],
        zoom=cfg["zoom"],
        out_path=out,
        boundary_label=f"{pref_name}境界",
        legend_title=f"{pref_name} チェーン別",
    )
    print(f"  マーカー地図: {out} ({plotted}件)")
    return str(out)


def _add_step_legend(map_obj, colormap, title: str, unit: str) -> None:
    """コロプレス用の段階別カラー凡例を追加"""
    vmin, vmax = colormap.vmin, colormap.vmax
    steps = 5
    values = np.linspace(vmin, vmax, steps)
    rows = []
    for i, v in enumerate(values):
        color = colormap(v)
        label = f"{v:.1f}{unit}"
        if i < steps - 1:
            next_v = values[i + 1]
            label = f"{v:.1f} 〜 {next_v:.1f}{unit}"
        rows.append(
            f'<div style="display:flex;align-items:center;margin:2px 0;">'
            f'<span style="background:{color};width:24px;height:14px;'
            f'display:inline-block;margin-right:6px;border:1px solid #666;"></span>'
            f"<span>{label}</span></div>"
        )

    html = f"""
    <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
         background:white;padding:10px 14px;border-radius:8px;
         border:2px solid #bbb;font-family:'Meiryo','Yu Gothic',sans-serif;
         font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,0.25);">
      <div style="font-weight:bold;font-size:13px;margin-bottom:6px;">{title}</div>
      {''.join(rows)}
      <div style="margin-top:6px;color:#888;font-size:11px;">灰色 = 店舗なし/データなし</div>
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(html))


def create_density_choropleth(slug: str) -> str:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    pref_name = cfg["name"]

    df = pd.read_csv(paths["density_csv"], encoding="utf-8-sig")
    df = df.dropna(subset=["市区町村", "人口10万人当たり店舗数"])
    density_dict = dict(zip(df["市区町村"], df["人口10万人当たり店舗数"]))

    geo = _load_geojson(paths["geojson"])
    values = [v for v in density_dict.values() if v > 0]
    vmin = float(np.percentile(values, 5)) if values else 0
    vmax = float(np.percentile(values, 95)) if values else 1

    for feat in geo["features"]:
        key = _city_key(feat["properties"])
        feat["properties"]["密度"] = density_dict.get(
            key, density_dict.get(feat["properties"].get("N03_004"), 0)
        )

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
    colormap = cm.LinearColormap(
        colors=["#ffffcc", "#ffe066", "#ffb347", "#ff6b35", "#c0392b"],
        vmin=vmin,
        vmax=vmax,
    )

    def style_fn(feature):
        d = feature["properties"].get("密度", 0) or 0
        if d > 0:
            return {
                "fillColor": colormap(np.clip(d, vmin, vmax)),
                "color": MUNI_BORDER_COLOR,
                "weight": MUNI_BORDER_WEIGHT,
                "fillOpacity": 0.78,
            }
        return {
            "fillColor": "#d9d9d9",
            "color": MUNI_BORDER_COLOR,
            "weight": MUNI_BORDER_WEIGHT,
            "fillOpacity": 0.5,
        }

    folium.GeoJson(
        geo,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["N03_004", "密度"],
            aliases=["市区町村:", "10万人あたり(店):"],
        ),
    ).add_to(m)
    _add_prefecture_boundary(m, geo, f"{pref_name}境界（赤線）")
    _add_step_legend(m, colormap, "ドラッグストア密度", " 店/10万人")

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
    vmin = float(np.percentile(values, 5)) if values else 0
    vmax = float(np.percentile(values, 95)) if values else 40

    for feat in geo["features"]:
        key = _city_key(feat["properties"])
        feat["properties"]["高齢化率"] = aging_dict.get(
            key, aging_dict.get(feat["properties"].get("N03_004"), 0)
        )

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
    colormap = cm.LinearColormap(
        colors=["#ffffcc", "#ffe066", "#ffb347", "#ff6b35", "#c0392b"],
        vmin=vmin,
        vmax=vmax,
    )

    def style_fn(feature):
        a = feature["properties"].get("高齢化率", 0) or 0
        if a > 0:
            return {
                "fillColor": colormap(np.clip(a, vmin, vmax)),
                "color": MUNI_BORDER_COLOR,
                "weight": MUNI_BORDER_WEIGHT,
                "fillOpacity": 0.78,
            }
        return {
            "fillColor": "#d9d9d9",
            "color": MUNI_BORDER_COLOR,
            "weight": MUNI_BORDER_WEIGHT,
            "fillOpacity": 0.5,
        }

    folium.GeoJson(
        geo,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["N03_004", "高齢化率"],
            aliases=["市区町村:", "高齢化率(%):"],
        ),
    ).add_to(m)
    _add_prefecture_boundary(m, geo, f"{pref_name}境界（赤線）")
    _add_step_legend(m, colormap, "高齢化率", "%")

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

"""Folium 地図生成（マーカー・密度コロプレス・高齢化率コロプレス）"""

import json
from pathlib import Path

import branca.colormap as cm
import folium
import numpy as np
import pandas as pd

from shared.config import (
    AGING_CHOROPLETH_COLORS,
    CHAIN_COLORS,
    CHOROPLETH_BORDER_COLOR,
    CHOROPLETH_BORDER_WEIGHT,
    DENSITY_CHOROPLETH_COLORS,
    DENSITY_CHOROPLETH_MID,
    DENSITY_CHOROPLETH_MID_POS,
    DENSITY_CHOROPLETH_UPPER_GAMMA,
    DENSITY_CHOROPLETH_VMAX,
    DENSITY_CHOROPLETH_VMIN,
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


def _muni_boundary_style() -> dict:
    return {
        "fillColor": "#ffffff",
        "color": MUNI_BORDER_COLOR,
        "weight": MUNI_BORDER_WEIGHT,
        "fillOpacity": 0.03,
    }


def _choropleth_style(fill_color: str, fill_opacity: float = 0.75) -> dict:
    return {
        "fillColor": fill_color,
        "color": CHOROPLETH_BORDER_COLOR,
        "weight": CHOROPLETH_BORDER_WEIGHT,
        "fillOpacity": fill_opacity,
    }


def _density_normalized(density: float) -> float:
    """密度値を0〜1に変換。平均付近は薄色域に留め、高密度のみ急峻に濃色化"""
    d = float(np.clip(density, DENSITY_CHOROPLETH_VMIN, DENSITY_CHOROPLETH_VMAX))
    mid = DENSITY_CHOROPLETH_MID
    mid_pos = DENSITY_CHOROPLETH_MID_POS
    if d <= mid:
        return (d / mid) * mid_pos if mid > 0 else 0.0
    t = (d - mid) / (DENSITY_CHOROPLETH_VMAX - mid)
    t = t ** DENSITY_CHOROPLETH_UPPER_GAMMA
    return mid_pos + t * (1.0 - mid_pos)


def _density_base_cmap() -> cm.LinearColormap:
    return cm.LinearColormap(DENSITY_CHOROPLETH_COLORS, vmin=0, vmax=1)


def _make_density_colormap() -> cm.LinearColormap:
    """凡例用。分段正規化を101点サンプリングして線形補間"""
    base = _density_base_cmap()
    samples = [
        base(_density_normalized(v))[:7]
        for v in np.linspace(DENSITY_CHOROPLETH_VMIN, DENSITY_CHOROPLETH_VMAX, 101)
    ]
    return cm.LinearColormap(
        samples,
        vmin=DENSITY_CHOROPLETH_VMIN,
        vmax=DENSITY_CHOROPLETH_VMAX,
        caption="人口10万人当たりドラッグストア数",
    )


def _density_fill_color(density: float) -> str:
    if density <= 0:
        return "#cccccc"
    color = _density_base_cmap()(_density_normalized(density))
    return color[:7]


def _add_prefecture_boundary(
    map_obj,
    geo: dict,
    label: str,
    group_key: str | None = None,
) -> folium.GeoJson:
    """県境界を赤線で描画"""
    outline = _dissolve_outlines(geo, group_key=group_key)
    layer = folium.GeoJson(
        outline,
        name=label,
        style_function=lambda x: _pref_boundary_style(),
        interactive=False,
    )
    layer.add_to(map_obj)
    return layer


def _chain_color(chain: str) -> str:
    return CHAIN_COLORS.get(chain, "#808080")


def _display_chain(chain: str) -> str:
    """凡例・マーカー表示用にチェーン名を正規化"""
    return "その他" if chain == "不明" else chain


def _merge_other_chains(counts: dict[str, int]) -> dict[str, int]:
    """「不明」を「その他」に統合したチェーン別店舗数"""
    merged = dict(counts)
    unknown = merged.pop("不明", 0)
    if unknown:
        merged["その他"] = merged.get("その他", 0) + unknown
    return merged


def _chain_counts(df: pd.DataFrame) -> dict[str, int]:
    raw = df["company"].value_counts().to_dict()
    return _merge_other_chains(raw)


def _add_map_title(map_obj, title: str, subtitle: str) -> None:
    html = f"""
    <div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);
         width:520px;background-color:white;z-index:9999;font-size:18px;
         border:3px solid #333;border-radius:10px;padding:15px;
         box-shadow:0 4px 12px rgba(0,0,0,0.4);font-family:Meiryo,sans-serif;">
      <h2 style="margin:0;text-align:center;color:#333;">{title}</h2>
      <p style="margin:8px 0 0 0;font-size:14px;text-align:center;color:#666;">{subtitle}</p>
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(html))


def _legend_chain_order(chain_counts: dict[str, int]) -> list[tuple[str, int]]:
    """愛知県地図と同じ CHAIN_COLORS 定義順を優先し、未定義チェーンは店舗数順"""
    ordered: list[tuple[str, int]] = []
    seen: set[str] = set()
    for chain in CHAIN_COLORS:
        count = chain_counts.get(chain, 0)
        if count > 0:
            ordered.append((chain, count))
            seen.add(chain)
    for chain, count in sorted(chain_counts.items(), key=lambda x: (-x[1], x[0])):
        if chain not in seen and count > 0:
            ordered.append((chain, count))
    return ordered


def _add_aichi_style_legend(map_obj, chain_counts: dict[str, int], plotted: int) -> None:
    """愛知県プロジェクト準拠のチェーン別凡例（右下）"""
    rows = []
    ordered = _legend_chain_order(chain_counts)
    for chain, count in ordered:
        color = _chain_color(chain)
        rows.append(
            f"""
<p style="margin:6px 0; display: flex; align-items: center;">
    <span style="background-color:{color}; width:16px; height:16px; display:inline-block;
                 border-radius:50%; margin-right:8px; border: 1px solid #333;"></span>
    <span style="font-size:12px;">{chain} <small style="color:#666;">({count})</small></span>
</p>"""
        )

    chain_count = len(ordered)
    html = f"""
<div style="position: fixed;
            bottom: 50px; right: 50px; width: 240px; height: auto;
            background-color: white; z-index:9999; font-size:13px;
            border:2px solid #333; border-radius: 8px; padding: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: Meiryo, sans-serif;">
<h4 style="margin:0 0 12px 0; text-align:center; color: #333; border-bottom: 2px solid #ddd; padding-bottom: 8px;">チェーン別色分け</h4>
{''.join(rows)}
<hr style="margin:10px 0; border: none; border-top: 1px solid #ddd;">
<p style="margin:5px 0; font-size:11px; text-align:center; color:#666;">
    総店舗数: {plotted}件<br>
    チェーン数: {chain_count}社
</p>
</div>
"""
    map_obj.get_root().html.add_child(folium.Element(html))


def _styled_popup(chain: str, store_name: str, address: str, extra: str = "") -> str:
    color = _chain_color(chain)
    extra_html = f"<p style='margin:4px 0;font-size:11px;color:#888;'>{extra}</p>" if extra else ""
    return f"""
    <div style='width:250px;font-family:Meiryo,"MS Gothic",sans-serif;'>
      <h4 style='margin:0 0 8px 0;color:{color};border-bottom:2px solid {color};padding-bottom:4px;'>{chain}</h4>
      <p style='margin:4px 0;font-weight:bold;font-size:13px;'>{store_name}</p>
      <p style='margin:4px 0;font-size:11px;color:#666;'>{address}</p>
      {extra_html}
    </div>
    """


def create_marker_map_from_df(
    df: pd.DataFrame,
    geo: dict,
    center: tuple,
    zoom: int,
    out_path: Path,
    boundary_label: str,
    map_title: str = "",
    map_subtitle: str = "",
    pref_col: str | None = None,
    boundary_group_key: str | None = None,
    show_pref_boundary: bool = False,
    show_title: bool = True,
) -> int:
    counts = _chain_counts(df)
    chains_sorted = sorted(counts.keys(), key=lambda c: (-counts[c], c))
    total = len(df)

    m = folium.Map(location=list(center), zoom_start=zoom, tiles="OpenStreetMap")
    folium.GeoJson(
        geo,
        name=boundary_label,
        style_function=lambda x: _muni_boundary_style(),
    ).add_to(m)
    if show_pref_boundary and boundary_group_key:
        _add_prefecture_boundary(m, geo, f"{boundary_label}（赤線）", group_key=boundary_group_key)

    groups: dict[str, folium.FeatureGroup] = {}
    for chain in chains_sorted:
        groups[chain] = folium.FeatureGroup(name=f"{chain}", show=True)

    plotted = 0
    for _, row in df.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            continue
        chain = _display_chain(str(row["company"]))
        color = _chain_color(chain)
        extra = ""
        if pref_col and pref_col in row and pd.notna(row[pref_col]):
            extra = str(row[pref_col])
        popup = _styled_popup(chain, str(row["store_name"]), str(row["address"]), extra)
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            popup=folium.Popup(popup, max_width=280),
            tooltip=f"{chain}",
            color="#000",
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            weight=1,
        ).add_to(groups[chain])
        plotted += 1

    for chain in chains_sorted:
        groups[chain].add_to(m)

    if show_title and map_title:
        _add_map_title(m, map_title, map_subtitle)
    _add_aichi_style_legend(m, counts, plotted)
    folium.LayerControl(collapsed=False, position="topleft").add_to(m)

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
        map_title=f"{pref_name}内ドラッグストア分布地図",
        map_subtitle=f"チェーン別色分け表示 - 全{len(df)}店舗",
    )
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

    for feat in geo["features"]:
        key = _city_key(feat["properties"])
        feat["properties"]["密度"] = density_dict.get(
            key, density_dict.get(feat["properties"].get("N03_004"), 0)
        )

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
    colormap = _make_density_colormap()

    def style_fn(feature):
        d = feature["properties"].get("密度", 0) or 0
        if d > 0:
            return _choropleth_style(_density_fill_color(d))
        return _choropleth_style("#cccccc", fill_opacity=0.5)

    folium.GeoJson(
        geo,
        name="ドラッグストア密度",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["N03_004", "密度"],
            aliases=["市区町村:", "10万人当たり店舗数:"],
            localize=True,
            style=(
                "background-color:white;color:black;font-family:Meiryo;"
                "font-size:12px;padding:10px;border-radius:5px;"
            ),
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
    values = [v for v in aging_dict.values() if pd.notna(v) and v > 0]
    vmin = float(np.percentile(values, 5)) if values else 0
    vmax = float(np.percentile(values, 95)) if values else 40

    for feat in geo["features"]:
        key = _city_key(feat["properties"])
        feat["properties"]["高齢化率"] = aging_dict.get(
            key, aging_dict.get(feat["properties"].get("N03_004"), 0)
        )

    m = folium.Map(location=list(cfg["center"]), zoom_start=cfg["zoom"], tiles="OpenStreetMap")
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
            fields=["N03_004", "高齢化率"],
            aliases=["市区町村:", "高齢化率(%):"],
            localize=True,
            style=(
                "background-color:white;color:black;font-family:Meiryo;"
                "font-size:12px;padding:10px;border-radius:5px;"
            ),
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

"""密度コロプレスマップを fitBounds 付き HTML と高解像度 PNG で出力"""

from __future__ import annotations

import argparse
import json
import math
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import branca.colormap as cm
import folium
import pandas as pd
from branca.element import MacroElement
from jinja2 import Template
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from shared.config import (
    EXPORTS_DIR,
    HOKKAIDO_TOHOKU,
    HOKKAIDO_TOHOKU_SLUGS,
    PREFECTURES,
    TOHOKU,
    TOHOKU_SLUGS,
)
from shared.create_maps import (
    _city_key,
    _density_fill_color,
    _load_geojson,
    _make_density_colormap,
    optimize_geojson,
    save_geojson,
)
from shared.geo_utils import exclude_northern_territories
from shared.utils import prefecture_paths

EXPORT_GEOJSON_TOLERANCE = 0.0002
EXPORT_GEOJSON_PRECISION = 5
EXPORT_BASE_HEIGHT = 3600
EXPORT_DEVICE_SCALE = 3
EXPORT_FIT_PADDING = (16, 16)
EXPORT_LAT_MIN = 37.0

_CHOROPLETH_STYLE_JS = """function(feature) {
    var p = feature.properties;
    return {
        fillColor: p._fill || "#cccccc",
        color: "#000000",
        weight: 0.5,
        fillOpacity: p._fillOpacity != null ? p._fillOpacity : 0.5
    };
}"""


class ExportGeoJson(MacroElement):
    """GeoJSON 読み込み後に fitBounds し、タイル描画完了を通知"""

    _template = Template(
        """
    {% macro script(this, kwargs) %}
    (function() {
        var map = {{ this._parent.get_name() }};
        var padding = {{ this.padding }};

        function signalReady() {
            window.__MAP_READY__ = true;
        }

        fetch('{{ this.url }}')
            .then(function(response) { return response.json(); })
            .then(function(data) {
                var layer = L.geoJSON(data, {
                    style: {{ this.style_js }},
                    interactive: false
                }).addTo(map);
                map.fitBounds(layer.getBounds(), {padding: padding});
                map.once('moveend', function() {
                    setTimeout(signalReady, 10000);
                });
            })
            .catch(function(err) {
                console.error('GeoJSON load failed:', err);
                window.__MAP_ERROR__ = String(err);
            });
    })();
    {% endmacro %}
    """
    )

    def __init__(self, url: str, style_js: str, padding: list[int]):
        super().__init__()
        self.url = url
        self.style_js = style_js
        self.padding = padding


def _region_specs() -> dict[str, dict]:
    return {
        "hokkaido_tohoku": {
            "label": "北海道東北",
            "slugs": HOKKAIDO_TOHOKU_SLUGS,
            "center": HOKKAIDO_TOHOKU["center"],
            "zoom": HOKKAIDO_TOHOKU["zoom"],
        },
        "hokkaido": {
            "label": "北海道",
            "slugs": ["09_北海道"],
            "center": PREFECTURES["09_北海道"]["center"],
            "zoom": PREFECTURES["09_北海道"]["zoom"],
        },
        "tohoku": {
            "label": "東北",
            "slugs": TOHOKU_SLUGS,
            "center": TOHOKU["center"],
            "zoom": TOHOKU["zoom"],
        },
    }


def _dissolve_municipalities(geo: dict) -> dict:
    """同一市区町村のポリゴン断片を統合し、描画・トリミングを安定させる"""
    groups: dict[str, list] = {}
    props_by_key: dict[str, dict] = {}

    for feat in geo["features"]:
        props = feat["properties"]
        key = str(
            props.get("N03_007")
            or props.get("市区町村_key")
            or _city_key(props)
            or id(feat)
        )
        groups.setdefault(key, []).append(shape(feat["geometry"]))
        props_by_key.setdefault(key, props)

    features = []
    for key, geoms in groups.items():
        merged = unary_union(geoms)
        if merged.is_empty:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": dict(props_by_key[key]),
                "geometry": mapping(merged),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _clip_for_export(geo: dict) -> dict:
    """離島など極端な外れ値を除き、海の余白を減らす"""
    geo = exclude_northern_territories(geo)
    kept = []
    for feat in geo["features"]:
        centroid = shape(feat["geometry"]).centroid
        if centroid.y < EXPORT_LAT_MIN:
            continue
        kept.append(feat)
    return {"type": "FeatureCollection", "features": kept}


def _merge_geojson(slugs: list[str]) -> dict:
    features = []
    for slug in slugs:
        cfg = PREFECTURES[slug]
        geo = _load_geojson(prefecture_paths(slug)["geojson"], slug)
        pref = cfg["name"]
        for feat in geo["features"]:
            props = dict(feat["properties"])
            props["都道府県"] = pref
            props["市区町村_key"] = _city_key(props)
            features.append(
                {"type": "Feature", "properties": props, "geometry": feat["geometry"]}
            )
    return {"type": "FeatureCollection", "features": features}


def _load_density_rows(slugs: list[str]) -> pd.DataFrame:
    frames = []
    for slug in slugs:
        cfg = PREFECTURES[slug]
        pref = cfg["name"]
        df = pd.read_csv(prefecture_paths(slug)["density_csv"], encoding="utf-8-sig")
        if "都道府県" not in df.columns:
            df.insert(0, "都道府県", pref)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _apply_density(geo: dict, density_df: pd.DataFrame) -> dict:
    detail_lookup: dict[tuple, dict] = {}
    for _, row in density_df.iterrows():
        key = (row["都道府県"], row["市区町村"])
        density = row["人口10万人当たり店舗数"]
        detail_lookup[key] = {
            "密度": float(density) if pd.notna(density) else 0.0,
            "密度表示": f"{density:.2f}" if pd.notna(density) and density > 0 else "—",
        }

    for feat in geo["features"]:
        props = feat["properties"]
        key = (props.get("都道府県"), props.get("市区町村_key", _city_key(props)))
        info = detail_lookup.get(
            key,
            detail_lookup.get((props.get("都道府県"), props.get("N03_004")), {}),
        )
        d = float(info.get("密度", 0))
        props["密度"] = d
        props["密度表示"] = str(info.get("密度表示", "—"))
        if d > 0:
            props["_fill"] = _density_fill_color(d)
            props["_fillOpacity"] = 0.75
        else:
            props["_fill"] = "#cccccc"
            props["_fillOpacity"] = 0.5
    return geo


def _bounds_sw_ne(geo: dict) -> tuple[list[float], list[float]]:
    geoms = [shape(feat["geometry"]) for feat in geo["features"]]
    minx, miny, maxx, maxy = unary_union(geoms).bounds
    return [miny, minx], [maxy, maxx]


def _viewport_size(sw: list[float], ne: list[float], base_height: int = EXPORT_BASE_HEIGHT) -> tuple[int, int]:
    lat_span = ne[0] - sw[0]
    lon_span = ne[1] - sw[1]
    mid_lat = (ne[0] + sw[0]) / 2
    lon_scale = max(math.cos(math.radians(mid_lat)), 0.2)
    aspect = lat_span / max(lon_span * lon_scale, 0.01)
    height = base_height
    width = int(round(height / aspect))
    width = max(width, 1800)
    return width, height


def _export_styles() -> str:
    return """
    <style>
      html, body { width: 100%; height: 100%; margin: 0; padding: 0; }
      .leaflet-control-zoom { display: none !important; }
      .leaflet-control-attribution {
        font-size: 10px !important;
        background: rgba(255,255,255,0.85) !important;
      }
    </style>
    """


def create_export_html(region: str, out_dir: Path | None = None) -> tuple[Path, tuple[int, int]]:
    specs = _region_specs()
    if region not in specs:
        raise ValueError(f"未知の region: {region}. 選択肢: {', '.join(specs)}")

    spec = specs[region]
    out_dir = out_dir or EXPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    geo = _apply_density(_merge_geojson(spec["slugs"]), _load_density_rows(spec["slugs"]))
    geo = _dissolve_municipalities(geo)
    geo = _clip_for_export(geo)
    sw, ne = _bounds_sw_ne(geo)
    width, height = _viewport_size(sw, ne)

    html_path = out_dir / f"{spec['label']}_ドラッグストア密度コロプレスマップ_export.html"
    sidecar = html_path.with_name(f"{html_path.stem}.geojson")

    optimized = optimize_geojson(
        geo,
        tolerance=0.0001,
        precision=EXPORT_GEOJSON_PRECISION,
    )
    save_geojson(sidecar, optimized)

    m = folium.Map(
        location=list(spec["center"]),
        zoom_start=spec["zoom"],
        tiles="OpenStreetMap",
        zoom_control=False,
        attr="© OpenStreetMap contributors",
    )
    m.get_root().html.add_child(folium.Element(_export_styles()))
    ExportGeoJson(
        url=sidecar.name,
        style_js=_CHOROPLETH_STYLE_JS,
        padding=list(EXPORT_FIT_PADDING),
    ).add_to(m)
    _make_density_colormap().add_to(m)
    m.save(str(html_path))

    meta_path = html_path.with_suffix(".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "region": region,
                "width": width,
                "height": height,
                "device_scale": EXPORT_DEVICE_SCALE,
                "bounds": {"sw": sw, "ne": ne},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  export HTML: {html_path} ({width}x{height})")
    return html_path, (width, height)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _serve_directory(directory: Path) -> tuple[ThreadingHTTPServer, int]:
    port = _pick_free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def export_png(
    html_path: Path,
    png_path: Path | None = None,
    width: int | None = None,
    height: int | None = None,
    device_scale: int = EXPORT_DEVICE_SCALE,
) -> Path:
    from playwright.sync_api import sync_playwright

    html_path = html_path.resolve()
    meta_path = html_path.with_suffix(".meta.json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        width = width or meta["width"]
        height = height or meta["height"]
        device_scale = meta.get("device_scale", device_scale)

    if width is None or height is None:
        raise ValueError("width/height が未指定で、meta.json も見つかりません")

    png_path = png_path or html_path.with_suffix(".png")
    server, port = _serve_directory(html_path.parent)
    url = f"http://127.0.0.1:{port}/{html_path.name}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=device_scale,
            )

            def _log_console(msg):
                if msg.type in {"error", "warning"}:
                    print(f"  [browser:{msg.type}] {msg.text}")

            page.on("console", _log_console)
            page.on("pageerror", lambda err: print(f"  [browser:error] {err}"))

            page.goto(url, wait_until="load", timeout=120_000)
            try:
                page.wait_for_function(
                    "window.__MAP_READY__ === true",
                    timeout=90_000,
                )
            except Exception:
                print("  警告: 描画完了シグナル待ちがタイムアウト。固定待機後に保存します。")
                page.wait_for_timeout(10_000)
            page.wait_for_timeout(5000)
            page.screenshot(path=str(png_path), type="png", full_page=False)
            browser.close()
    finally:
        server.shutdown()

    pixel_w = width * device_scale
    pixel_h = height * device_scale
    print(f"  PNG: {png_path} ({pixel_w}x{pixel_h}px)")
    return png_path


def build_and_export(
    region: str,
    out_dir: Path | None = None,
    html_only: bool = False,
) -> dict[str, Path]:
    html_path, _ = create_export_html(region, out_dir=out_dir)
    result = {"html": html_path, "geojson": html_path.with_name(f"{html_path.stem}.geojson")}
    if not html_only:
        result["png"] = export_png(html_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="密度コロプレスマップを fitBounds 付き HTML / 高解像度 PNG で出力",
    )
    parser.add_argument(
        "--region",
        choices=list(_region_specs()),
        default="hokkaido_tohoku",
        help="出力対象地域 (default: hokkaido_tohoku)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="HTML のみ生成（PNG は出力しない）",
    )
    parser.add_argument(
        "--png-only",
        type=Path,
        metavar="HTML",
        help="既存 export HTML から PNG のみ生成",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=EXPORTS_DIR,
        help=f"出力先 (default: {EXPORTS_DIR})",
    )
    args = parser.parse_args()

    if args.png_only:
        export_png(args.png_only)
        return

    print(f"密度コロプレス PNG 出力: {args.region}")
    build_and_export(args.region, out_dir=args.out_dir, html_only=args.html_only)


if __name__ == "__main__":
    main()

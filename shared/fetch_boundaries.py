"""国土地理院 N03 / GitHub ミラーから市区町村境界 GeoJSON 取得"""

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests

from shared.config import PREFECTURES
from shared.utils import ensure_dirs

# 国土地理院 行政区域データ（2025年基準・検証済みURL）
N03_ZIP_URLS = {
    "02": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2025/N03-20250101_02_GML.zip",
    "03": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2025/N03-20250101_03_GML.zip",
    "04": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2025/N03-20250101_04_GML.zip",
    "05": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2025/N03-20250101_05_GML.zip",
    "06": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2025/N03-20250101_06_GML.zip",
    "07": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2025/N03-20250101_07_GML.zip",
}

NIIYZ_API = "https://api.github.com/repos/niiyz/JapanCityGeoJson/contents/geojson"


def _download_gsi_zip(url: str, output_path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            return False
        with ZipFile(BytesIO(resp.content)) as zf:
            geojson_files = [n for n in zf.namelist() if n.endswith(".geojson")]
            if not geojson_files:
                return False
            with zf.open(geojson_files[0]) as f:
                geo = json.load(f)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geo, f, ensure_ascii=False)
        print(f"  GSI取得成功: {url} ({len(geo.get('features', []))} features)")
        return True
    except Exception as e:
        print(f"  GSI失敗 ({url}): {e}")
        return False


def _download_from_niiyz(pref_code: str, output_path: Path) -> Path:
    print(f"  GitHub ミラーから取得: pref={pref_code}")
    resp = requests.get(
        f"{NIIYZ_API}/{pref_code}?per_page=200",
        timeout=60,
        headers={"Accept": "application/vnd.github+json"},
    )
    resp.raise_for_status()
    files = resp.json()

    features = []
    for item in files:
        if item["type"] != "file" or not item["name"].endswith(".json"):
            continue
        try:
            geo_resp = requests.get(item["download_url"], timeout=60)
            geo_resp.raise_for_status()
            data = geo_resp.json()
            if data.get("type") == "FeatureCollection":
                features.extend(data.get("features", []))
            elif data.get("type") == "Feature":
                features.append(data)
        except Exception as e:
            print(f"    警告: {item['name']} 取得失敗 ({e})")

    if not features:
        raise RuntimeError(f"pref={pref_code} の GeoJSON が0件です")

    merged = {"type": "FeatureCollection", "features": features}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)
    print(f"  保存: {output_path} ({len(features)} features)")
    return output_path


def fetch_for_prefecture(slug: str) -> Path:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)

    if paths["geojson"].exists():
        with open(paths["geojson"], encoding="utf-8") as f:
            geo = json.load(f)
        if geo.get("features"):
            print(f"  既存GeoJSON: {paths['geojson']} ({len(geo['features'])}件)")
            return paths["geojson"]

    url = N03_ZIP_URLS.get(cfg["code"])
    if url and _download_gsi_zip(url, paths["geojson"]):
        return paths["geojson"]

    return _download_from_niiyz(cfg["code"], paths["geojson"])


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    fetch_for_prefecture(slug)

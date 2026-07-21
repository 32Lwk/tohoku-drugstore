"""国土地理院 N03 市区町村境界 GeoJSON 取得"""

import json
import zipfile
from io import BytesIO
from pathlib import Path

import requests

from shared.config import PREFECTURES
from shared.utils import ensure_dirs

# 国土地理院 行政区域データ（2020年基準）
N03_ZIP_URLS = {
    "02": "https://nlftp.mlit.go.jp/ksj/gml/codelist/N03-20230101_02_GML.zip",
    "03": "https://nlftp.mlit.go.jp/ksj/gml/codelist/N03-20230101_03_GML.zip",
    "04": "https://nlftp.mlit.go.jp/ksj/gml/codelist/N03-20230101_04_GML.zip",
    "05": "https://nlftp.mlit.go.jp/ksj/gml/codelist/N03-20230101_05_GML.zip",
    "06": "https://nlftp.mlit.go.jp/ksj/gml/codelist/N03-20230101_06_GML.zip",
    "07": "https://nlftp.mlit.go.jp/ksj/gml/codelist/N03-20230101_07_GML.zip",
}


def download_geojson(pref_code: str, output_path: Path) -> Path:
    url = N03_ZIP_URLS.get(pref_code)
    if not url:
        raise ValueError(f"未対応の都道府県コード: {pref_code}")

    print(f"  境界データDL: {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(BytesIO(resp.content)) as zf:
        geojson_files = [n for n in zf.namelist() if n.endswith(".geojson")]
        if not geojson_files:
            raise FileNotFoundError("ZIP内にGeoJSONが見つかりません")
        with zf.open(geojson_files[0]) as f:
            geo = json.load(f)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False)

    print(f"  保存: {output_path} ({len(geo.get('features', []))} features)")
    return output_path


def fetch_for_prefecture(slug: str) -> Path:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    if paths["geojson"].exists():
        print(f"  既存GeoJSONを使用: {paths['geojson']}")
        return paths["geojson"]
    return download_geojson(cfg["code"], paths["geojson"])


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    fetch_for_prefecture(slug)

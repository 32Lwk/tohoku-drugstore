"""和歌山県ドラッグストア地図 HTML から座標付き CSV を生成"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MAP_HTML = ROOT / "prefectures" / "08_和歌山県" / "maps" / "和歌山県ドラッグストア地図.html"
OUT_CSV = ROOT / "prefectures" / "08_和歌山県" / "data" / "和歌山県ドラッグストア_座標付き.csv"


def extract_stores(html_path: Path = MAP_HTML) -> pd.DataFrame:
    text = html_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"circle_marker_\w+ = L\.circleMarker\(\s*"
        r"\[([\d.]+),\s*([\d.]+)\],"
        r".*?"
        r"<b>([^<]+)</b>",
        re.DOTALL,
    )
    rows = []
    for lat, lon, name in pattern.findall(text):
        rows.append(
            {
                "company": name.strip(),
                "store_name": name.strip(),
                "address": "和歌山県",
                "latitude": float(lat),
                "longitude": float(lon),
            }
        )
    return pd.DataFrame(rows)


def main() -> Path:
    df = extract_stores()
    if df.empty:
        raise RuntimeError(f"店舗座標を抽出できません: {MAP_HTML}")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"和歌山店舗CSV: {OUT_CSV} ({len(df)}件)")
    return OUT_CSV


if __name__ == "__main__":
    main()

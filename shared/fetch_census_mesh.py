"""国勢調査2020 1kmメッシュ人口（e-Stat GIS）取得"""

import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from shared.config import PREFECTURES

CACHE_DIR = Path(__file__).resolve().parent / "census_cache" / "mesh_1km"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 令和2年国勢調査 3次メッシュ（1km）人口及び世帯（都道府県別）
ESTAT_MESH_STATS_ID = "T001100"
ESTAT_MESH_POP_COL = "T001100001"
ESTAT_MESH_URL = "https://www.e-stat.go.jp/gis/statmap-search/data"


def _download_mesh_csv(pref_code: str) -> Path:
    cache = CACHE_DIR / f"{pref_code}_mesh_1km.csv"
    if cache.exists():
        return cache

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 tohoku-drugstore/1.0",
            "Referer": "https://www.e-stat.go.jp/gis/statmap-search?page=1&toukeiCode=00200521&type=1",
        }
    )
    resp = session.get(
        ESTAT_MESH_URL,
        params={
            "statsId": ESTAT_MESH_STATS_ID,
            "code": pref_code,
            "downloadType": "2",
        },
        timeout=180,
    )
    resp.raise_for_status()
    if resp.content[:2] != b"PK":
        raise RuntimeError(f"メッシュZIP取得失敗: pref={pref_code}")

    with zipfile.ZipFile(BytesIO(resp.content)) as zf:
        txt_files = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txt_files:
            raise RuntimeError(f"メッシュTXT不在: pref={pref_code}")
        raw = zf.read(txt_files[0])

    cache.write_bytes(raw)
    print(f"  メッシュ人口DL: {cache}")
    return cache


def _parse_mesh_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp932")
    # 1行目は日本語ヘッダー行
    if pd.isna(df.iloc[0].get("KEY_CODE")):
        df = df.iloc[1:].copy()

    df["KEY_CODE"] = df["KEY_CODE"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["人口"] = pd.to_numeric(df[ESTAT_MESH_POP_COL], errors="coerce").fillna(0)
    df.loc[df["人口"] < 0, "人口"] = 0

    out = df[["KEY_CODE", "人口"]].copy()
    out = out[out["人口"] > 0].drop_duplicates("KEY_CODE")
    return out


def fetch_mesh_population(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    pref_code = cfg["code"]
    csv_path = _download_mesh_csv(pref_code)
    mesh = _parse_mesh_csv(csv_path)
    print(f"  メッシュ人口: {len(mesh)}件 (pref={pref_code})")
    return mesh


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    fetch_mesh_population(target)

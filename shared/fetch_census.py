"""国勢調査2020 市区町村別 人口・高齢化率 取得"""

import json
import os
import re
from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
import requests

from shared.config import PREFECTURES
from shared.utils import ensure_dirs

CACHE_DIR = Path(__file__).resolve().parent / "census_cache"
CACHE_DIR.mkdir(exist_ok=True)

# 令和2年国勢調査 都道府県・市区町村別の主な結果（xlsx）
ESTAT_MUNICIPAL_XLSX = {
    "url": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032143614&fileKind=0",
    "referer": "https://www.e-stat.go.jp/stat-search/files?stat_infid=000032143614",
}

ESTAT_SIMPLE = "https://api.e-stat.go.jp/rest/3.0/app/getSimpleStatsData"
STATS_DATA_IDS = ["0004014782", "0004009730", "0003445078"]
PREF_CD_AREA = {
    "02": "02000", "03": "03000", "04": "04000",
    "05": "05000", "06": "06000", "07": "07000",
}


def _download_estat_xlsx() -> bytes:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 tohoku-drugstore/1.0"})
    session.get(ESTAT_MUNICIPAL_XLSX["referer"], timeout=60)
    resp = session.get(ESTAT_MUNICIPAL_XLSX["url"], timeout=180)
    resp.raise_for_status()
    return resp.content


def _parse_estat_xlsx(content: bytes, prefecture: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_excel(BytesIO(content), sheet_name="第１面事項_2020年", header=None)
    pref_code = next(v["code"] for v in PREFECTURES.values() if v["name"] == prefecture)
    rows = df[df[0].astype(str).str.startswith(f"{pref_code}_")]

    pop_rows, aging_rows = [], []
    for _, row in rows.iterrows():
        code_name = str(row[1])
        if pd.isna(code_name) or code_name == "nan":
            continue
        city = _parse_city_name(code_name)
        if not city or city == prefecture:
            continue
        total = _to_float(row[4])
        elderly = _to_float(row[16])
        aging_rate = _to_float(row[19])
        if total:
            pop_rows.append({"市区町村": city, "人口": total})
        if elderly and total:
            aging_rows.append({
                "市区町村": city,
                "総数": total,
                "65歳以上": elderly,
                "高齢化率": aging_rate if aging_rate else round(elderly / total * 100, 2),
            })

    return (
        pd.DataFrame(pop_rows).drop_duplicates("市区町村"),
        pd.DataFrame(aging_rows).drop_duplicates("市区町村"),
    )


def _fetch_via_estat_api(pref_code: str, prefecture: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    app_id = os.getenv("ESTAT_APP_ID") or os.getenv("estat_app_id")
    if not app_id:
        raise ValueError("ESTAT_APP_ID 未設定")

    for stats_id in STATS_DATA_IDS:
        try:
            resp = requests.get(
                ESTAT_SIMPLE,
                params={"appId": app_id, "statsDataId": stats_id, "cdArea": PREF_CD_AREA[pref_code], "metaGetFlg": "N"},
                timeout=120,
            )
            if resp.status_code != 200 or len(resp.content) < 100:
                continue
            for enc in ["utf-8", "cp932", "shift_jis"]:
                try:
                    text = resp.content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                continue
            df = pd.read_csv(StringIO(text), low_memory=False)
            pop_df, aging_df = _parse_estat_table(df, prefecture)
            if not pop_df.empty:
                return pop_df, aging_df
        except Exception:
            continue
    raise RuntimeError("e-Stat API 取得失敗")


def _parse_estat_table(df: pd.DataFrame, prefecture: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = [str(c) for c in df.columns]
    city_col = next((c for c in cols if "市区町村" in c or "地域" in c), cols[0])
    pop_col = next((c for c in cols if "人口" in c and "密度" not in c), None)
    elderly_col = next((c for c in cols if "65" in c or "高齢" in c), None)
    aging_rate_col = next((c for c in cols if "高齢化率" in c), None)

    pop_rows, aging_rows = [], []
    for _, row in df.iterrows():
        city = _normalize_city(str(row.get(city_col, "")), prefecture)
        if not city:
            continue
        pop = _to_float(row.get(pop_col)) if pop_col else None
        elderly = _to_float(row.get(elderly_col)) if elderly_col else None
        aging_rate = _to_float(row.get(aging_rate_col)) if aging_rate_col else None
        if pop and pop > 0:
            pop_rows.append({"市区町村": city, "人口": pop})
        if aging_rate:
            aging_rows.append({"市区町村": city, "高齢化率": aging_rate})
        elif elderly and pop:
            aging_rows.append({"市区町村": city, "総数": pop, "65歳以上": elderly, "高齢化率": round(elderly / pop * 100, 2)})

    return pd.DataFrame(pop_rows), pd.DataFrame(aging_rows)


def _build_from_geojson(slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = ensure_dirs(slug)
    with open(paths["geojson"], encoding="utf-8") as f:
        geo = json.load(f)
    cities = []
    for feat in geo.get("features", []):
        p = feat.get("properties", {})
        prefix = p.get("N03_003") or ""
        name = p.get("N03_004") or ""
        cities.append(f"{prefix}{name}" if prefix and name else name)
    unique = sorted(set(c for c in cities if c))
    pop_df = pd.DataFrame({"市区町村": unique, "人口": None})
    aging_df = pd.DataFrame({"市区町村": unique, "高齢化率": None})
    print("  警告: GeoJSONフォールバック（人口・高齢化率は空）")
    return pop_df, aging_df


def _parse_city_name(code_name: str) -> str:
    m = re.search(r"_(.+)$", code_name)
    return m.group(1) if m else code_name


def _normalize_city(raw: str, prefecture: str) -> str:
    s = raw.replace(prefecture, "").strip()
    m = re.search(r"(.+?(?:市|区|町|村))", s)
    return m.group(1) if m else s.strip()


def _to_float(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(str(val).replace(",", "").replace(" ", "").replace("－", ""))
    except ValueError:
        return None


def fetch_for_prefecture(slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    prefecture = cfg["name"]
    pref_code = cfg["code"]

    pop_cache = CACHE_DIR / f"{pref_code}_population.csv"
    aging_cache = CACHE_DIR / f"{pref_code}_aging.csv"

    if pop_cache.exists() and aging_cache.exists():
        pop_df = pd.read_csv(pop_cache, encoding="utf-8-sig")
        aging_df = pd.read_csv(aging_cache, encoding="utf-8-sig")
        print(f"  キャッシュ使用: {pref_code}")
    else:
        pop_df, aging_df = pd.DataFrame(), pd.DataFrame()

        # 手法1: e-Stat xlsx（ESTAT_APP_ID 不要）
        try:
            xlsx_cache = CACHE_DIR / "estat_municipal_2020.xlsx"
            if not xlsx_cache.exists():
                print("  国勢調査xlsxをダウンロード中...")
                xlsx_cache.write_bytes(_download_estat_xlsx())
            pop_df, aging_df = _parse_estat_xlsx(xlsx_cache.read_bytes(), prefecture)
            if not pop_df.empty:
                print("  xlsx取得成功")
        except Exception as e:
            print(f"  xlsx取得失敗: {e}")

        # 手法2: e-Stat API
        if pop_df.empty:
            try:
                pop_df, aging_df = _fetch_via_estat_api(pref_code, prefecture)
                print("  e-Stat API取得成功")
            except Exception as e:
                print(f"  e-Stat API失敗: {e}")

        # 手法3: GeoJSONフォールバック（人口なし）
        if pop_df.empty:
            pop_df, aging_df = _build_from_geojson(slug)

        pop_df.to_csv(pop_cache, index=False, encoding="utf-8-sig")
        aging_df.to_csv(aging_cache, index=False, encoding="utf-8-sig")

    pop_df.to_csv(paths["population_csv"], index=False, encoding="utf-8-sig")
    aging_df.to_csv(paths["aging_csv"], index=False, encoding="utf-8-sig")
    print(f"  人口: {len(pop_df)}市区町村 / 高齢化率: {len(aging_df)}市区町村")
    return pop_df, aging_df


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    fetch_for_prefecture(slug)

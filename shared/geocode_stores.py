"""座標取得・補完"""

import os
import pickle
import time

import pandas as pd
import requests

from shared.config import PREFECTURES
from shared.utils import ensure_dirs, load_api_key


def geocode_google(address: str, api_key: str) -> tuple[float, float] | None:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "region": "jp"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    except Exception as e:
        print(f"    Geocode error: {e}")
    return None


def geocode_gsi(address: str) -> tuple[float, float] | None:
    url = "https://msearch.gsi.go.jp/address-search/AddressSearch"
    try:
        resp = requests.get(url, params={"q": address}, timeout=15)
        results = resp.json()
        if results:
            coords = results[0].get("geometry", {}).get("coordinates", [])
            if len(coords) >= 2:
                return coords[1], coords[0]
    except Exception:
        pass
    return None


def geocode_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    api_key = load_api_key(required=False)

    df_raw = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig") if paths["raw_csv"].exists() else pd.DataFrame()
    coord_from_raw = {}
    if not df_raw.empty and "address" in df_raw.columns:
        for _, row in df_raw.iterrows():
            if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
                coord_from_raw[row["address"]] = (row["latitude"], row["longitude"])

    df = pd.read_csv(paths["final_csv"], encoding="utf-8-sig")
    cache: dict = {}
    if paths["cache"].exists():
        with open(paths["cache"], "rb") as f:
            cache = pickle.load(f)

    lats, lons = [], []
    api_calls = 0
    # Geocoding も課金対象のためハード上限（超過分は国土地理院へフォールバック）
    max_geocode_calls = int(os.getenv("GEOCODE_MAX_REQUESTS_PER_RUN", "200"))

    for _, row in df.iterrows():
        addr = row["address"]
        coords = coord_from_raw.get(addr) or cache.get(addr)

        if coords is None and api_key and api_calls < max_geocode_calls:
            coords = geocode_google(addr, api_key)
            api_calls += 1
            time.sleep(0.1)
        elif coords is None and api_key and api_calls >= max_geocode_calls:
            # 予算超過後は Google Geocoding を呼ばない
            pass

        if coords is None:
            coords = geocode_gsi(addr)

        cache[addr] = coords
        if coords:
            lats.append(coords[0])
            lons.append(coords[1])
        else:
            lats.append(None)
            lons.append(None)

    df["latitude"] = lats
    df["longitude"] = lons
    df.to_csv(paths["coord_csv"], index=False, encoding="utf-8-sig")

    with open(paths["cache"], "wb") as f:
        pickle.dump(cache, f)

    ok = df["latitude"].notna().sum()
    print(f"座標付き: {paths['coord_csv']} ({ok}/{len(df)}件, API呼出{api_calls}回)")
    return df


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    geocode_for_prefecture(slug)

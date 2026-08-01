"""地理計算ユーティリティ（距離・メッシュ中心）"""

import math

import numpy as np

EARTH_RADIUS_KM = 6371.0


def mesh_center(key_code) -> tuple[float, float]:
    """8桁 KEY_CODE から 1km メッシュ中心の (lat, lon) を返す（JIS X 0410）"""
    code = str(int(float(key_code))).zfill(8)
    p = int(code[0:2])
    q = int(code[2:4])
    r_lat = int(code[4])
    r_lon = int(code[5])
    s_lat = int(code[6])
    s_lon = int(code[7])

    lat = p * 2 / 3 + r_lat * (2 / 3 / 8) + s_lat * (2 / 3 / 8 / 10) + (2 / 3 / 8 / 10 / 2)
    lon = q + 100 + r_lon * (1 / 8) + s_lon * (1 / 8 / 10) + (1 / 8 / 10 / 2)
    return lat, lon


def haversine_km(
    lat1: np.ndarray | float,
    lon1: np.ndarray | float,
    lat2: np.ndarray | float,
    lon2: np.ndarray | float,
) -> np.ndarray:
    """Haversine 直線距離 (km)。配列ブロードキャスト対応。"""
    lat1 = np.asarray(lat1, dtype=float)
    lon1 = np.asarray(lon1, dtype=float)
    lat2 = np.asarray(lat2, dtype=float)
    lon2 = np.asarray(lon2, dtype=float)

    lat1_r = np.radians(lat1)
    lon1_r = np.radians(lon1)
    lat2_r = np.radians(lat2)
    lon2_r = np.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def nearest_distances_km(
    point_lat: np.ndarray,
    point_lon: np.ndarray,
    store_lat: np.ndarray,
    store_lon: np.ndarray,
) -> np.ndarray:
    """各点から最寄り店舗までの直線距離 (km)"""
    point_lat = np.asarray(point_lat, dtype=float)
    point_lon = np.asarray(point_lon, dtype=float)
    store_lat = np.asarray(store_lat, dtype=float)
    store_lon = np.asarray(store_lon, dtype=float)

    lat = point_lat[:, None]
    lon = point_lon[:, None]
    slat = store_lat[None, :]
    slon = store_lon[None, :]
    dist = haversine_km(lat, lon, slat, slon)
    return dist.min(axis=1)


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    """人口加重平均"""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    mask = weights > 0
    if not mask.any():
        return float("nan")
    return float(np.average(values[mask], weights=weights[mask]))


def weighted_percentile(
    values: np.ndarray,
    weights: np.ndarray,
    percentile: float,
) -> float:
    """人口加重パーセンタイル（近似）"""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    mask = (weights > 0) & np.isfinite(values)
    if not mask.any():
        return float("nan")
    v = values[mask]
    w = weights[mask]
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cum = np.cumsum(w)
    target = percentile / 100.0 * cum[-1]
    idx = int(np.searchsorted(cum, target, side="left"))
    idx = min(idx, len(v) - 1)
    return float(v[idx])

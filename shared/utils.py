"""共通ユーティリティ"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_api_key() -> str:
    load_dotenv(ROOT_DIR / ".env")
    key = os.getenv("Google_Place_API") or os.getenv("GOOGLE_PLACE_API")
    if not key:
        raise ValueError(
            "Google_Place_API が未設定です。"
            " .env または Cloud Agent の Environment Variables に設定してください。"
        )
    return key


def normalize_address(address: str, prefecture: str) -> str:
    if not address:
        return ""
    addr = address.strip()
    addr = re.sub(r"^日本、?\s*", "", addr)
    addr = re.sub(r"〒?\d{3}-?\d{4}\s*", "", addr)
    addr = re.sub(r"\s+", "", addr)
    if not addr.startswith(prefecture):
        if prefecture.replace("県", "") in addr or prefecture in addr:
            idx = addr.find(prefecture[0])
            for i, c in enumerate(addr):
                if addr[i:].startswith(prefecture[:2]):
                    addr = addr[i:]
                    break
        if not addr.startswith(prefecture):
            addr = prefecture + addr
    return addr


def is_pharmacy_only(store_name: str) -> bool:
    from shared.config import EXCLUDE_NAME_KEYWORDS

    name = store_name or ""
    if any(kw in name for kw in EXCLUDE_NAME_KEYWORDS):
        if not any(
            ds in name
            for ds in [
                "ドラッグ",
                "Drug",
                "DRUG",
                "スギ",
                "Vドラッグ",
                "GENKY",
                "ZIP",
                "マツモト",
                "ツルハ",
                "ウエルシア",
                "サンド",
                "ココカラ",
                "コスモス",
                "ユタカ",
            ]
        ):
            return True
    return False


def normalize_chain_name(name: str, search_query: str = "") -> str:
    from shared.config import CHAIN_NORMALIZE, KNOWN_CHAINS

    text = name or search_query
    for chain in KNOWN_CHAINS:
        if chain in text or chain.lower() in text.lower():
            return CHAIN_NORMALIZE.get(chain, chain)
    if "スギ" in text and "薬局" not in text:
        return "スギ薬局"
    return name.split(" ")[0] if name else "不明"


def prefecture_paths(slug: str) -> dict:
    base = ROOT_DIR / "prefectures" / slug
    return {
        "base": base,
        "data": base / "data",
        "maps": base / "maps",
        "geojson": base / "data" / "municipalities.geojson",
        "raw_csv": base / "data" / "raw_stores.csv",
        "final_csv": base / "data" / f"{slug.split('_', 1)[1]}ドラッグストア_最終版.csv",
        "coord_csv": base / "data" / f"{slug.split('_', 1)[1]}ドラッグストア_座標付き.csv",
        "density_csv": base / "data" / "市区町村別ドラッグストア分析.csv",
        "aging_csv": base / "data" / "市区町村別高齢化率.csv",
        "population_csv": base / "data" / "市区町村別人口.csv",
        "report": base / "report.md",
        "cache": base / "data" / "geocode_cache.pkl",
    }


def ensure_dirs(slug: str) -> dict:
    paths = prefecture_paths(slug)
    paths["data"].mkdir(parents=True, exist_ok=True)
    paths["maps"].mkdir(parents=True, exist_ok=True)
    return paths

"""共通ユーティリティ"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_api_key(required: bool = True) -> str | None:
    load_dotenv(ROOT_DIR / ".env")
    key = (
        os.getenv("Google_Place_API")
        or os.getenv("GOOGLE_PLACE_API")
        or os.getenv("GOOGLE_MAPS_API_KEY")
    )
    if not key:
        if required:
            raise ValueError(
                "Google_Place_API が未設定です。"
                " .env または Cloud Agent の Environment Variables に設定してください。"
            )
        return None
    return key


PREFECTURE_NAMES = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]


def normalize_address(address: str, prefecture: str) -> str:
    if not address:
        return ""
    addr = address.strip()
    addr = re.sub(r"^日本、?\s*", "", addr)
    addr = re.sub(r"〒?\d{3}-?\d{4}\s*", "", addr)
    addr = re.sub(r"\s+", "", addr)

    found = [p for p in PREFECTURE_NAMES if p in addr]

    # 「岩手県岐阜県…」のように対象県を誤前置した汚染 → 先頭の対象県を除去
    if addr.startswith(prefecture):
        rest = addr[len(prefecture) :]
        others_in_rest = [p for p in PREFECTURE_NAMES if p != prefecture and p in rest]
        if others_in_rest:
            return rest  # 他県住所として返す（is_in_prefecture で除外）

    if prefecture in found:
        idx = addr.find(prefecture)
        if idx > 0:
            addr = addr[idx:]
        return addr

    if found:
        # 対象県以外の都道府県住所
        return addr

    if not addr.startswith(prefecture):
        addr = prefecture + addr
    return addr


def is_in_prefecture(address: str, prefecture: str) -> bool:
    if not address or prefecture not in address:
        return False
    others = [p for p in PREFECTURE_NAMES if p != prefecture and p in address]
    return len(others) == 0


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
                "薬王堂",
                "ハッピー",
                "カワチ",
            ]
        ):
            return True
    return False


def normalize_chain_name(name: str, search_query: str = "") -> str:
    from shared.config import CHAIN_NORMALIZE, KNOWN_CHAINS

    text = name or search_query
    # 長いチェーン名を優先マッチ（部分一致の誤爆を減らす）
    for chain in sorted(KNOWN_CHAINS, key=len, reverse=True):
        if chain in text or chain.lower() in text.lower():
            return CHAIN_NORMALIZE.get(chain, chain)
    if "スギ" in text:
        return "スギ薬局"
    if "薬王堂" in text:
        return "薬王堂"
    if "ハッピー" in text and "ドラッグ" in text:
        return "ハッピードラッグ"
    if "クリエイトSD" in text or "クリエイト エスディー" in text:
        return "クリエイトSD"
    if "サンドラッグ" in text or "サンドラック" in text:
        return "サンドラック"
    # 未知チェーンは店舗名全体を返さず「その他」に統一（discovered_chains 汚染防止）
    return "その他"


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

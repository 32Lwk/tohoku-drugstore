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


_OTHER_PREF_RE = re.compile(
    r"北海道|(?:東京|京都|大阪)都?府?|"
    r"(?:青森|岩手|宮城|秋田|山形|茨城|栃木|群馬|埼玉|千葉|神奈川|新潟|富山|石川|福井|"
    r"山梨|長野|岐阜|静岡|愛知|三重|滋賀|兵庫|奈良|和歌山|鳥取|島根|岡山|広島|山口|"
    r"徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄)県"
)


def address_in_prefecture(address: str, prefecture: str) -> bool:
    """正規化前の住所が対象県のものか判定（他県住所への県名付与を防ぐ）"""
    if not address:
        return False
    addr = address.strip()
    addr = re.sub(r"^日本、?\s*", "", addr)
    addr = re.sub(r"〒?\d{3}-?\d{4}\s*", "", addr)
    addr = re.sub(r"\s+", "", addr)
    if not addr.startswith(prefecture):
        return False
    rest = addr[len(prefecture) :]
    # 「福島県福井県…」「福島県愛知県…」のような二重県名を除外
    if _OTHER_PREF_RE.search(rest):
        return False
    return True


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

    text = name or ""
    # 曖昧語は厳密マッチ
    if "薬王堂" in text:
        return "薬王堂"
    if "ハッピードラッグ" in text or "ハッピー・ドラッグ" in text:
        return "ハッピードラッグ"
    if "サンドラッグ" in text or "サンドラック" in text:
        return "サンドラッグ"
    if any(k in text for k in ("ドラッグストアコスモス", "コスモス薬品", "コスモスドラッグ")) or (
        text.startswith("コスモス") and "ドラッグ" in text
    ):
        return "コスモス"
    if any(k in text for k in ("クリエイトエス", "クリエイトSD")) or (
        "クリエイト" in text and "ドラッグ" in text
    ):
        return "クリエイトSD"
    if "キョーリン堂" in text:
        return "キョーリン堂"

    for chain in KNOWN_CHAINS:
        # 曖昧チェーンは上で処理済みのためスキップ
        if chain in ("コスモス", "クリエイトエス・ディー", "クリエイトSD", "キョーリン堂"):
            continue
        if chain in text or chain.lower() in text.lower():
            return CHAIN_NORMALIZE.get(chain, chain)
    if "スギ" in text and "薬局" not in text:
        return "スギ薬局"
    # 未知ブランドをチェーン扱いにしない（先頭語を返すと二次検索が爆発する）
    return "不明"


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

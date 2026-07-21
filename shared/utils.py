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


_PREFECTURE_NAMES = [
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
    """住所を正規化する。対象都道府県外なら空文字を返す。"""
    if not address:
        return ""
    addr = address.strip()
    addr = re.sub(r"^日本、?\s*", "", addr)
    addr = re.sub(r"〒?\d{3}-?\d{4}\s*", "", addr)
    addr = re.sub(r"\s+", "", addr)

    # 他都道府県を含む場合は対象外（誤って県名を前置しない）
    for p in _PREFECTURE_NAMES:
        if p == prefecture:
            continue
        if p in addr:
            return ""

    if addr.startswith(prefecture):
        return addr

    # 「秋田市…」のように県名なしの場合のみ補完
    short = prefecture.replace("県", "").replace("府", "").replace("都", "")
    if short and short in addr[:10]:
        return prefecture + addr if not addr.startswith(prefecture) else addr

    # 県名が一切確認できない住所は採用しない
    return ""


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


# 曖昧語は厳密パターン必須（理容室・企業名などの誤ヒット防止）
# 注意: パターン1つでも末尾カンマ必須 → (r"foo",)  でないと str になり1文字ずつ誤マッチする
_STRICT_CHAIN_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("コスモス", (r"ドラッグストア\s*コスモス", r"コスモス\s*ドラッグ", r"ドラッグストアコスモス")),
    ("クリエイト", (r"クリエイト\s*S\s*D", r"クリエイトＳＤ", r"クリエイトエス・?ディー", r"クリエイトエスディー")),
    ("キョーリン", (r"キョーリン\s*ドラッグ", r"ドラッグ\s*キョーリン")),
    ("杏林堂", (r"杏林堂ドラッグ", r"ドラッグ杏林堂")),
    ("GENKY", (r"GENKY", r"ゲンキー")),
    ("ツルハドラッグ", (r"ツルハドラッグ", r"ツルハ")),
    ("ハッピードラッグ", (r"ハッピー[・･\s]?ドラッグ", r"ハッピードラッグ")),
    ("ウエルシア", (r"ウエルシア",)),
    ("サンドラッグ", (r"サンドラッグ", r"サンドラック")),
    ("マツモトキヨシ", (r"マツモトキヨシ", r"マツキヨ")),
    ("セイムス", (r"セイムス",)),
    ("サツドラ", (r"サツドラ",)),
    ("カワチ薬品", (r"カワチ薬品", r"カワチ")),
    ("クスリのアオキ", (r"クスリのアオキ", r"くすりのあおき")),
    ("なの花ドラッグ", (r"なの花ドラッグ",)),
    ("よどやドラッグ", (r"よどやドラッグ",)),
    ("ドラッグユタカ", (r"ドラッグユタカ", r"ユタカ薬局")),
    ("スギ薬局", (r"スギ薬局", r"スギドラッグ")),
    ("Vドラッグ", (r"Vドラッグ", r"ブイドラッグ")),
    ("ZIPドラッグ", (r"ZIPドラッグ", r"ジップドラッグ")),
    ("ココカラファイン", (r"ココカラファイン", r"ココカラ")),
    ("トモズ", (r"トモズ",)),
    ("ダイコクドラッグ", (r"ダイコクドラッグ",)),
    ("キリン堂", (r"キリン堂",)),
    ("コクミン", (r"コクミン",)),
    ("ハックドラッグ", (r"ハックドラッグ",)),
    ("セキ薬品", (r"セキ薬品",)),
    ("ドラッグスギヤマ", (r"ドラッグスギヤマ", r"スギヤマ")),
    ("スーパードラッグアサヒ", (r"スーパードラッグアサヒ", r"スーパードラッグメガ", r"ドラッグアサヒ")),
    ("薬王堂", (r"薬王堂",)),
]


def normalize_chain_name(name: str, search_query: str = "") -> str:
    from shared.config import CHAIN_NORMALIZE

    text = (name or "") + " " + (search_query or "")
    text_n = text.replace("・", "").replace("･", "").replace(" ", "")

    for chain, patterns in _STRICT_CHAIN_RULES:
        if isinstance(patterns, str):  # カンマ漏れ防御
            patterns = (patterns,)
        for pat in patterns:
            flags = re.IGNORECASE if re.search(r"[A-Za-z]", pat) else 0
            if re.search(pat, text, flags) or re.search(pat, text_n, flags):
                return CHAIN_NORMALIZE.get(chain, chain)

    if "スギ" in text and ("ドラッグ" in text or "薬局" in text):
        return "スギ薬局"
    return "不明"


def store_matches_searched_chain(store_name: str, company: str) -> bool:
    """チェーン精査検索の結果が、本当にそのチェーンか判定する。"""
    if not company:
        return True
    detected = normalize_chain_name(store_name)
    return detected == company


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

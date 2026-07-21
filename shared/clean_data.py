"""データクリーニング・重複削除・薬局除外"""

import re

import pandas as pd

from shared.config import CHAIN_NORMALIZE, PREFECTURES
from shared.utils import (
    address_in_prefecture,
    ensure_dirs,
    is_pharmacy_only,
    normalize_address,
    normalize_chain_name,
)

# ドラッグストア以外の誤検出を除外
NON_DRUGSTORE_PATTERNS = re.compile(
    r"Can★Do|キャンドゥ|Seria|セリア|TSUTAYA|ツタヤ|道の駅|"
    r"Amazon\s*ロッカー|カインズ|PLANT-?5|PLANT5|"
    r"イオンモール|イオンスーパー|イオン双葉|イオン広野|イオン浪江|イオン\s|"
    r"エコス|物産館|アートプロジェクト|オフィス・|"
    r"コスモスの会|なみえの記憶|Dias\s*コスモス|"
    r"\(有\)クリエイト|（有）クリエイト|アースクリエイト|クリエイト㈱|クリエイト株式会社|"
    r"キョーリン製薬|工場株式会社|"
    r"セブン-?イレブン|ファミリーマート|ローソン|ミニストップ|"
    r"ダイソー|しまむら|ドン・?キホーテ|トライアル|"
    r"ダイユーエイト|ファッションセンター|スーパーセンター|"
    r"ショッピングセンター|復興交流館|コスメティックサロン|"
    r"撚糸|薬草店|清水薬草|"
    r"むすんでひらいて"
)

# 他県の「福島」地名（大阪市福島区など）や不完全住所
INVALID_FUKUSHIMA_ADDR = re.compile(
    r"福島県福島区|福島県福島[０-９0-9]|福島県福島１５|福島県福島[一二三四五六七八九]"
)


def _load_municipality_names(slug: str, prefecture: str) -> list[str]:
    paths = ensure_dirs(slug)
    names: set[str] = set()
    pop = paths["population_csv"]
    if pop.exists():
        try:
            pdf = pd.read_csv(pop, encoding="utf-8-sig")
            col = "市区町村" if "市区町村" in pdf.columns else pdf.columns[0]
            for v in pdf[col].dropna().astype(str):
                v = v.strip()
                if v and v != prefecture:
                    names.add(v.replace(prefecture, ""))
        except Exception:
            pass
    geo = paths["geojson"]
    if geo.exists():
        try:
            import json

            with open(geo, encoding="utf-8") as f:
                g = json.load(f)
            for feat in g.get("features", []):
                p = feat.get("properties", {})
                n = p.get("N03_004") or ""
                if n and n not in ("所属未定地",):
                    names.add(n)
        except Exception:
            pass
    return sorted(names, key=len, reverse=True)


def address_has_municipality(address: str, prefecture: str, municipalities: list[str]) -> bool:
    if not address_in_prefecture(address, prefecture):
        return False
    if INVALID_FUKUSHIMA_ADDR.search(address or ""):
        return False
    if not municipalities:
        return bool(re.search(r"(市|区|町|村)", address or ""))
    return any(m and m in address for m in municipalities)


def normalize_company(company: str, store_name: str = "") -> str:
    name = store_name or ""
    if "ブイチェーン" in name or "Vチェーン" in name or "Ｖチェーン" in name:
        return "Vドラッグ"
    if "ハシドラッグ" in name:
        return "ハシドラッグ"
    if store_name:
        inferred = normalize_chain_name(store_name)
        if inferred != "不明":
            return CHAIN_NORMALIZE.get(inferred, inferred)
    company = company or "不明"
    return CHAIN_NORMALIZE.get(company, company)


def address_key(address: str) -> str:
    a = re.sub(r"\s+", "", address or "")
    a = re.sub(r"[０-９]", lambda m: chr(ord(m.group()) - 0xFEE0), a)
    return a


def is_non_drugstore_noise(store_name: str) -> bool:
    name = store_name or ""
    if NON_DRUGSTORE_PATTERNS.search(name):
        return True
    # 「クリエイト」単独でドラッグストア語がないもの
    if "クリエイト" in name and not any(k in name for k in ("ドラッグ", "エス・ディー", "SD", "create")):
        return True
    # コスモスの曖昧ヒット
    if "コスモス" in name and not any(
        k in name for k in ("ドラッグ", "薬品", "cosmos", "Cosmos")
    ):
        return True
    # スーパー・モール・コンビニ等
    if any(
        k in name
        for k in (
            "ヨークベニマル",
            "リオン・ドール",
            "リオン・ドール",
            "メガステージ",
            "ヤマザキ",
            "Ｙショップ",
            "Yショップ",
            "さくらモール",
            "ショッピングプラザ",
            "おしゃべり",
            "マルイチ商店",
            "デイリーストアー",
            "スーパー",
            "コンビニ",
        )
    ):
        return True
    return False


def looks_like_drugstore(store_name: str, company: str) -> bool:
    """不明チェーンはドラッグストアらしい名称のみ残す"""
    if company and company != "不明":
        return True
    name = store_name or ""
    keywords = (
        "ドラッグ",
        "Drug",
        "DRUG",
        "くすり",
        "クスリ",
        "薬店",
        "薬舗",
        "薬品",
        "ファーマシー",
        "Pharmacy",
        "ケンコー",
        "薬王",
    )
    return any(k in name for k in keywords)


def clean_stores(df: pd.DataFrame, prefecture: str, slug: str = "") -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    municipalities = _load_municipality_names(slug, prefecture) if slug else []

    # 正規化前に他県住所・不正住所を除外
    before = len(df)
    df = df[df["address"].apply(lambda a: address_has_municipality(a, prefecture, municipalities))]
    print(f"  他県/不正住所除外: {before - len(df)}件")

    df["address"] = df["address"].apply(lambda a: normalize_address(a, prefecture))
    df = df[df["address"].str.startswith(prefecture, na=False)]

    before = len(df)
    df = df[~df["store_name"].apply(is_non_drugstore_noise)]
    print(f"  非DSノイズ除外: {before - len(df)}件")

    df["company"] = df.apply(
        lambda r: normalize_company(r.get("company", ""), r.get("store_name", "")),
        axis=1,
    )

    before = len(df)
    df = df[df.apply(lambda r: looks_like_drugstore(r["store_name"], r["company"]), axis=1)]
    print(f"  非DS名称除外(不明): {before - len(df)}件")

    before = len(df)
    strict_pharmacy = df["store_name"].str.contains("薬局|調剤", na=False)
    df = df[~strict_pharmacy]
    print(f"  薬局除外（厳格）: {before - len(df)}件")

    before = len(df)
    df = df[~df["store_name"].apply(is_pharmacy_only)]
    print(f"  薬局除外（追加）: {before - len(df)}件")

    if "place_id" in df.columns:
        df = df.drop_duplicates(subset=["place_id"], keep="first")
    df = df.drop_duplicates(subset=["company", "address"], keep="first")

    # 同一住所・同一チェーンの重複のみ整理（異チェーンは残す）
    groups = {}
    for idx, row in df.iterrows():
        key = address_key(row["address"])
        groups.setdefault(key, []).append(idx)

    drop_indices = []
    for key, indices in groups.items():
        if len(indices) <= 1:
            continue
        rows = [(i, df.loc[i]) for i in indices]
        by_company: dict[str, list] = {}
        for i, r in rows:
            by_company.setdefault(r["company"], []).append(i)
        for company, idxs in by_company.items():
            if len(idxs) > 1:
                for i in idxs[1:]:
                    drop_indices.append(i)

    if drop_indices:
        df = df.drop(index=drop_indices)
        print(f"  同一住所重複整理: {len(drop_indices)}件削除")

    df = df.sort_values(["company", "store_name"]).reset_index(drop=True)
    return df[["company", "store_name", "address"]]


def clean_for_prefecture(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)

    if not paths["raw_csv"].exists():
        raise FileNotFoundError(f"生データがありません: {paths['raw_csv']}")

    df = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
    print(f"クリーニング開始: {len(df)}件")
    cleaned = clean_stores(df, cfg["name"], slug=slug)
    cleaned.to_csv(paths["final_csv"], index=False, encoding="utf-8-sig")
    print(f"最終データ: {paths['final_csv']} ({len(cleaned)}件)")
    return cleaned


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    clean_for_prefecture(slug)

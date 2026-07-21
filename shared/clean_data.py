"""データクリーニング・重複削除・薬局除外"""

import re

import pandas as pd

from shared.config import (
    CHAIN_NORMALIZE,
    CHAIN_NAME_REQUIRED_PATTERNS,
    KNOWN_CHAINS,
    NOISE_NAME_KEYWORDS,
    PREFECTURES,
)
from shared.utils import ensure_dirs, is_pharmacy_only, normalize_address, normalize_chain_name

KNOWN_CHAIN_NAMES = set(KNOWN_CHAINS) | set(CHAIN_NORMALIZE.values())

DRUGSTORE_HINTS = [
    "ドラッグ",
    "Drug",
    "DRUG",
    "くすり",
    "クスリ",
    "ウエルシア",
    "ウェルシア",
    "ツルハ",
    "マツモトキヨシ",
    "コスモス",
    "セイムス",
    "サツドラ",
    "GENKY",
    "ゲンキー",
    "薬王堂",
    "ココカラ",
    "ダイコク",
    "カワチ",
    "アオキ",
    "クリエイトSD",
    "クリエイト・エス・ディー",
    "ハックドラッグ",
    "トモズ",
    "キリン堂",
    "スギ薬局",
    "スギドラッグ",
    "杏林堂",
    "キョーリン",
    "ドラッグストアモリ",
    "ドラッグヤマザワ",
    "アークドラッグ",
    "イオンドラッグ",
    "サンドラッグ",
]


def normalize_company(company: str, store_name: str = "") -> str:
    derived = normalize_chain_name(store_name or "")
    if derived != "不明":
        return CHAIN_NORMALIZE.get(derived, derived)

    company_norm = CHAIN_NORMALIZE.get(company or "", company or "")
    if company_norm in KNOWN_CHAIN_NAMES and store_name:
        aliases = {company_norm}
        for src, dst in CHAIN_NORMALIZE.items():
            if dst == company_norm or src == company_norm:
                aliases.add(src)
                aliases.add(dst)
        if not any(a and a in store_name for a in aliases):
            # 誤ラベルの可能性が高い
            return "不明"
    return company_norm or "不明"


def address_key(address: str) -> str:
    a = re.sub(r"\s+", "", address or "")
    a = re.sub(r"[０-９]", lambda m: chr(ord(m.group()) - 0xFEE0), a)
    return a


def is_noise_store(store_name: str) -> bool:
    name = store_name or ""
    return any(kw in name for kw in NOISE_NAME_KEYWORDS)


def company_name_matches_store(company: str, store_name: str) -> bool:
    """曖昧なチェーン名は必須パターンでのみ採用。"""
    name = store_name or ""
    if company in CHAIN_NAME_REQUIRED_PATTERNS:
        return any(p in name for p in CHAIN_NAME_REQUIRED_PATTERNS[company])
    if company == "不明" or not company:
        return True
    aliases = {company}
    for src, dst in CHAIN_NORMALIZE.items():
        if dst == company or src == company:
            aliases.add(src)
            aliases.add(dst)
    return any(a and a in name for a in aliases)


def looks_like_drugstore(store_name: str, company: str) -> bool:
    if company in KNOWN_CHAIN_NAMES and company != "不明":
        if not company_name_matches_store(company, store_name):
            return False
        return True
    text = f"{company} {store_name}"
    return any(h in text for h in DRUGSTORE_HINTS)


def clean_stores(df: pd.DataFrame, prefecture: str) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["company"] = [
        normalize_company(c, n) for c, n in zip(df.get("company", ""), df.get("store_name", ""))
    ]

    other_prefs = [
        p for p in [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
        ]
        if p != prefecture
    ]

    def _repair_address(addr: str) -> str:
        a = normalize_address(addr or "", prefecture)
        # 過去データで「宮城県岐阜県…」となっていたものを復元
        for p in other_prefs:
            if a.startswith(prefecture + p):
                return a[len(prefecture) :]
        return a

    df["address"] = df["address"].apply(_repair_address)
    before = len(df)
    df = df[df["address"].str.startswith(prefecture, na=False)]
    # 対象県以外の都道府県名を含む住所は除外
    other_pat = "|".join(map(re.escape, other_prefs))
    df = df[~df["address"].str.contains(other_pat, na=False)]
    print(f"  住所フィルタ: {before - len(df)}件除外")

    before = len(df)
    # 品質基準: 店舗名に「薬局」「調剤」を含むものは除外
    strict_pharmacy = df["store_name"].str.contains("薬局|調剤", na=False)
    df = df[~strict_pharmacy]
    print(f"  薬局除外（厳格）: {before - len(df)}件")

    before = len(df)
    df = df[~df["store_name"].apply(is_pharmacy_only)]
    print(f"  薬局除外（追加）: {before - len(df)}件")

    before = len(df)
    df = df[~df["store_name"].apply(is_noise_store)]
    print(f"  ノイズ除外: {before - len(df)}件")

    before = len(df)
    df = df[df.apply(lambda r: looks_like_drugstore(str(r["store_name"]), str(r["company"])), axis=1)]
    print(f"  非ドラッグストア除外: {before - len(df)}件")

    # チェーン精査の誤ラベル修正: 店舗名から再判定した会社名を優先
    df["company"] = [
        normalize_company(c, n) for c, n in zip(df["company"], df["store_name"])
    ]

    if "place_id" in df.columns:
        df = df.drop_duplicates(subset=["place_id"], keep="first")
    df = df.drop_duplicates(subset=["company", "address"], keep="first")
    df = df.drop_duplicates(subset=["store_name", "address"], keep="first")

    # 同一チェーンで店舗名の表記ゆれ重複を除去
    def _norm_store(n: str) -> str:
        s = re.sub(r"\s+", "", str(n))
        s = s.replace("店", "")
        return s

    before = len(df)
    df["_norm_store"] = df["store_name"].map(_norm_store)
    df = df.drop_duplicates(subset=["company", "_norm_store"], keep="first")
    df = df.drop(columns=["_norm_store"])
    print(f"  店舗名正規化重複: {before - len(df)}件削除")

    # 同一住所で薬局系とドラッグストア系が混在 → ドラッグストア優先
    # 異チェーン同一住所は両方残す
    groups = {}
    for idx, row in df.iterrows():
        key = address_key(row["address"])
        groups.setdefault(key, []).append(idx)

    drop_indices = []
    for key, indices in groups.items():
        if len(indices) <= 1:
            continue
        rows = [(i, df.loc[i]) for i in indices]
        drugstore_rows = [r for r in rows if not is_pharmacy_only(r[1]["store_name"])]
        by_company = {}
        for i, r in drugstore_rows or rows:
            # 同一住所で既知チェーンと「不明」が混在する場合は既知を優先
            if r["company"] == "不明" and any(
                x[1]["company"] in KNOWN_CHAIN_NAMES for x in (drugstore_rows or rows)
            ):
                drop_indices.append(i)
                continue
            by_company.setdefault(r["company"], i)
        keep_set = set(by_company.values())
        for i, _ in rows:
            if i not in keep_set and i not in drop_indices:
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
    cleaned = clean_stores(df, cfg["name"])
    cleaned.to_csv(paths["final_csv"], index=False, encoding="utf-8-sig")
    print(f"最終データ: {paths['final_csv']} ({len(cleaned)}件)")
    return cleaned


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    clean_for_prefecture(slug)

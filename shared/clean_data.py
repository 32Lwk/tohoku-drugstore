"""データクリーニング・重複削除・薬局除外"""

import re

import pandas as pd

from shared.config import CHAIN_NORMALIZE, PREFECTURES
from shared.utils import ensure_dirs, is_pharmacy_only, normalize_address


def normalize_company(company: str) -> str:
    return CHAIN_NORMALIZE.get(company, company)


def address_key(address: str) -> str:
    a = re.sub(r"\s+", "", address or "")
    a = re.sub(r"[０-９]", lambda m: chr(ord(m.group()) - 0xFEE0), a)
    return a


def clean_stores(df: pd.DataFrame, prefecture: str) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["company"] = df["company"].apply(normalize_company)
    df["address"] = df["address"].apply(lambda a: normalize_address(a, prefecture))
    # 他県住所や正規化失敗（空）を除外
    before = len(df)
    df = df[df["address"].str.len() > 0]
    df = df[df["address"].str.contains(prefecture, na=False)]
    print(f"  住所フィルタ: {before - len(df)}件除外")

    before = len(df)
    strict_pharmacy = df["store_name"].str.contains("薬局|調剤", na=False)
    df = df[~strict_pharmacy]
    print(f"  薬局除外（厳格）: {before - len(df)}件")

    before = len(df)
    df = df[~df["store_name"].apply(is_pharmacy_only)]
    print(f"  薬局除外（追加）: {before - len(df)}件")

    # チェーン不明かつドラッグストアらしき名称でないものを除外
    ds_name = df["store_name"].str.contains(
        r"ドラッグ|Drug|DRUG|ウエルシア|Welcia|GENKY|ゲンキー|マツモトキヨシ|コスモス|セイムス|サツドラ|クリエイト",
        na=False,
        regex=True,
    )
    known_company = df["company"].fillna("").ne("") & df["company"].ne("不明")
    before = len(df)
    df = df[known_company | ds_name]
    print(f"  非DS除外（チェーン不明）: {before - len(df)}件")

    df = df.drop_duplicates(subset=["place_id"], keep="first")
    df = df.drop_duplicates(subset=["company", "address"], keep="first")

    # 同一住所で薬局系とドラッグストア系が混在 → ドラッグストアのみ残す
    # 異なるチェーン同一住所は残す
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
        pharmacy_rows = [r for r in rows if is_pharmacy_only(r[1]["store_name"])]
        if drugstore_rows and pharmacy_rows:
            for i, _ in pharmacy_rows:
                drop_indices.append(i)

    if drop_indices:
        df = df.drop(index=drop_indices)
        print(f"  同一住所の薬局優先除外: {len(drop_indices)}件削除")

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

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
    df = df[df["address"].str.contains(prefecture, na=False)]

    before = len(df)
    # 例外: チェーン名に薬局を含む正規ドラッグストア（スギ薬局等）は is_pharmacy_only で残す
    from shared.utils import is_pharmacy_only

    pharmacy_mask = df["store_name"].apply(is_pharmacy_only)
    df = df[~pharmacy_mask]
    print(f"  薬局除外: {before - len(df)}件")

    # ドラッグストアらしさフィルタ（既知チェーン or 店名にドラッグ）
    from shared.config import CHAIN_NORMALIZE, KNOWN_CHAINS

    known = set(CHAIN_NORMALIZE.values()) | {
        CHAIN_NORMALIZE.get(c, c) for c in KNOWN_CHAINS
    }
    known |= {"ハッピードラッグ", "サンドラッグ", "その他"}

    def is_drugstore_like(row) -> bool:
        name = str(row.get("store_name", ""))
        company = str(row.get("company", ""))
        if company == "コスモス":
            return any(k in name for k in ("ドラッグ", "Drug", "薬局", "コスモス薬品"))
        if company in known and company not in ("その他", "コスモス"):
            return True
        if any(k in name for k in ("ドラッグ", "Drug", "DRUG")):
            return True
        return False

    before = len(df)
    df = df[df.apply(is_drugstore_like, axis=1)]
    print(f"  非DS除外: {before - len(df)}件")

    df = df.drop_duplicates(subset=["place_id"], keep="first") if "place_id" in df.columns else df
    df = df.drop_duplicates(subset=["company", "address"], keep="first")

    # 同一住所で薬局系とドラッグストア系が混在 → ドラッグストア優先
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
        if drugstore_rows:
            keep = drugstore_rows[0][0]
            for i, _ in rows:
                if i != keep:
                    drop_indices.append(i)

    if drop_indices:
        df = df.drop(index=drop_indices)
        print(f"  同一住所重複整理: {len(drop_indices)}件削除")

    df = df.sort_values(["company", "store_name"]).reset_index(drop=True)
    cols = [c for c in ["company", "store_name", "address"] if c in df.columns]
    return df[cols]


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

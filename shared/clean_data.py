"""データクリーニング・重複削除・薬局除外"""

import re
import unicodedata

import pandas as pd

from shared.config import CHAIN_NORMALIZE, KNOWN_CHAINS, PREFECTURES
from shared.utils import ensure_dirs, is_pharmacy_only, normalize_address


def normalize_company(company: str) -> str:
    return CHAIN_NORMALIZE.get(company, company)


def address_key(address: str) -> str:
    a = unicodedata.normalize("NFKC", address or "")
    a = re.sub(r"\s+", "", a)
    a = a.replace("丁目", "-").replace("番", "-").replace("号", "")
    a = re.sub(r"-{2,}", "-", a)
    return a


def store_name_key(name: str) -> str:
    n = unicodedata.normalize("NFKC", name or "")
    n = re.sub(r"\s+", "", n)
    n = n.replace("・", "").replace("･", "")
    n = re.sub(r"ハッピー.?ドラッグ", "ハッピードラッグ", n)
    n = re.sub(r"ツルハ.?ドラッグ", "ツルハドラッグ", n)
    # 店内併設の別業態を除去して本体名に寄せる
    n = re.sub(r"^(Can★Do|キャンドゥ)", "", n)
    return n


def is_valid_chain_store(row) -> bool:
    """誤ヒットチェーン・併設店・住所不正を除外。"""
    name = str(row.get("store_name", ""))
    company = str(row.get("company", ""))
    address = str(row.get("address", ""))

    if len(address) < 12:
        return False

    # 100円ショップ等の併設店
    if re.search(r"Can★Do|キャンドゥ|cando", name, re.I):
        return False

    # 調剤専門（スーパードラッグアサヒ調剤薬局 等）
    if "調剤" in name and "ドラッグ" not in name.replace("調剤", ""):
        return False
    if re.search(r"調剤薬局", name) and not re.search(r"ドラッグ", name):
        return False
    # 「スーパードラッグ〜調剤薬局」は除外（調剤併記）
    if "調剤薬局" in name:
        return False

    ambiguous = {
        "クリエイト": ("ドラッグ", "エス・ディー", "エスディー", "SD", "クリエイトSD"),
        "コスモス": ("ドラッグ", "薬局", "コスモス薬品"),
        "クスリのアオキ": ("クスリのアオキ", "くすりのアオキ", "薬のアオキ"),
        "ココカラファイン": ("ココカラファイン", "ココカラ"),
        "キリン堂": ("キリン堂",),
        "ウエルシア": ("ウエルシア", "ウェルシア"),
        "スギ薬局": ("スギ薬局", "スギドラッグ"),
        "ドラッグスギヤマ": ("スギヤマ",),
    }
    if company in ambiguous:
        keys = ambiguous[company]
        if company == "ココカラファイン" and name.strip() in ("ココカラ", "ここから"):
            return False
        if not any(k in name for k in keys):
            return False
        # スギヤマ工場等
        if company == "スギ薬局" and "スギヤマ" in name and "ドラッグ" not in name:
            return False
        # くすりのキリン堂（個人薬局）はドラッグなしなら除外
        if company == "キリン堂" and "ドラッグ" not in name and "キリン堂" in name and name.startswith("くすり"):
            return False

    return True


def is_drugstore_like(row) -> bool:
    name = str(row.get("store_name", ""))
    company = str(row.get("company", ""))
    known = set(CHAIN_NORMALIZE.values()) | {CHAIN_NORMALIZE.get(c, c) for c in KNOWN_CHAINS}
    known |= {"ハッピードラッグ", "サンドラッグ", "その他", "スーパードラッグアサヒ"}

    if company == "コスモス":
        return any(k in name for k in ("ドラッグ", "Drug", "薬局", "コスモス薬品"))
    if company == "クリエイト":
        return any(k in name for k in ("ドラッグ", "エス・ディー", "SD"))
    if company in known and company not in ("その他", "コスモス", "クリエイト"):
        return True
    if any(k in name for k in ("ドラッグ", "Drug", "DRUG")):
        return True
    return False


def clean_stores(df: pd.DataFrame, prefecture: str) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["company"] = df["company"].apply(normalize_company)
    # スーパードラッグアサヒをチェーン化
    mask_asahi = df["store_name"].astype(str).str.contains("スーパードラッグアサヒ|メガドラッグ", na=False)
    df.loc[mask_asahi, "company"] = "スーパードラッグアサヒ"
    mask_you = df["store_name"].astype(str).str.contains("ドラッグ・ユー|ドラッグユー", na=False)
    df.loc[mask_you, "company"] = "ドラッグ・ユー"

    df["address"] = df["address"].apply(lambda a: normalize_address(a, prefecture))
    df = df[df["address"].str.contains(prefecture, na=False)]

    before = len(df)
    # 店舗名に「薬局」「調剤」を含むものは除外（チェーン例外なし）
    strict = df["store_name"].astype(str).str.contains(r"薬局|調剤", na=False)
    df = df[~strict]
    print(f"  薬局除外: {before - len(df)}件")

    before = len(df)
    df = df[df.apply(is_drugstore_like, axis=1)]
    print(f"  非DS除外: {before - len(df)}件")

    before = len(df)
    df = df[df.apply(is_valid_chain_store, axis=1)]
    print(f"  誤ヒット/併設除外: {before - len(df)}件")

    if "place_id" in df.columns:
        df = df.drop_duplicates(subset=["place_id"], keep="first")

    # 住所正規化キーで重複削除
    df["_addr_key"] = df["address"].apply(address_key)
    df = df.drop_duplicates(subset=["company", "_addr_key"], keep="first")

    # 店舗名キーで重複削除（全角半角表記ゆれ）
    df["_name_key"] = df["store_name"].apply(store_name_key)
    before = len(df)
    df = df.drop_duplicates(subset=["company", "_name_key"], keep="first")
    print(f"  店名表記ゆれ重複: {before - len(df)}件削除")

    # 同一住所で複数件 → 先頭を残す（異チェーンは別会社なので company 込みキー済み）
    # 異チェーン同一住所は残す
    groups = {}
    for idx, row in df.iterrows():
        key = row["_addr_key"]
        groups.setdefault(key, []).append(idx)

    drop_indices = []
    for key, indices in groups.items():
        if len(indices) <= 1:
            continue
        rows = [(i, df.loc[i]) for i in indices]
        # 同一会社のみ追加整理
        by_company: dict[str, list] = {}
        for i, r in rows:
            by_company.setdefault(r["company"], []).append(i)
        for comp, idxs in by_company.items():
            for extra in idxs[1:]:
                drop_indices.append(extra)

    if drop_indices:
        df = df.drop(index=drop_indices)
        print(f"  同一住所同一チェーン整理: {len(drop_indices)}件削除")

    df = df.drop(columns=[c for c in ["_addr_key", "_name_key"] if c in df.columns])
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

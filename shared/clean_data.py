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

    from shared.utils import address_in_prefecture, normalize_chain_name

    df = df.copy()
    # 店舗名からチェーンを再判定（過去の誤ラベルを訂正）
    if "store_name" in df.columns:
        df["company"] = df.apply(
            lambda r: normalize_chain_name(r.get("store_name", ""))
            if normalize_chain_name(r.get("store_name", "")) not in ("その他", "不明")
            else normalize_company(r.get("company", "")),
            axis=1,
        )
    df["company"] = df["company"].apply(normalize_company)
    df["address"] = df["address"].apply(lambda a: normalize_address(a, prefecture))
    before = len(df)
    df = df[df["address"].apply(lambda a: address_in_prefecture(a, prefecture))]
    print(f"  他県住所除外: {before - len(df)}件")

    before = len(df)
    strict_pharmacy = df["store_name"].str.contains("薬局|調剤", na=False)
    # スギ薬局などDSチェーン名に「薬局」を含む例外
    ds_exception = df["store_name"].str.contains(
        "スギ薬局|スギドラッグ|カワチ薬品|薬局マツモトキヨシ", na=False
    )
    df = df[~(strict_pharmacy & ~ds_exception)]
    print(f"  薬局除外（厳格）: {before - len(df)}件")

    before = len(df)
    df = df[~df["store_name"].apply(is_pharmacy_only)]
    print(f"  薬局除外（追加）: {before - len(df)}件")

    # 曖昧チェーンは店名がドラッグ系でない限り除外
    ambiguous = {
        "コスモス": r"ドラッグ|薬品|薬局",
        "クリエイト": r"クリエイトエス|クリエイトS|Create",
        "クリエイトエス・ディー": r"クリエイトエス|クリエイトS|Create",
        "スギ薬局": r"スギ薬局|スギドラッグ",
        "杏林堂": r"杏林堂ドラッグ|ドラッグストア杏林堂|杏林堂薬品",
        "クスリのアオキ": r"クスリのアオキ",
        "GENKY": r"GENKY|ゲンキー",
    }
    for company, pattern in ambiguous.items():
        mask = df["company"] == company
        if mask.any():
            before = len(df)
            keep = df["store_name"].str.contains(pattern, na=False, case=False)
            df = df[~(mask & ~keep)]
            print(f"  曖昧チェーン除外({company}): {before - len(df)}件")

    # 非店舗・併設ノイズ
    before = len(df)
    noise = df["store_name"].str.contains(
        r"駐車場|理容|美容|ヘア|サロン|鍼灸|治療所|カイロ|神社|公衆トイレ|"
        r"処方せん受付|処方箋受付|ワッツ|スーパーのアオキ|グループホーム|"
        r"訪問|きっず|アトリエ|メゾン|セジュール|ハイツ",
        na=False,
    )
    df = df[~noise]
    print(f"  非店舗ノイズ除外: {before - len(df)}件")

    # 「その他」はドラッグ/くすり系店名のみ残す
    before = len(df)
    other_mask = df["company"].isin(["その他", "不明"])
    drug_hint = df["store_name"].str.contains(
        "ドラッグ|Drug|DRUG|くすり|クスリ|薬王堂|サンドラッグ", na=False, case=False
    )
    df = df[~(other_mask & ~drug_hint)]
    print(f"  その他ノイズ除外: {before - len(df)}件")

    if "place_id" in df.columns:
        df = df.drop_duplicates(subset=["place_id"], keep="first")
    df = df.drop_duplicates(subset=["company", "address"], keep="first")
    # 同一チェーン・同一店舗名は住所表記ゆれでも1件に
    before = len(df)
    df = df.drop_duplicates(subset=["company", "store_name"], keep="first")
    print(f"  店舗名重複除外: {before - len(df)}件")

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

    # 県の概ねの緯度経度範囲外を除外（誤ジオコード）
    if "latitude" in df.columns and "longitude" in df.columns:
        from shared.config import PREFECTURES

        # 東北6県の粗い bbox（県ごとの精密は不要、明らかな外れ値除去）
        bbox = {
            "青森県": (40.2, 41.6, 139.5, 141.8),
            "岩手県": (38.7, 40.5, 140.6, 142.1),
            "宮城県": (37.7, 39.1, 140.2, 141.8),
            "秋田県": (38.8, 40.6, 139.5, 141.0),
            "山形県": (37.7, 39.2, 139.4, 140.7),
            "福島県": (36.8, 38.0, 139.1, 141.1),
        }
        # prefecture name from first address
        pref_name = prefecture
        if pref_name in bbox:
            lat_min, lat_max, lon_min, lon_max = bbox[pref_name]
            before = len(df)
            has_coord = df["latitude"].notna() & df["longitude"].notna()
            in_box = (
                df["latitude"].between(lat_min, lat_max)
                & df["longitude"].between(lon_min, lon_max)
            )
            df = df[~has_coord | in_box]
            print(f"  座標範囲外除外: {before - len(df)}件")

    df = df.sort_values(["company", "store_name"]).reset_index(drop=True)
    cols = ["company", "store_name", "address"]
    for optional in ("place_id", "latitude", "longitude", "source"):
        if optional in df.columns:
            cols.append(optional)
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

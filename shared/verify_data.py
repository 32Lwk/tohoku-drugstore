"""二次調査・整合性チェック（公式サイトとの突合）"""

import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from shared.config import PREFECTURES
from shared.utils import ensure_dirs, normalize_address

# 公式店舗検索URL（取得可能なチェーン）
CHAIN_OFFICIAL_URLS = {
    "GENKY": "https://www.genky.co.jp/store/",
    "ウエルシア": "https://store.welcia.co.jp/welcia/",
    "ツルハドラッグ": "https://www.tsuruha.co.jp/shop/",
    "コスモス": "https://www.cosmospc.co.jp/shop/",
}


def verify_genky(prefecture: str) -> list[dict]:
    stores = []
    try:
        resp = requests.get(CHAIN_OFFICIAL_URLS["GENKY"], timeout=30)
        soup = BeautifulSoup(resp.content, "lxml")
        for item in soup.select(".shop-list li, .store-item, tr"):
            text = item.get_text()
            if prefecture.replace("県", "") in text or prefecture in text:
                stores.append({"company": "GENKY", "source": "official", "text": text[:100]})
    except Exception as e:
        print(f"  GENKY公式取得失敗: {e}")
    return stores


def cross_validate(slug: str) -> dict:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    df = pd.read_csv(paths["coord_csv"], encoding="utf-8-sig")

    report = {
        "prefecture": cfg["name"],
        "total": len(df),
        "missing_coords": int(df["latitude"].isna().sum()),
        "duplicate_addresses": 0,
        "pharmacy_leak": 0,
        "chain_coverage": {},
    }

    addr_counts = df["address"].value_counts()
    report["duplicate_addresses"] = int((addr_counts > 1).sum())

    pharmacy_pattern = re.compile(r"薬局|調剤")
    report["pharmacy_leak"] = int(df["store_name"].str.contains(pharmacy_pattern, na=False).sum())

    for chain, count in df["company"].value_counts().items():
        report["chain_coverage"][chain] = int(count)

    out = paths["data"] / "validation_report.json"
    import json

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  検証レポート: {out}")
    return report


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    cross_validate(slug)

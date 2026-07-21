"""公式サイトからの二次調査（Google Places 補完）"""

import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from shared.config import KNOWN_CHAINS, PREFECTURES
from shared.utils import ensure_dirs, normalize_address, normalize_chain_name

CHAIN_SCRAPERS = {
    "GENKY": {
        "url": "https://www.genky.co.jp/store/",
        "company": "GENKY",
    },
    "ウエルシア": {
        "url": "https://store.welcia.co.jp/welcia/",
        "company": "ウエルシア",
    },
    "ツルハドラッグ": {
        "url": "https://www.tsuruha.co.jp/shop/",
        "company": "ツルハドラッグ",
    },
    "コスモス": {
        "url": "https://www.cosmospc.co.jp/shop/",
        "company": "コスモス",
    },
}


def _extract_addresses_from_html(html: str, prefecture: str, company: str) -> list[dict]:
    stores = []
    pref_short = prefecture.replace("県", "")

    patterns = [
        rf"({prefecture}[^、<\n]{{5,80}}?(?:市|区|町|村)[^、<\n]{{0,60}})",
        rf"({pref_short}[^、<\n]{{5,80}}?(?:市|区|町|村)[^、<\n]{{0,60}})",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html):
            addr = normalize_address(match.group(1).strip(), prefecture)
            if prefecture in addr and len(addr) > 8:
                stores.append({
                    "company": company,
                    "store_name": f"{company}（公式サイト）",
                    "address": addr,
                    "place_id": "",
                    "latitude": None,
                    "longitude": None,
                    "source": "official_site",
                })

    seen = set()
    unique = []
    for s in stores:
        key = s["address"]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def scrape_official_sites(slug: str) -> list[dict]:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    all_stores = []

    for name, info in CHAIN_SCRAPERS.items():
        try:
            print(f"    公式サイト: {name}")
            resp = requests.get(
                info["url"],
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TohokuDrugstoreBot/1.0)"},
            )
            if resp.status_code != 200:
                print(f"      HTTP {resp.status_code}")
                continue

            batch = _extract_addresses_from_html(resp.text, prefecture, info["company"])
            all_stores.extend(batch)
            print(f"      +{len(batch)}件")
            time.sleep(0.5)
        except Exception as e:
            print(f"      失敗 ({e})")

    return all_stores


def merge_official_into_raw(slug: str) -> int:
    paths = ensure_dirs(slug)
    if not paths["raw_csv"].exists():
        return 0

    df = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
    existing_addrs = set(df["address"].tolist()) if "address" in df.columns else set()
    existing_ids = set(df["place_id"].dropna().tolist()) if "place_id" in df.columns else set()

    official = scrape_official_sites(slug)
    added = 0
    new_rows = []

    for store in official:
        if store["address"] in existing_addrs:
            continue
        pid = store.get("place_id")
        if pid and pid in existing_ids:
            continue
        new_rows.append(store)
        existing_addrs.add(store["address"])
        added += 1

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")

    print(f"  公式サイト追加分: +{added}件 (合計{len(df)}件)")
    return added


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    merge_official_into_raw(slug)

"""Playwright で各チェーン公式サイトから青森県店舗を取得"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

PREF = "青森県"
OUT = Path(__file__).resolve().parent.parent / "prefectures" / "01_青森県" / "data" / "extra_chains.json"


def extract_aomori_from_text(text: str) -> list[dict]:
    stores = []
    seen = set()
    for m in re.finditer(rf"({PREF}[^\n\"'<>]{{8,120}}?(?:市|区|町|村)[^\n\"'<>]{{0,80}})", text):
        addr = re.sub(r"\s+", " ", m.group(1)).strip()
        addr = re.sub(r"(TEL|電話|営業|FAX|〒).*", "", addr).strip()
        if len(addr) < 12 or addr in seen:
            continue
        seen.add(addr)
        stores.append({"address": addr})
    return stores


def scrape_with_playwright() -> dict:
    results: dict[str, list] = {}

    targets = [
        (
            "マツモトキヨシ",
            [
                "https://www.matsukiyococokara-online.com/store/search?prefectureCode=02",
                "https://www.matsukiyococokara-online.com/store/search?prefecture=2",
                "https://www.matsukiyococokara-online.com/store",
            ],
        ),
        (
            "サンドラッグ",
            [
                "https://www.sundrug.co.jp/store/",
                "https://www.sundrug.co.jp/shop/store/",
                "https://www.sundrug.co.jp/shop/shop.php",
            ],
        ),
        (
            "スーパードラッグアサヒ",
            [
                "https://www.sda.co.jp/shop/list.php",
                "https://www.sda.co.jp/store/",
                "https://www.sda.co.jp/company/shop/",
            ],
        ),
        (
            "クスリのアオキ",
            [
                "https://www.kusuri-aoki.co.jp/shop/",
                "https://www.aoki-pharmacy.co.jp/shop/",
                "https://kusuri-aoki.jp/shop/",
            ],
        ),
        (
            "セイムス",
            ["https://www.seims.co.jp/shop/", "https://www.seims.jp/shop/"],
        ),
        (
            "コスモス",
            [
                "https://www.cosmospc.co.jp/shop/search?pref=02",
                "https://www.cosmospc.co.jp/shop/",
            ],
        ),
        (
            "GENKY",
            [
                "https://www.genky.co.jp/store/",
                "http://www.genky.co.jp/store/list.php",
            ],
        ),
        (
            "カワチ薬品",
            ["https://www.kawachi.co.jp/shop/", "https://www.kawachi.co.jp/store/"],
        ),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
        )

        for chain, urls in targets:
            chain_stores: list[dict] = []
            for url in urls:
                try:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3000)
                    # 都道府県フィルタ操作を試行
                    for sel in [
                        "select[name*='pref']",
                        "select[id*='pref']",
                        "option:has-text('青森')",
                    ]:
                        try:
                            if "option" in sel:
                                page.locator(sel).first.click(timeout=2000)
                            else:
                                page.select_option(sel, label=PREF, timeout=2000)
                            page.wait_for_timeout(2000)
                            break
                        except Exception:
                            pass
                    text = page.content()
                    found = extract_aomori_from_text(text)
                    if found:
                        print(f"  {chain} @ {url}: {len(found)}件")
                        chain_stores.extend(found)
                    page.close()
                except Exception as e:
                    print(f"  {chain} @ {url} 失敗: {e}")
                    try:
                        page.close()
                    except Exception:
                        pass
            if chain_stores:
                results[chain] = chain_stores

        browser.close()
    return results


if __name__ == "__main__":
    print("Playwright スクレイピング開始...")
    data = scrape_with_playwright()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存: {OUT}")
    for chain, stores in data.items():
        print(f"  {chain}: {len(stores)}件")

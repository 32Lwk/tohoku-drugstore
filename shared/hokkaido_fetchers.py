"""北海道地域別 fetcher（Places API 不使用）"""

from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from shared.collect_official_only import (
    HEADERS,
    _store,
    dedupe_stores,
    fetch_aoki,
    fetch_cosmos,
    fetch_kawachi,
    fetch_matsukiyo,
    fetch_satsudora,
    fetch_sundrag,
    fetch_welcia,
)
from shared.fetch_official_stores import fetch_tsuruha_yext
from shared.hokkaido_regions import PREFECTURE, filter_stores_for_region
from shared.utils import normalize_address

HOKKAIDO_PREF_PARAM = "01"
HOKKAIDO_MATSUKIYO_CODE = "1"


def fetch_sapporo_drug() -> list[dict]:
    return fetch_satsudora(PREFECTURE)


def fetch_kusuri_kodama() -> list[dict]:
    stores: list[dict] = []
    urls = [
        "https://www.kusuri-kodama.co.jp/shop/",
        "https://www.kusuri-kodama.co.jp/store/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text("\n", strip=True)
            for m in re.finditer(rf"({PREFECTURE}[^\n]{{8,100}})", text):
                addr = normalize_address(m.group(1), PREFECTURE)
                if len(addr) > 12:
                    stores.append(_store("クスリのコダマ", "クスリのコダマ", addr, "official_kusuri_kodama", PREFECTURE))
        except Exception as e:
            print(f"    クスリのコダマ {url} 失敗: {e}")
    return stores


def fetch_drug_eleven() -> list[dict]:
    stores: list[dict] = []
    try:
        resp = requests.get("https://www.drug11.jp/shop/", headers=HEADERS, timeout=60)
        if resp.status_code != 200:
            return stores
        for m in re.finditer(rf"({PREFECTURE}[^<\n\"']{{8,120}})", resp.text):
            addr = normalize_address(m.group(1), PREFECTURE)
            stores.append(_store("ドラッグイレブン", "ドラッグイレブン", addr, "official_drug11", PREFECTURE))
    except Exception as e:
        print(f"    ドラッグイレブン 失敗: {e}")
    return stores


def fetch_kirin_do() -> list[dict]:
    stores: list[dict] = []
    try:
        resp = requests.get("https://www.kirindo.co.jp/shop/list/", headers=HEADERS, timeout=60)
        if resp.status_code != 200:
            return stores
        for m in re.finditer(rf"({PREFECTURE}[^<\n\"']{{8,120}})", resp.text):
            addr = normalize_address(m.group(1), PREFECTURE)
            stores.append(_store("キリン堂", "キリン堂", addr, "official_kirindo", PREFECTURE))
    except Exception as e:
        print(f"    キリン堂 失敗: {e}")
    return stores


def fetch_cosmos_hokkaido() -> list[dict]:
    stores: list[dict] = []
    urls = [
        f"https://www.cosmospc.co.jp/shop/search?pref={HOKKAIDO_PREF_PARAM}",
        "https://www.cosmospc.co.jp/shop/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=45)
            if resp.status_code != 200:
                continue
            for m in re.finditer(rf"({PREFECTURE}[^<\n\"']{{8,100}})", resp.text):
                addr = normalize_address(m.group(1), PREFECTURE)
                if len(addr) > 12:
                    stores.append(_store("コスモス", "コスモス", addr, "official_cosmos", PREFECTURE))
        except Exception as e:
            print(f"    コスモス 失敗: {e}")
    return stores


def fetch_matsukiyo_hokkaido() -> list[dict]:
    stores: list[dict] = []
    try:
        resp = requests.get(
            f"https://www.matsukiyococokara-online.com/store/list?prefecture={HOKKAIDO_MATSUKIYO_CODE}",
            headers=HEADERS,
            timeout=45,
        )
        if resp.status_code != 200:
            return stores
        soup = BeautifulSoup(resp.text, "html.parser")
        for block in soup.select("li, .store-item, tr"):
            text = block.get_text("\n", strip=True)
            if PREFECTURE not in text:
                continue
            m = re.search(rf"({PREFECTURE}[^\n]{{8,80}})", text)
            if m:
                name = "マツモトキヨシ"
                for line in text.split("\n"):
                    if "マツモト" in line or "マツキヨ" in line:
                        name = line.strip()
                        break
                stores.append(_store("マツモトキヨシ", name, m.group(1), "official_matsukiyo", PREFECTURE))
    except Exception as e:
        print(f"    マツキヨ 失敗: {e}")
    return stores


def fetch_all_hokkaido_sources(center: tuple[float, float]) -> list[dict]:
    """北海道全域の公式ソースから取得（地域フィルタ前）"""
    fetchers = [
        ("ツルハYext", lambda: fetch_tsuruha_yext(PREFECTURE, center, full_scan=True)),
        ("ウエルシアAPI", lambda: fetch_welcia(PREFECTURE)),
        ("サッポロドラッグ", fetch_sapporo_drug),
        ("クスリのコダマ", fetch_kusuri_kodama),
        ("ドラッグイレブン", fetch_drug_eleven),
        ("キリン堂", fetch_kirin_do),
        ("コスモス", fetch_cosmos_hokkaido),
        ("サンドラッグ", lambda: fetch_sundrag(PREFECTURE)),
        ("クスリのアオキ", lambda: fetch_aoki(PREFECTURE)),
        ("マツモトキヨシ", fetch_matsukiyo_hokkaido),
        ("カワチ薬品", lambda: fetch_kawachi(PREFECTURE)),
    ]
    all_stores: list[dict] = []
    for name, fn in fetchers:
        try:
            batch = dedupe_stores(fn())
            print(f"  [全域] {name}: {len(batch)}件")
            all_stores.extend(batch)
        except Exception as e:
            print(f"  [全域] {name} 失敗: {e}")
    return dedupe_stores(all_stores)


def fetch_gmaps_for_region(region_id: str, region_cfg: dict) -> list[dict]:
    """Playwright: Google Maps ブラウザ検索（Places API 不使用）"""
    from playwright.sync_api import sync_playwright

    stores: list[dict] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="ja-JP")

        def _batch(chain: str, query: str) -> None:
            nonlocal stores
            try:
                page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}", timeout=90000)
                page.wait_for_timeout(4000)
                try:
                    feed = page.locator('div[role="feed"]').first
                    for _ in range(15):
                        feed.evaluate("el => el.scrollTop += 400")
                        page.wait_for_timeout(800)
                except Exception:
                    pass
                for item in page.locator('a[href*="/maps/place"]').all()[:40]:
                    try:
                        label = (item.get_attribute("aria-label") or "").strip()
                        if not label:
                            continue
                        item.click(timeout=3000)
                        page.wait_for_timeout(1500)
                        body = page.inner_text("body")
                        m = re.search(rf"({PREFECTURE}[^\n]{{8,100}})", body)
                        if not m:
                            continue
                        addr = normalize_address(m.group(1).strip(), PREFECTURE)
                        if addr in seen or not filter_stores_for_region([{"address": addr}], region_id):
                            continue
                        seen.add(addr)
                        stores.append(_store(chain, label[:80], addr, "google_maps_browser", PREFECTURE))
                    except Exception:
                        continue
            except Exception as e:
                print(f"    gmaps {chain}/{query[:30]} 失敗: {e}")

        for chain, query in region_cfg.get("gmaps_queries", []):
            _batch(chain, query)
            time.sleep(1)

        for chain, prefix in region_cfg.get("city_gmaps", []):
            for city in region_cfg.get("municipalities", [])[:12]:
                if city.endswith("市") or city.endswith("町"):
                    _batch(chain, f"{prefix} {city}")
                    time.sleep(0.5)

        browser.close()
    return stores

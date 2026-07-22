"""追加チェーン取得 — drug-asahi / sundrug / matsukiyo / Google Maps browser"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from shared.fetch_official_stores import _make_place_id
from shared.utils import normalize_address, normalize_chain_name

PREF = "青森県"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}


def _store(company, name, address, source, lat=None, lon=None):
    company = normalize_chain_name(company)
    address = normalize_address(address, PREF)
    return {
        "company": company,
        "store_name": name or company,
        "address": address,
        "place_id": _make_place_id(source, company, address),
        "latitude": lat,
        "longitude": lon,
        "source": source,
    }


def fetch_drug_asahi() -> list[dict]:
    """スーパードラッグアサヒ — 番号付き店舗ページ"""
    stores = []
    seen = set()
    for i in range(1, 80):
        for url in [f"https://drug-asahi.co.jp/{i}ten.html", f"https://drug-asahi.co.jp/5{i}ten.html"]:
            try:
                r = requests.get(url, headers=HEADERS, timeout=20)
                if r.status_code != 200 or PREF not in r.text:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.find_all("tr")
                for row in rows:
                    cells = [c.get_text(strip=True) for c in row.find_all("td")]
                    text = " ".join(cells)
                    if PREF not in text:
                        continue
                    m = re.search(rf"({PREF}[^\s]{{8,120}})", text)
                    if not m:
                        continue
                    addr = re.sub(r"営業時間.*", "", m.group(1)).strip()
                    name = cells[1] if len(cells) >= 2 else "スーパードラッグアサヒ"
                    if addr in seen:
                        continue
                    seen.add(addr)
                    stores.append(_store("スーパードラッグアサヒ", f"スーパードラッグアサヒ {name}", addr, "official_drug_asahi"))
            except Exception:
                pass
    return stores


def fetch_sundrug_playwright() -> list[dict]:
    """サンドラッグ — sundrug-online 店舗検索"""
    stores = []
    seen = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://sundrug-online.com/tools/locations", timeout=90000)
            page.wait_for_timeout(5000)
            # 都道府県で検索
            for selector in ["input[placeholder*='検索']", "input[type='search']", "#search", "input"]:
                try:
                    inp = page.locator(selector).first
                    if inp.is_visible(timeout=2000):
                        inp.fill("青森")
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(4000)
                        break
                except Exception:
                    pass
            text = page.content()
            for m in re.finditer(rf"({PREF}[^<\"']{{8,100}})", text):
                addr = m.group(1).strip()
                if addr not in seen and len(addr) > 12:
                    seen.add(addr)
                    stores.append(_store("サンドラッグ", "サンドラッグ", addr, "official_sundrug_pw"))
        except Exception as e:
            print(f"  sundrug playwright: {e}")
        browser.close()
    return stores


def fetch_matsukiyo_playwright() -> list[dict]:
    """マツモトキヨシ — 公式店舗検索"""
    stores = []
    seen = set()
    urls = [
        "https://www.matsukiyococokara-online.com/store/search?prefectureCode=02",
        "https://mcoy.monogatari.co.jp/shop/search?prefecture=aomori",
        "https://www.matsukiyococokara-online.com/store/search",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for url in urls:
            try:
                page.goto(url, timeout=90000, wait_until="networkidle")
                page.wait_for_timeout(3000)
                # 青森選択
                try:
                    page.get_by_text("青森", exact=False).first.click(timeout=3000)
                    page.wait_for_timeout(3000)
                except Exception:
                    pass
                text = page.content()
                if PREF not in text:
                    continue
                soup = BeautifulSoup(text, "html.parser")
                for block in soup.find_all(["li", "div", "tr", "article"]):
                    t = block.get_text("\n", strip=True)
                    if PREF not in t or ("マツモト" not in t and "マツキヨ" not in t):
                        continue
                    m = re.search(rf"({PREF}[^\n]{{8,100}})", t)
                    if not m:
                        continue
                    addr = m.group(1).strip()
                    name = "マツモトキヨシ"
                    for line in t.split("\n"):
                        if "マツモト" in line or "マツキヨ" in line:
                            name = line.strip()[:60]
                            break
                    if addr not in seen:
                        seen.add(addr)
                        stores.append(_store("マツモトキヨシ", name, addr, "official_matsukiyo_pw"))
            except Exception as e:
                print(f"  matsukiyo {url}: {e}")
        browser.close()
    return stores


def fetch_google_maps_browser(chain: str, query: str, max_scroll: int = 5) -> list[dict]:
    """Google Maps ブラウザ検索（Places API 不使用）"""
    stores = []
    seen = set()
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="ja-JP")
        try:
            page.goto(search_url, timeout=90000)
            page.wait_for_timeout(5000)
            for _ in range(max_scroll):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(1500)
            text = page.content()
            # aria-label や結果テキストから住所抽出
            for m in re.finditer(rf"({PREF}[^<\"']{{8,100}}?(?:市|区|町|村)[^<\"']{{0,80}})", text):
                addr = re.sub(r"\s+", " ", m.group(1)).strip()
                if addr in seen or len(addr) < 15:
                    continue
                seen.add(addr)
                stores.append(_store(chain, chain, addr, "google_maps_browser"))
        except Exception as e:
            print(f"  gmaps {chain}: {e}")
        browser.close()
    return stores


def fetch_all_extra() -> dict[str, list]:
    results = {}

    print("スーパードラッグアサヒ...")
    sda = fetch_drug_asahi()
    print(f"  {len(sda)}件")
    if sda:
        results["スーパードラッグアサヒ"] = sda

    print("サンドラッグ (Playwright)...")
    sd = fetch_sundrug_playwright()
    print(f"  {len(sd)}件")
    if sd:
        results["サンドラッグ"] = sd

    print("マツモトキヨシ (Playwright)...")
    mk = fetch_matsukiyo_playwright()
    print(f"  {len(mk)}件")
    if mk:
        results["マツモトキヨシ"] = mk

    # Google Maps browser fallback for chains still missing
    gmaps_queries = [
        ("サンドラッグ", "サンドラッグ 青森県"),
        ("マツモトキヨシ", "マツモトキヨシ 青森県"),
        ("クスリのアオキ", "クスリのアオキ 青森県"),
        ("セイムス", "セイムス 青森県"),
        ("コスモス", "ドラッグストアコスモス 青森県"),
    ]
    for chain, query in gmaps_queries:
        if chain in results and len(results[chain]) >= 3:
            continue
        print(f"Google Maps: {query}...")
        batch = fetch_google_maps_browser(chain, query)
        print(f"  {len(batch)}件")
        if batch:
            existing = results.get(chain, [])
            addrs = {s["address"] for s in existing}
            for s in batch:
                if s["address"] not in addrs:
                    existing.append(s)
                    addrs.add(s["address"])
            results[chain] = existing

    return results


if __name__ == "__main__":
    data = fetch_all_extra()
    out = Path(__file__).resolve().parent.parent / "prefectures" / "01_青森県" / "data" / "extra_chains.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存: {out}")
    for k, v in data.items():
        print(f"  {k}: {len(v)}件")

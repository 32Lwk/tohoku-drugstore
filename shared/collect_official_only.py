"""Places API 不使用 — 公式サイト/API から店舗収集"""

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import requests
from bs4 import BeautifulSoup

from shared.config import PREFECTURES
from shared.fetch_official_stores import fetch_tsuruha_yext, fetch_welcia, _make_place_id
from shared.utils import ensure_dirs, normalize_address, normalize_chain_name

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}


def _store(
    company: str,
    name: str,
    address: str,
    source: str,
    prefecture: str,
    lat=None,
    lon=None,
) -> dict:
    company = normalize_chain_name(company)
    address = normalize_address(address, prefecture)
    return {
        "company": company,
        "store_name": name or company,
        "address": address,
        "place_id": _make_place_id(source, company, address),
        "latitude": lat,
        "longitude": lon,
        "source": source,
    }


# Playwright + Google Maps ブラウザ検索の県別設定
PLAYWRIGHT_PREF_CONFIG: dict[str, dict] = {
    "青森県": {
        "drug_asahi": True,
        "cities": [
            "青森市", "弘前市", "八戸市", "黒石市", "五所川原市", "十和田市",
            "三沢市", "むつ市", "つがる市", "平川市",
        ],
        "pref_queries": [
            ("マツモトキヨシ", "マツモトキヨシ 青森県"),
        ],
        "city_queries": [("サンドラッグ", "サンドラッグ")],
    },
    "福島県": {
        "drug_asahi": False,
        "cities": [
            "福島市", "郡山市", "いわき市", "会津若松市", "須賀川市", "白河市",
            "喜多方市", "相馬市", "二本松市", "田村市", "南相馬市", "伊達市",
        ],
        "pref_queries": [
            ("マツモトキヨシ", "マツモトキヨシ 福島県"),
            ("クスリのアオキ", "クスリのアオキ 福島県"),
            ("カワチ薬品", "カワチ薬品 福島県"),
            ("ハシドラッグ", "ハシドラッグ 福島県"),
            ("コスモス", "ドラッグストアコスモス 福島県"),
            ("Vドラッグ", "Vドラッグ 福島県"),
        ],
        "city_queries": [
            ("サンドラッグ", "サンドラッグ"),
            ("ココカラファイン", "ココカラファイン"),
        ],
    },
}


def fetch_yakuodo(prefecture: str) -> list[dict]:
    """薬王堂 店舗検索結果ページ（都道府県フィルタ）"""
    pref_slug_map = {
        "青森県": "aomori",
        "岩手県": "iwate",
        "宮城県": "miyagi",
        "秋田県": "akita",
        "山形県": "yamagata",
        "福島県": "fukushima",
    }
    pref_slug = pref_slug_map.get(prefecture)
    if not pref_slug:
        return []

    stores: list[dict] = []
    url = f"https://www.yakuodo.co.jp/shop/result/?pref={pref_slug}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for h in soup.find_all("h2"):
            name = h.get_text(strip=True)
            if not name or "該当店舗数" in name or name == "会社情報":
                continue
            addr_p = h.find_next("p", class_="address")
            if not addr_p:
                continue
            addr = re.sub(r"\s+", " ", addr_p.get_text(strip=True))
            addr = re.sub(r"^〒[0-9\-]+", "", addr).strip()
            if prefecture not in addr:
                continue
            store_name = f"薬王堂 {name}" if "薬王堂" not in name else name
            stores.append(_store("薬王堂", store_name, addr, "official_yakuodo", prefecture))
    except Exception as e:
        print(f"    薬王堂 失敗: {e}")
    return stores


def fetch_cosmos(prefecture: str) -> list[dict]:
    """コスモス 店舗一覧"""
    stores: list[dict] = []
    pref_param = {"青森県": "02", "岩手県": "03", "宮城県": "04", "秋田県": "05", "山形県": "06", "福島県": "07"}.get(
        prefecture, "02"
    )
    urls = [
        f"https://www.cosmospc.co.jp/shop/search?pref={pref_param}",
        "https://www.cosmospc.co.jp/shop/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=45)
            if resp.status_code != 200:
                continue
            for m in re.finditer(rf"({prefecture}[^<\n\"']{{8,100}})", resp.text):
                addr = normalize_address(m.group(1), prefecture)
                if len(addr) < 12:
                    continue
                stores.append(_store("コスモス", "コスモス", addr, "official_cosmos", prefecture))
        except Exception as e:
            print(f"    コスモス 失敗: {e}")
    return stores


def fetch_sundrag(prefecture: str) -> list[dict]:
    """サンドラッグ"""
    stores: list[dict] = []
    try:
        resp = requests.get("https://www.sundrug.co.jp/store/search.php", headers=HEADERS, timeout=45)
        if resp.status_code == 200:
            for m in re.finditer(rf"({prefecture}[^<\n\"']{{8,100}})", resp.text):
                addr = normalize_address(m.group(1), prefecture)
                stores.append(_store("サンドラッグ", "サンドラッグ", addr, "official_sundrag", prefecture))
    except Exception as e:
        print(f"    サンドラッグ 失敗: {e}")
    return stores


def fetch_aoki(prefecture: str) -> list[dict]:
    """クスリのアオキ"""
    stores: list[dict] = []
    try:
        resp = requests.get(
            "https://www.aoki-pharm.co.jp/shop/",
            headers=HEADERS,
            timeout=45,
        )
        if resp.status_code == 200:
            for m in re.finditer(rf"({prefecture}[^<\n\"']{{8,100}})", resp.text):
                addr = normalize_address(m.group(1), prefecture)
                stores.append(_store("クスリのアオキ", "クスリのアオキ", addr, "official_aoki", prefecture))
    except Exception as e:
        print(f"    アオキ 失敗: {e}")
    return stores


def fetch_matsukiyo(prefecture: str) -> list[dict]:
    """マツモトキヨシ"""
    stores: list[dict] = []
    pref_code = {"青森県": "2", "岩手県": "3", "宮城県": "4", "秋田県": "5", "山形県": "6", "福島県": "7"}.get(
        prefecture, "2"
    )
    try:
        resp = requests.get(
            f"https://www.matsukiyococokara-online.com/store/list?prefecture={pref_code}",
            headers=HEADERS,
            timeout=45,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for block in soup.select("li, .store-item, tr"):
                text = block.get_text("\n", strip=True)
                if prefecture not in text:
                    continue
                m = re.search(rf"({prefecture}[^\n]{{8,80}})", text)
                if m:
                    name = "マツモトキヨシ"
                    for line in text.split("\n"):
                        if "マツモト" in line or "マツキヨ" in line:
                            name = line.strip()
                            break
                    stores.append(_store("マツモトキヨシ", name, m.group(1), "official_matsukiyo", prefecture))
    except Exception as e:
        print(f"    マツキヨ 失敗: {e}")
    return stores


def fetch_seims(prefecture: str) -> list[dict]:
    """セイムス"""
    stores: list[dict] = []
    try:
        resp = requests.get("https://www.seims.co.jp/shop/", headers=HEADERS, timeout=45)
        if resp.status_code == 200:
            for m in re.finditer(rf"({prefecture}[^<\n\"']{{8,100}})", resp.text):
                stores.append(_store("セイムス", "セイムス", m.group(1), "official_seims", prefecture))
    except Exception as e:
        print(f"    セイムス 失敗: {e}")
    return stores


def fetch_genky(prefecture: str) -> list[dict]:
    """GENKY 店舗一覧ページ"""
    stores: list[dict] = []
    for page in range(12):
        try:
            url = f"https://www.genky.co.jp/store/list.php?page={page}"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                continue
            if prefecture not in resp.text:
                continue
            for m in re.finditer(rf"({prefecture}[^<\n\"']{{8,100}})", resp.text):
                stores.append(_store("GENKY", "GENKY", m.group(1), "official_genky", prefecture))
            time.sleep(0.3)
        except Exception as e:
            print(f"    GENKY page {page} 失敗: {e}")
    return stores


def fetch_kawachi(prefecture: str) -> list[dict]:
    """カワチ薬品"""
    stores: list[dict] = []
    try:
        resp = requests.get("https://www.kawachi.co.jp/shop/", headers=HEADERS, timeout=45)
        if resp.status_code == 200:
            for m in re.finditer(rf"({prefecture}[^<\n\"']{{8,100}})", resp.text):
                stores.append(_store("カワチ薬品", "カワチ薬品", m.group(1), "official_kawachi", prefecture))
    except Exception as e:
        print(f"    カワチ 失敗: {e}")
    return stores


def fetch_extra_chains_playwright(prefecture: str) -> list[dict]:
    """Playwright: drug-asahi 公式 + Google Maps ブラウザ検索"""
    from playwright.sync_api import sync_playwright

    cfg = PLAYWRIGHT_PREF_CONFIG.get(prefecture)
    if not cfg:
        return []

    stores: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="ja-JP")

        if cfg.get("drug_asahi"):
            try:
                page.goto("https://drug-asahi.co.jp/ten.html", timeout=60000)
                page.wait_for_timeout(4000)
                lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
                for i, line in enumerate(lines):
                    if line.startswith(prefecture) and len(line) > 12 and "｜" not in line:
                        addr = re.sub(r"営業時間.*", "", line).strip()
                        name = lines[i - 1] if i > 0 else "スーパードラッグアサヒ"
                        if name.startswith(prefecture) or name in ("TEL", "地図"):
                            name = "スーパードラッグアサヒ"
                        name = re.sub(r"\t+", " ", name).strip()
                        stores.append(
                            _store("スーパードラッグアサヒ", f"スーパードラッグアサヒ {name}", addr, "official_drug_asahi", prefecture)
                        )
            except Exception as e:
                print(f"    drug-asahi 失敗: {e}")

        def _gmaps_batch(chain: str, query: str) -> None:
            nonlocal stores
            seen = {s["address"] for s in stores}
            try:
                page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}", timeout=90000)
                page.wait_for_timeout(4000)
                try:
                    feed = page.locator('div[role="feed"]').first
                    for _ in range(12):
                        feed.evaluate("el => el.scrollTop += 400")
                        page.wait_for_timeout(800)
                except Exception:
                    pass
                for item in page.locator('a[href*="/maps/place"]').all()[:30]:
                    try:
                        label = (item.get_attribute("aria-label") or "").strip()
                        if not label:
                            continue
                        item.click(timeout=3000)
                        page.wait_for_timeout(1500)
                        body = page.inner_text("body")
                        m = re.search(rf"({prefecture}[^\n]{{8,100}})", body)
                        if m:
                            addr = normalize_address(m.group(1).strip(), prefecture)
                            if addr not in seen:
                                seen.add(addr)
                                stores.append(_store(chain, label[:80], addr, "google_maps_browser", prefecture))
                    except Exception:
                        continue
            except Exception as e:
                print(f"    gmaps {chain}/{query[:20]} 失敗: {e}")

        for chain, query in cfg.get("pref_queries", []):
            _gmaps_batch(chain, query)
        for chain, prefix in cfg.get("city_queries", []):
            for city in cfg.get("cities", []):
                _gmaps_batch(chain, f"{prefix} {city} {prefecture[:2]}")

        browser.close()
    return stores


def dedupe_stores(stores: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique: list[dict] = []
    for s in stores:
        key = (s["company"], s["address"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique


def collect_official_only(slug: str) -> pd.DataFrame:
    cfg = PREFECTURES[slug]
    prefecture = cfg["name"]
    paths = ensure_dirs(slug)

    print(f"\n[公式収集] {prefecture} — Places API 不使用")

    all_stores: list[dict] = []
    fetchers = [
        ("ツルハYext", lambda: fetch_tsuruha_yext(prefecture, cfg["center"])),
        ("ウエルシアAPI", lambda: fetch_welcia(prefecture)),
        ("薬王堂", lambda: fetch_yakuodo(prefecture)),
        ("コスモス", lambda: fetch_cosmos(prefecture)),
        ("サンドラッグ", lambda: fetch_sundrag(prefecture)),
        ("クスリのアオキ", lambda: fetch_aoki(prefecture)),
        ("マツモトキヨシ", lambda: fetch_matsukiyo(prefecture)),
        ("セイムス", lambda: fetch_seims(prefecture)),
        ("GENKY", lambda: fetch_genky(prefecture)),
        ("カワチ薬品", lambda: fetch_kawachi(prefecture)),
        ("Playwright追加", lambda: fetch_extra_chains_playwright(prefecture)),
    ]

    for name, fn in fetchers:
        try:
            batch = fn()
            batch = dedupe_stores(batch)
            print(f"  {name}: {len(batch)}件")
            all_stores.extend(batch)
        except Exception as e:
            print(f"  {name} 失敗: {e}")

    all_stores = dedupe_stores(all_stores)
    df = pd.DataFrame(all_stores)
    df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
    print(f"\n  raw_stores.csv: {len(df)}件")
    if not df.empty:
        print("  チェーン別:", df["company"].value_counts().to_dict())
        print("  ソース別:", df["source"].value_counts().to_dict())
    return df


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    target = sys.argv[1] if len(sys.argv) > 1 else "01_青森県"
    collect_official_only(target)

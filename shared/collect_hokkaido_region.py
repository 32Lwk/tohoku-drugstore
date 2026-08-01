"""北海道 1地域分の店舗収集（Multitask Mode 用）"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.hokkaido_fetchers import fetch_all_hokkaido_sources, fetch_gmaps_for_region
from shared.hokkaido_regions import HOKKAIDO_SLUG, REGIONS, filter_stores_for_region
from shared.utils import ensure_dirs

SLUG = HOKKAIDO_SLUG


def region_paths(region_id: str) -> dict:
    base = ROOT / "prefectures" / SLUG / "data" / "regions" / region_id
    return {
        "base": base,
        "raw_csv": base / "raw_stores.csv",
        "report": base / "report.md",
        "done": base / ".done",
    }


def collect_region(region_id: str, skip_gmaps: bool = False) -> pd.DataFrame:
    if region_id not in REGIONS:
        raise ValueError(f"未知の地域ID: {region_id}. 有効: {list(REGIONS)}")

    cfg = REGIONS[region_id]
    paths = region_paths(region_id)
    paths["base"].mkdir(parents=True, exist_ok=True)
    ensure_dirs(SLUG)

    print("=" * 80)
    print(f"北海道 {cfg['title']} ({region_id}) — Places API 不使用")
    print("=" * 80)

    all_stores: list[dict] = []

    # 公式API/サイト（全域取得 → 地域フィルタ）
    hokkaido_stores = fetch_all_hokkaido_sources(cfg["center"])
    region_official = filter_stores_for_region(hokkaido_stores, region_id)
    print(f"  公式/API フィルタ後: {len(region_official)}件")
    all_stores.extend(region_official)

    # Google Maps ブラウザ検索（地域特化）
    if not skip_gmaps:
        gmaps_stores = fetch_gmaps_for_region(region_id, cfg)
        print(f"  Google Maps ブラウザ: {len(gmaps_stores)}件")
        all_stores.extend(gmaps_stores)

    # 重複除去
    seen: set[tuple] = set()
    unique: list[dict] = []
    for s in all_stores:
        key = (s["company"], s["address"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    df = pd.DataFrame(unique)
    df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")

    report_lines = [
        f"# 北海道 {cfg['title']} 収集レポート",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**地域ID**: `{region_id}`",
        "",
        f"- 店舗数: **{len(df)}件**",
        "",
    ]
    if not df.empty:
        report_lines.extend([
            "## チェーン別",
            "",
            "| チェーン | 件数 |",
            "|---------|------|",
        ])
        for chain, count in df["company"].value_counts().items():
            report_lines.append(f"| {chain} | {count} |")
        report_lines.extend([
            "",
            "## ソース別",
            "",
            "| ソース | 件数 |",
            "|--------|------|",
        ])
        for src, count in df["source"].value_counts().items():
            report_lines.append(f"| {src} | {count} |")

    paths["report"].write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    paths["done"].write_text(datetime.now().isoformat(), encoding="utf-8")

    print(f"\n完了: {cfg['title']} — {len(df)}件 → {paths['raw_csv']}")
    return df


def status() -> dict:
    result = {}
    for region_id, cfg in REGIONS.items():
        paths = region_paths(region_id)
        done = paths["done"].exists()
        count = 0
        if paths["raw_csv"].exists():
            count = len(pd.read_csv(paths["raw_csv"], encoding="utf-8-sig"))
        result[region_id] = {"title": cfg["title"], "done": done, "stores": count}
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="北海道地域別店舗収集")
    parser.add_argument("region_id", nargs="?", help="r1_sapporo 等")
    parser.add_argument("--status", action="store_true", help="全地域の進捗表示")
    parser.add_argument("--skip-gmaps", action="store_true", help="Google Maps ブラウザ検索をスキップ")
    args = parser.parse_args()

    if args.status:
        for rid, info in status().items():
            mark = "OK" if info["done"] else "未"
            print(f"[{mark}] {rid}: {info['title']} — {info['stores']}件")
    elif args.region_id:
        collect_region(args.region_id, skip_gmaps=args.skip_gmaps)
    else:
        parser.print_help()

"""北海道5地域の raw_stores.csv をマージ"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.collect_hokkaido_region import region_paths, status
from shared.hokkaido_regions import HOKKAIDO_SLUG, REGIONS, all_region_ids
from shared.utils import ensure_dirs

SLUG = HOKKAIDO_SLUG


def merge_regions(require_all: bool = True) -> pd.DataFrame:
    st = status()
    pending = [rid for rid, info in st.items() if not info["done"]]
    if require_all and pending:
        raise RuntimeError(f"未完了地域: {pending}. 全5地域完了後にマージしてください。")

    frames = []
    for region_id in all_region_ids():
        paths = region_paths(region_id)
        if not paths["raw_csv"].exists():
            if require_all:
                raise FileNotFoundError(f"raw_stores.csv なし: {paths['raw_csv']}")
            continue
        df = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
        df["region_id"] = region_id
        frames.append(df)
        print(f"  {region_id}: {len(df)}件")

    if not frames:
        raise RuntimeError("マージ対象データがありません")

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["company", "address"], keep="first")
    if "place_id" in merged.columns:
        merged = merged.drop_duplicates(subset=["place_id"], keep="first")

    paths = ensure_dirs(SLUG)
    merged.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")

    summary_path = ROOT / "prefectures" / SLUG / "data" / "regions" / "merge_report.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 北海道 地域マージレポート",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**合計店舗数**: {len(merged)}件",
        "",
        "## 地域別",
        "",
        "| 地域 | 件数 |",
        "|------|------|",
    ]
    for region_id in all_region_ids():
        cfg = REGIONS[region_id]
        n = len(merged[merged.get("region_id", pd.Series()) == region_id]) if "region_id" in merged.columns else 0
        lines.append(f"| {cfg['title']} | {n} |")
    lines.extend([
        "",
        "## チェーン別 TOP15",
        "",
        "| チェーン | 件数 |",
        "|---------|------|",
    ])
    for chain, count in merged["company"].value_counts().head(15).items():
        lines.append(f"| {chain} | {count} |")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nマージ完了: {len(merged)}件 → {paths['raw_csv']}")
    return merged


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="未完了地域があってもマージ")
    args = parser.parse_args()
    merge_regions(require_all=not args.force)

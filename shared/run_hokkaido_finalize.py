"""北海道調査 — マージ後の最終処理（Coordinator 用）"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.analyze_density import analyze_for_prefecture
from shared.clean_data import clean_for_prefecture
from shared.create_maps import create_all_maps
from shared.geocode_stores import geocode_for_prefecture
from shared.hokkaido_regions import HOKKAIDO_SLUG
from shared.merge_hokkaido_regions import merge_regions
from shared.run_prefecture import run_step, validate_prefecture, write_report
from shared.verify_data import cross_validate

SLUG = HOKKAIDO_SLUG


def finalize(gsi_only: bool = True, force_merge: bool = False) -> dict:
    print("=" * 80)
    print(f"北海道 最終処理 — {'GSI座標のみ' if gsi_only else 'Google Geocoding 可'}")
    print("=" * 80)

    run_step("Step 0: 5地域マージ", merge_regions, not force_merge)
    run_step("Step 5: クリーニング", clean_for_prefecture, SLUG)
    run_step("Step 6: 座標取得", geocode_for_prefecture, SLUG, gsi_only=gsi_only)
    run_step("Step 7: 密度分析", analyze_for_prefecture, SLUG)
    run_step("Step 8: 地図生成", create_all_maps, SLUG)
    run_step("Step 9: 検証", cross_validate, SLUG, max_retries=1)

    checks = validate_prefecture(SLUG)
    write_report(SLUG, checks)

    if checks["coord_rate"] < 90:
        print(f"  [注意] 座標取得率 {checks['coord_rate']}% — geocode 再実行を推奨")
    print(f"\n完了: 北海道 — {checks['total_stores']}件 / 座標率 {checks['coord_rate']}%")
    return checks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-google-geocode", action="store_true")
    parser.add_argument("--force-merge", action="store_true")
    args = parser.parse_args()
    finalize(gsi_only=not args.allow_google_geocode, force_merge=args.force_merge)

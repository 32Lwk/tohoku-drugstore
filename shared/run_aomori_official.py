"""青森県再調査 — Places API 不使用版パイプライン"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.analyze_density import analyze_for_prefecture
from shared.clean_data import clean_for_prefecture
from shared.collect_official_only import collect_official_only
from shared.config import PREFECTURES
from shared.create_maps import create_all_maps
from shared.fetch_boundaries import fetch_for_prefecture as fetch_boundaries
from shared.fetch_census import fetch_for_prefecture as fetch_census
from shared.geocode_stores import geocode_for_prefecture
from shared.run_prefecture import run_step, validate_prefecture, write_report
from shared.verify_data import cross_validate


def run_aomori_official(slug: str = "01_青森県") -> dict:
    cfg = PREFECTURES[slug]
    print("=" * 80)
    print(f"開始: {cfg['name']} ({slug}) — 公式サイト/API のみ（Places API 不使用）")
    print("=" * 80)

    run_step("Step 1: 境界データ", fetch_boundaries, slug)
    run_step("Step 2: 国勢調査2020", fetch_census, slug)
    run_step("Step 3: 公式サイト/API 収集", collect_official_only, slug)
    run_step("Step 5: クリーニング", clean_for_prefecture, slug)
    run_step("Step 6: 座標取得", geocode_for_prefecture, slug)
    run_step("Step 7: 密度分析", analyze_for_prefecture, slug)
    run_step("Step 8: 地図生成", create_all_maps, slug)
    run_step("Step 9: 検証", cross_validate, slug, max_retries=1)

    checks = validate_prefecture(slug)
    write_report(slug, checks)
    print(f"\n完了: {cfg['name']} - {checks['total_stores']}件 / 座標率 {checks['coord_rate']}%")
    return checks


if __name__ == "__main__":
    run_aomori_official(sys.argv[1] if len(sys.argv) > 1 else "01_青森県")

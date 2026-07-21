"""1県分の全パイプライン実行"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.analyze_density import analyze_for_prefecture
from shared.clean_data import clean_for_prefecture
from shared.collect_stores import collect_for_prefecture
from shared.config import PREFECTURES
from shared.create_maps import create_all_maps
from shared.fetch_boundaries import fetch_for_prefecture as fetch_boundaries
from shared.fetch_census import fetch_for_prefecture as fetch_census
from shared.geocode_stores import geocode_for_prefecture
from shared.verify_data import cross_validate


def validate_prefecture(slug: str) -> dict:
    paths = ensure_dirs(slug)
    checks = {}

    coord = __import__("pandas").read_csv(paths["coord_csv"], encoding="utf-8-sig")
    checks["total_stores"] = len(coord)
    checks["with_coords"] = coord["latitude"].notna().sum()
    checks["coord_rate"] = round(checks["with_coords"] / max(len(coord), 1) * 100, 1)
    checks["chains"] = coord["company"].nunique()
    checks["chain_counts"] = coord["company"].value_counts().to_dict()

    density = __import__("pandas").read_csv(paths["density_csv"], encoding="utf-8-sig")
    checks["municipalities"] = len(density)
    checks["maps_exist"] = all(
        (paths["maps"] / f).exists()
        for f in [
            f"{PREFECTURES[slug]['name']}ドラッグストア地図.html",
            f"{PREFECTURES[slug]['name']}ドラッグストア密度コロプレスマップ.html",
            f"{PREFECTURES[slug]['name']}高齢化率コロプレスマップ.html",
        ]
    )
    return checks


def write_report(slug: str, checks: dict) -> None:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    lines = [
        f"# {cfg['name']} ドラッグストア調査レポート",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## サマリー",
        "",
        f"- 総店舗数: **{checks['total_stores']}件**",
        f"- 座標取得率: **{checks['coord_rate']}%** ({checks['with_coords']}/{checks['total_stores']})",
        f"- チェーン数: **{checks['chains']}**",
        f"- 分析市区町村数: **{checks['municipalities']}**",
        f"- 地図生成: **{'完了' if checks['maps_exist'] else '未完了'}**",
        "",
        "## チェーン別店舗数",
        "",
        "| チェーン | 店舗数 |",
        "|---------|--------|",
    ]
    for chain, count in sorted(checks["chain_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {chain} | {count} |")

    lines.extend([
        "",
        "## 成果物",
        "",
        f"- `{paths['final_csv'].name}`",
        f"- `{paths['coord_csv'].name}`",
        f"- `{paths['density_csv'].name}`",
        f"- maps/ 内 HTML 3ファイル",
        "",
    ])
    paths["report"].write_text("\n".join(lines), encoding="utf-8")


def run_prefecture(slug: str) -> dict:
    cfg = PREFECTURES[slug]
    print("=" * 80)
    print(f"開始: {cfg['name']} ({slug})")
    print("=" * 80)

    print("\n[Step 1/8] 境界データ取得")
    fetch_boundaries(slug)

    print("\n[Step 2/8] 国勢調査データ取得")
    fetch_census(slug)

    print("\n[Step 3/8] 店舗データ収集")
    collect_for_prefecture(slug)

    print("\n[Step 4/8] データクリーニング")
    clean_for_prefecture(slug)

    print("\n[Step 5/8] 座標取得")
    geocode_for_prefecture(slug)

    print("\n[Step 6/8] 密度分析")
    analyze_for_prefecture(slug)

    print("\n[Step 7/8] 地図生成")
    create_all_maps(slug)

    print("\n[Step 8/8] 検証・レポート")
    cross_validate(slug)
    checks = validate_prefecture(slug)
    write_report(slug, checks)

    print(f"\n完了: {cfg['name']} - {checks['total_stores']}件")
    return checks


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    run_prefecture(target)

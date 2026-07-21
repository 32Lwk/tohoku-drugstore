"""1県分の全パイプライン実行（エラー時リトライ・自己修復対応）"""

import sys
import traceback
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
from shared.fetch_official_stores import fetch_official_for_prefecture
from shared.geocode_stores import geocode_for_prefecture
from shared.scrape_official import merge_official_into_raw
from shared.utils import ensure_dirs
from shared.verify_data import cross_validate


def run_step(name: str, func, *args, max_retries: int = 3, **kwargs):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n>>> {name} (試行 {attempt}/{max_retries})")
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            print(f"  [警告] {name} 失敗: {e}")
            if attempt < max_retries:
                print("  → 再試行します...")
            else:
                print(traceback.format_exc())
    raise RuntimeError(f"{name} が {max_retries} 回失敗: {last_error}")


def validate_prefecture(slug: str) -> dict:
    paths = ensure_dirs(slug)
    coord = __import__("pandas").read_csv(paths["coord_csv"], encoding="utf-8-sig")
    density = __import__("pandas").read_csv(paths["density_csv"], encoding="utf-8-sig")
    pref_name = PREFECTURES[slug]["name"]

    return {
        "total_stores": len(coord),
        "with_coords": int(coord["latitude"].notna().sum()),
        "coord_rate": round(int(coord["latitude"].notna().sum()) / max(len(coord), 1) * 100, 1),
        "chains": int(coord["company"].nunique()),
        "chain_counts": coord["company"].value_counts().to_dict(),
        "municipalities": len(density),
        "maps_exist": all(
            (paths["maps"] / f).exists()
            for f in [
                f"{pref_name}ドラッグストア地図.html",
                f"{pref_name}ドラッグストア密度コロプレスマップ.html",
                f"{pref_name}高齢化率コロプレスマップ.html",
            ]
        ),
    }


def write_report(slug: str, checks: dict) -> None:
    cfg = PREFECTURES[slug]
    paths = ensure_dirs(slug)
    zero_chains = [
        c for c in [
            "GENKY", "コスモス", "クリエイト", "ハックドラッグ", "ドラッグユタカ",
            "Vドラッグ", "ZIPドラッグ", "セキ薬品", "よどやドラッグ", "サツドラ",
        ]
        if checks["chain_counts"].get(c, 0) == 0
    ]
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
    if zero_chains:
        lines.extend([
            "",
            "## 0件チェーン（東北未出店または検出なし）",
            "",
            ", ".join(zero_chains),
        ])
    lines.extend(["", "## 成果物", "", f"- maps/ HTML 3ファイル", ""])
    paths["report"].write_text("\n".join(lines), encoding="utf-8")


def run_prefecture(slug: str) -> dict:
    cfg = PREFECTURES[slug]
    print("=" * 80)
    print(f"開始: {cfg['name']} ({slug})")
    print("=" * 80)

    run_step("Step 1: 境界データ", fetch_boundaries, slug)
    run_step("Step 2: 国勢調査2020", fetch_census, slug)
    run_step("Step 3: Google Places 一次調査", collect_for_prefecture, slug)
    run_step("Step 4a: 公式API二次調査", fetch_official_for_prefecture, slug, max_retries=2)
    run_step("Step 4b: 公式サイトスクレイピング", merge_official_into_raw, slug, max_retries=2)
    run_step("Step 5: クリーニング", clean_for_prefecture, slug)
    run_step("Step 6: 座標取得", geocode_for_prefecture, slug)
    run_step("Step 7: 密度分析", analyze_for_prefecture, slug)
    run_step("Step 8: 地図生成", create_all_maps, slug)
    run_step("Step 9: 検証", cross_validate, slug, max_retries=1)

    checks = validate_prefecture(slug)
    write_report(slug, checks)

    if checks["coord_rate"] < 95:
        print(f"  [注意] 座標取得率 {checks['coord_rate']}% — geocode_stores.py 再実行を推奨")
    if not checks["maps_exist"]:
        print("  [注意] 地図未生成 — create_maps.py 再実行を推奨")

    print(f"\n完了: {cfg['name']} - {checks['total_stores']}件")
    return checks


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    run_prefecture(target)

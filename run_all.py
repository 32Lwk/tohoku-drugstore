"""東北6県 一括実行（県別順次処理）"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from shared.config import PREFECTURES
from shared.run_prefecture import run_prefecture


def write_summary(results: dict) -> None:
    lines = [
        "# 東北6県 ドラッグストア調査 実行レポート",
        "",
        f"**完了日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 県別サマリー",
        "",
        "| 県 | 店舗数 | 座標率 | チェーン数 | 地図 |",
        "|-----|--------|--------|-----------|------|",
    ]
    total = 0
    for slug, checks in results.items():
        name = PREFECTURES[slug]["name"]
        total += checks["total_stores"]
        maps = "OK" if checks["maps_exist"] else "NG"
        lines.append(
            f"| {name} | {checks['total_stores']} | {checks['coord_rate']}% "
            f"| {checks['chains']} | {maps} |"
        )

    lines.extend([
        "",
        f"**合計店舗数: {total}件**",
        "",
        "## 詳細レポート",
        "",
    ])
    for slug in PREFECTURES:
        lines.append(f"- [prefectures/{slug}/report.md](prefectures/{slug}/report.md)")

    (ROOT / "00_実行レポート.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nサマリー保存: {ROOT / '00_実行レポート.md'}")


def run_all(parallel: bool = False) -> dict:
    slugs = list(PREFECTURES.keys())
    results = {}

    if parallel:
        with ProcessPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(run_prefecture, s): s for s in slugs}
            for fut in as_completed(futures):
                slug = futures[fut]
                results[slug] = fut.result()
    else:
        for slug in slugs:
            results[slug] = run_prefecture(slug)

    write_summary(results)
    return results


if __name__ == "__main__":
    parallel = "--parallel" in sys.argv
    run_all(parallel=parallel)

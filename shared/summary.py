"""6県サマリーレポート生成"""

from datetime import datetime
from pathlib import Path

from shared.config import PREFECTURES

ROOT = Path(__file__).resolve().parent.parent


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
    for slug in PREFECTURES:
        if slug not in results:
            continue
        checks = results[slug]
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

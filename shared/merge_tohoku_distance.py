"""東北6県 距離分析の統合"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from shared.config import PREFECTURES, TOHOKU, TOHOKU_DIR, TOHOKU_SLUGS
from shared.utils import prefecture_paths


def tohoku_distance_paths() -> dict:
    data = TOHOKU_DIR / "data"
    data.mkdir(parents=True, exist_ok=True)
    return {
        "centroid_csv": data / "市区町村別最寄りドラッグストア距離.csv",
        "mesh_csv": data / "メッシュ別最寄りドラッグストア距離.csv",
        "summary_csv": data / "距離分析サマリー.csv",
        "report": TOHOKU_DIR / "distance_report.md",
    }


def merge_tohoku_distance() -> dict:
    paths = tohoku_distance_paths()
    centroid_frames, mesh_frames, summary_frames = [], [], []

    for slug in TOHOKU_SLUGS:
        cfg = PREFECTURES[slug]
        pref = cfg["name"]
        p = prefecture_paths(slug)

        c = pd.read_csv(p["data"] / "市区町村別最寄りドラッグストア距離.csv", encoding="utf-8-sig")
        c.insert(0, "都道府県", pref)
        centroid_frames.append(c)

        m = pd.read_csv(p["data"] / "メッシュ別最寄りドラッグストア距離.csv", encoding="utf-8-sig")
        m.insert(0, "都道府県", pref)
        mesh_frames.append(m)

        s = pd.read_csv(p["data"] / "距離分析サマリー.csv", encoding="utf-8-sig")
        summary_frames.append(s)

    centroid_all = pd.concat(centroid_frames, ignore_index=True)
    mesh_all = pd.concat(mesh_frames, ignore_index=True)
    summary_all = pd.concat(summary_frames, ignore_index=True)

    centroid_all.to_csv(paths["centroid_csv"], index=False, encoding="utf-8-sig")
    mesh_all.to_csv(paths["mesh_csv"], index=False, encoding="utf-8-sig")
    summary_all.to_csv(paths["summary_csv"], index=False, encoding="utf-8-sig")

    write_report(summary_all, paths["report"])

    print(f"  統合重心CSV: {paths['centroid_csv']} ({len(centroid_all)}件)")
    print(f"  統合メッシュCSV: {paths['mesh_csv']} ({len(mesh_all)}件)")
    print(f"  統合サマリー: {paths['summary_csv']}")
    return {
        "centroid_rows": len(centroid_all),
        "mesh_rows": len(mesh_all),
        "summary": summary_all,
    }


def write_report(summary: pd.DataFrame, report_path: Path) -> None:
    centroid = summary[summary["分析方法"] == "市区町村重心法"].copy()
    mesh = summary[summary["分析方法"] == "1kmメッシュ法"].copy()

    lines = [
        "# 東北6県 ドラッグストア距離分析レポート",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 概要",
        "",
        "各県の居住者（国勢調査2020人口）から最寄りドラッグストアまでの**直線距離**を、",
        "市区町村重心法（近似）と1kmメッシュ法（より正確）の2通りで算出しました。",
        "最寄り店舗の探索範囲は**東北6県全体**です（県境付近の越境利用を反映）。",
        "",
        "## 県別 人口加重平均距離 (km)",
        "",
        "| 都道府県 | 重心法 | 1kmメッシュ法 | 差 (mesh - centroid) |",
        "|---------|--------|--------------|---------------------|",
    ]

    for pref in [PREFECTURES[s]["name"] for s in TOHOKU_SLUGS]:
        c_row = centroid[centroid["都道府県"] == pref]
        m_row = mesh[mesh["都道府県"] == pref]
        if c_row.empty or m_row.empty:
            continue
        c_val = c_row.iloc[0]["人口加重平均距離_km"]
        m_val = m_row.iloc[0]["人口加重平均距離_km"]
        diff = round(m_val - c_val, 3)
        lines.append(f"| {pref} | {c_val} | {m_val} | {diff:+.3f} |")

    lines.extend(
        [
            "",
            "## 詳細指標",
            "",
            "### 市区町村重心法",
            "",
            "| 都道府県 | 平均(km) | 中央値(km) | 90%ile(km) | 市区町村数 | 人口 |",
            "|---------|---------|-----------|-----------|-----------|------|",
        ]
    )
    for _, row in centroid.iterrows():
        lines.append(
            f"| {row['都道府県']} | {row['人口加重平均距離_km']} | "
            f"{row['人口加重中央値_km']} | {row['人口加重90パーセンタイル_km']} | "
            f"{int(row['対象市区町村数'])} | {int(row['対象人口']):,} |"
        )

    lines.extend(
        [
            "",
            "### 1kmメッシュ法",
            "",
            "| 都道府県 | 平均(km) | 中央値(km) | 90%ile(km) | メッシュ数 | 人口 |",
            "|---------|---------|-----------|-----------|-----------|------|",
        ]
    )
    for _, row in mesh.iterrows():
        lines.append(
            f"| {row['都道府県']} | {row['人口加重平均距離_km']} | "
            f"{row['人口加重中央値_km']} | {row['人口加重90パーセンタイル_km']} | "
            f"{int(row['対象メッシュ数'])} | {int(row['対象人口']):,} |"
        )

    lines.extend(
        [
            "",
            "## 成果物",
            "",
            "- `data/市区町村別最寄りドラッグストア距離.csv`",
            "- `data/メッシュ別最寄りドラッグストア距離.csv`",
            "- `data/距離分析サマリー.csv`",
            "",
            "## 注記",
            "",
            "- 距離は Haversine 直線距離（道路距離ではありません）",
            "- メッシュ人口は e-Stat 都道府県別 1km メッシュ（国勢調査2020）",
            "- 重心法は政令市など広域市区町村で過小/過大評価になる場合があります",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  レポート: {report_path}")


if __name__ == "__main__":
    merge_tohoku_distance()

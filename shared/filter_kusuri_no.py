"""既存の最終版・座標付きCSVから「くすりの○○」調剤薬局のみ除外"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.analyze_density import analyze_for_prefecture
from shared.build_tohoku import build_tohoku
from shared.config import PREFECTURES
from shared.create_maps import create_all_maps
from shared.utils import ensure_dirs, is_kusuri_no_pharmacy
from shared.verify_data import cross_validate


def filter_kusuri_no(slug: str) -> int:
    paths = ensure_dirs(slug)
    removed = 0

    for key in ("final_csv", "coord_csv"):
        p = paths[key]
        if not p.exists():
            continue
        df = pd.read_csv(p, encoding="utf-8-sig")
        before = len(df)
        mask = df.apply(
            lambda r: is_kusuri_no_pharmacy(r["store_name"], r.get("company", "")),
            axis=1,
        )
        df = df[~mask].reset_index(drop=True)
        removed = before - len(df)
        df.to_csv(p, index=False, encoding="utf-8-sig")
        print(f"  {p.name}: {before} → {len(df)} ({removed}件除外)")

    return removed


def main():
    total_removed = 0
    for slug in PREFECTURES:
        print(f"\n--- {PREFECTURES[slug]['name']} ---")
        total_removed += filter_kusuri_no(slug)
        analyze_for_prefecture(slug)
        create_all_maps(slug)
        cross_validate(slug)

    print(f"\n合計除外: {total_removed}件")
    build_tohoku()


if __name__ == "__main__":
    main()

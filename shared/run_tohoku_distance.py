"""東北6県 距離分析（県別並列実行 + 統合）"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.config import PREFECTURES, TOHOKU_SLUGS
from shared.merge_tohoku_distance import merge_tohoku_distance
from shared.run_distance_prefecture import run_distance_prefecture


def run_all_parallel(store_scope: str = "tohoku", max_workers: int = 6) -> dict:
    print("=" * 60)
    print("東北6県 距離分析（並列実行）")
    print("=" * 60)

    results = {}
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_distance_prefecture, slug, store_scope): slug
            for slug in TOHOKU_SLUGS
        }
        for future in as_completed(futures):
            slug = futures[future]
            results[slug] = future.result()

    print("\n" + "=" * 60)
    print("東北6県 統合")
    print("=" * 60)
    merged = merge_tohoku_distance()
    return {"prefectures": results, "merged": merged}


def run_all_sequential(store_scope: str = "tohoku") -> dict:
    results = {}
    for slug in TOHOKU_SLUGS:
        results[slug] = run_distance_prefecture(slug, store_scope=store_scope)
    merged = merge_tohoku_distance()
    return {"prefectures": results, "merged": merged}


if __name__ == "__main__":
    parallel = "--sequential" not in sys.argv
    scope = "prefecture" if "--pref-only" in sys.argv else "tohoku"
    if parallel:
        run_all_parallel(store_scope=scope)
    else:
        run_all_sequential(store_scope=scope)

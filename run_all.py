"""東北6県 一括実行（県別順次処理）"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from shared.config import PREFECTURES
from shared.run_prefecture import run_prefecture
from shared.summary import write_summary


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


def summarize_existing() -> dict | None:
    """既存の6県成果物からサマリーのみ生成（再調査なし）"""
    from shared.auto_summarize import check_status, collect_results

    count, _, pending = check_status()
    if count < 6:
        print(f"未完了: {len(pending)}県")
        return None
    results = collect_results()
    write_summary(results)
    return results


if __name__ == "__main__":
    if "--summary-only" in sys.argv:
        summarize_existing()
    else:
        parallel = "--parallel" in sys.argv
        run_all(parallel=parallel)

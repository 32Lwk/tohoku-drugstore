"""1県分の距離分析実行"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.analyze_distance import analyze_for_prefecture
from shared.config import PREFECTURES


def run_distance_prefecture(slug: str, store_scope: str = "tohoku") -> dict:
    cfg = PREFECTURES[slug]
    print("=" * 60)
    print(f"距離分析: {cfg['name']} ({slug})")
    print("=" * 60)
    try:
        result = analyze_for_prefecture(slug, store_scope=store_scope)
        print(f"完了: {cfg['name']}")
        return result
    except Exception:
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "03_宮城県"
    scope = sys.argv[2] if len(sys.argv) > 2 else "tohoku"
    run_distance_prefecture(slug, store_scope=scope)

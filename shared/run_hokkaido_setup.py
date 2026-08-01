"""北海道調査 — 初期セットアップ（Coordinator 用・1回のみ）"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.fetch_boundaries import fetch_for_prefecture
from shared.fetch_census import fetch_for_prefecture
from shared.hokkaido_regions import HOKKAIDO_SLUG
from shared.utils import ensure_dirs

SLUG = HOKKAIDO_SLUG


def setup() -> None:
    print("=" * 80)
    print("北海道 初期セットアップ（境界 + 国勢調査）")
    print("=" * 80)

    ensure_dirs(SLUG)
    regions_dir = ROOT / "prefectures" / SLUG / "data" / "regions"
    regions_dir.mkdir(parents=True, exist_ok=True)

    print("\n>>> Step 1: 境界データ")
    fetch_for_prefecture(SLUG)

    print("\n>>> Step 2: 国勢調査2020")
    fetch_for_prefecture(SLUG)

    print("\nセットアップ完了。5地域の Multitask 収集を開始してください。")
    print("進捗確認: python shared/collect_hokkaido_region.py --status")


if __name__ == "__main__":
    setup()

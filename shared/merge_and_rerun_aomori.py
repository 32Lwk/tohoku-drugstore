"""extra_chains.json を raw_stores.csv にマージしてパイプライン再実行"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.clean_data import clean_for_prefecture
from shared.analyze_density import analyze_for_prefecture
from shared.create_maps import create_all_maps
from shared.geocode_stores import geocode_for_prefecture
from shared.verify_data import cross_validate
from shared.run_prefecture import validate_prefecture, write_report
from shared.fetch_official_stores import _make_place_id
from shared.utils import ensure_dirs, normalize_address, normalize_chain_name

SLUG = "01_青森県"


def merge_extra_chains(slug: str) -> int:
    paths = ensure_dirs(slug)
    extra_path = paths["data"] / "extra_chains.json"
    if not extra_path.exists():
        print("extra_chains.json なし")
        return 0

    df = pd.read_csv(paths["raw_csv"], encoding="utf-8-sig")
    existing_addrs = set(df["address"].astype(str).tolist())
    extra = json.loads(extra_path.read_text(encoding="utf-8"))

    added = 0
    rows = []
    for chain, stores in extra.items():
        for s in stores:
            company = normalize_chain_name(s.get("company") or chain)
            addr = normalize_address(s["address"], "青森県")
            if addr in existing_addrs:
                continue
            rows.append({
                "company": company,
                "store_name": s.get("store_name") or company,
                "address": addr,
                "place_id": _make_place_id("extra", company, addr),
                "latitude": None,
                "longitude": None,
                "source": "official_extra",
            })
            existing_addrs.add(addr)
            added += 1

    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
        df.to_csv(paths["raw_csv"], index=False, encoding="utf-8-sig")
    print(f"raw_stores.csv: +{added}件 → 合計{len(df)}件")
    print("  チェーン別:", df["company"].value_counts().to_dict())
    return added


def main():
    merge_extra_chains(SLUG)
    clean_for_prefecture(SLUG)
    geocode_for_prefecture(SLUG)
    analyze_for_prefecture(SLUG)
    create_all_maps(SLUG)
    cross_validate(SLUG)
    checks = validate_prefecture(SLUG)
    write_report(SLUG, checks)
    print(f"\n完了: {checks['total_stores']}件 / 座標率 {checks['coord_rate']}%")
    print("チェーン:", checks["chain_counts"])


if __name__ == "__main__":
    main()

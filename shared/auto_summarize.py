"""6県すべて完了したら 00_実行レポート.md を自動生成（最後に終わった Agent が実行）"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.config import PREFECTURES
from shared.summary import write_summary
from shared.utils import prefecture_paths

LOCK_FILE = ROOT / ".summary_generated.lock"


def _prefecture_complete(slug: str) -> bool:
    cfg = PREFECTURES[slug]
    paths = prefecture_paths(slug)
    pref = cfg["name"]

    required = [
        paths["report"],
        paths["coord_csv"],
        paths["density_csv"],
        paths["maps"] / f"{pref}ドラッグストア地図.html",
        paths["maps"] / f"{pref}ドラッグストア密度コロプレスマップ.html",
        paths["maps"] / f"{pref}高齢化率コロプレスマップ.html",
    ]
    return all(p.exists() for p in required)


def check_status() -> tuple[int, list[str], list[str]]:
    done, pending = [], []
    for slug in PREFECTURES:
        if _prefecture_complete(slug):
            done.append(slug)
        else:
            pending.append(slug)
    return len(done), done, pending


def validate_prefecture(slug: str) -> dict:
    """軽量検証（googlemaps 等不要）"""
    import pandas as pd

    cfg = PREFECTURES[slug]
    paths = prefecture_paths(slug)
    coord_csv = paths["coord_csv"]
    density_csv = paths["density_csv"]
    maps = paths["maps"]
    pref = cfg["name"]

    coord = pd.read_csv(coord_csv, encoding="utf-8-sig")
    density = pd.read_csv(density_csv, encoding="utf-8-sig")

    return {
        "total_stores": len(coord),
        "with_coords": int(coord["latitude"].notna().sum()),
        "coord_rate": round(int(coord["latitude"].notna().sum()) / max(len(coord), 1) * 100, 1),
        "chains": int(coord["company"].nunique()),
        "chain_counts": coord["company"].value_counts().to_dict(),
        "municipalities": len(density),
        "maps_exist": all(
            (maps / f).exists()
            for f in [
                f"{pref}ドラッグストア地図.html",
                f"{pref}ドラッグストア密度コロプレスマップ.html",
                f"{pref}高齢化率コロプレスマップ.html",
            ]
        ),
    }


def collect_results() -> dict:
    results = {}
    for slug in PREFECTURES:
        results[slug] = validate_prefecture(slug)
    return results


def _git_pull():
    try:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT, check=False, capture_output=True)
    except Exception:
        pass


def _git_push_summary():
    subprocess.run(["git", "add", "00_実行レポート.md"], cwd=ROOT, check=True)
    msg = f"docs: 東北6県調査サマリー自動生成 ({datetime.now():%Y-%m-%d %H:%M})"
    r = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, capture_output=True, text=True)
    if r.returncode == 0:
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
        print("  git push 完了")
    elif "nothing to commit" in (r.stdout or "") + (r.stderr or ""):
        print("  サマリーは既に最新です")


def try_summarize(force: bool = False) -> bool:
    _git_pull()

    count, done, pending = check_status()
    print(f"\n[auto_summarize] 完了: {count}/6 県")
    for slug in done:
        print(f"  [OK] {PREFECTURES[slug]['name']}")
    for slug in pending:
        print(f"  [待] {PREFECTURES[slug]['name']}")

    if count < 6 and not force:
        print("  → 6県未完了のためサマリー生成をスキップ（最後の Agent が再実行します）")
        return False

    if LOCK_FILE.exists() and not force:
        mtime = datetime.fromtimestamp(LOCK_FILE.stat().st_mtime)
        report = ROOT / "00_実行レポート.md"
        if report.exists() and count == 6:
            print(f"  → サマリー生成済み ({mtime:%Y-%m-%d %H:%M})")
            return True

    print("\n[auto_summarize] 6県すべて完了 → サマリー生成中...")
    results = collect_results()
    write_summary(results)
    LOCK_FILE.write_text(datetime.now().isoformat(), encoding="utf-8")
    _git_push_summary()
    print("[auto_summarize] 完了: 00_実行レポート.md")
    return True


def watch(interval_sec: int = 300):
    """PC常時稼働時: 5分ごとに完了確認 → 自動サマリー"""
    print(f"[watch] {interval_sec}秒間隔で6県完了を監視...")
    while True:
        if try_summarize():
            print("[watch] サマリー生成完了。監視終了。")
            return
        time.sleep(interval_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="完了まで定期監視")
    parser.add_argument("--interval", type=int, default=300, help="監視間隔（秒）")
    parser.add_argument("--force", action="store_true", help="6県未完了でも強制生成")
    args = parser.parse_args()

    if args.watch:
        watch(args.interval)
    else:
        try_summarize(force=args.force)

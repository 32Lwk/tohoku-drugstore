"""GitHub Pages 用サイトを組み立てる。"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.config import PREFECTURES, TOHOKU_SLUGS

SITE_DIR = ROOT / "_site"
CUSTOM_DOMAIN = "maps.medicine.yutok.dev"
TOHOKU_MAPS_SOURCE = ROOT / "tohoku" / "maps"

MAP_TYPES = [
    ("{name}ドラッグストア地図.html", "ドラッグストア地図", "チェーン別店舗位置（ピンマップ）"),
    ("{name}ドラッグストア密度コロプレスマップ.html", "ドラッグストア密度コロプレスマップ", "市区町村別の店舗密度"),
    ("{name}高齢化率コロプレスマップ.html", "高齢化率コロプレスマップ", "市区町村別の高齢化率"),
]

TOHOKU_UNIFIED_MAPS = [
    ("東北ドラッグストア地図.html", "東北6県統合 — ドラッグストア地図", "チェーン別店舗位置（ピンマップ）"),
    (
        "東北ドラッグストア密度コロプレスマップ.html",
        "東北6県統合 — 密度コロプレスマップ",
        "市区町村別の店舗密度",
    ),
    (
        "東北高齢化率コロプレスマップ.html",
        "東北6県統合 — 高齢化率コロプレスマップ",
        "市区町村別の高齢化率（2020年国勢調査）",
    ),
]

TOHOKU_PREFECTURES = []
for slug in TOHOKU_SLUGS:
    pref_name = PREFECTURES[slug]["name"]
    pref_id = slug.split("_", 1)[0]
    TOHOKU_PREFECTURES.append(
        {
            "id": pref_id,
            "title": pref_name,
            "subtitle": f"{pref_name}の個別調査マップ",
            "source": ROOT / "prefectures" / slug / "maps",
            "maps": [
                (
                    filename.format(name=pref_name),
                    f"{pref_name}{label}",
                    desc,
                )
                for filename, label, desc in MAP_TYPES
            ],
        }
    )

STANDALONE_REGIONS = [
    {
        "id": "aichi",
        "title": "愛知県",
        "subtitle": "愛知県内のドラッグストア調査",
        "source": ROOT / "prefectures" / "07_愛知県" / "maps",
        "maps": [
            ("愛知県ドラッグストア地図.html", "愛知県ドラッグストア地図", "チェーン別店舗位置（ピンマップ）"),
            ("愛知県ドラッグストア密度コロプレスマップ.html", "愛知県ドラッグストア密度コロプレスマップ", "市区町村別の店舗密度"),
            ("愛知県高齢化率コロプレスマップ.html", "愛知県高齢化率コロプレスマップ", "市区町村別の高齢化率"),
        ],
    },
    {
        "id": "wakayama",
        "title": "和歌山県",
        "subtitle": "和歌山県内のドラッグストア・薬局調査",
        "source": ROOT / "prefectures" / "08_和歌山県" / "maps",
        "maps": [
            ("和歌山県ドラッグストア地図.html", "和歌山県ドラッグストア地図", "薬局・店舗位置（ピンマップ）"),
            ("和歌山県ドラッグストア密度コロプレスマップ.html", "和歌山県ドラッグストア密度コロプレスマップ", "市区町村別の店舗密度"),
            ("和歌山県高齢化率コロプレスマップ.html", "和歌山県高齢化率コロプレスマップ", "市区町村別の高齢化率"),
        ],
    },
]

TOP_REGIONS = [
    {
        "id": "tohoku",
        "title": "東北地方",
        "subtitle": "6県統合マップと県別マップ",
    },
    *STANDALONE_REGIONS,
]

SITE_CSS = """
    * { box-sizing: border-box; }
    body {
      font-family: "Meiryo", "Yu Gothic", sans-serif;
      max-width: 760px;
      margin: 0 auto;
      padding: 2rem 1.5rem;
      line-height: 1.6;
      color: #222;
      background: #f7f9fb;
    }
    h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
    h2 {
      font-size: 1.15rem;
      margin: 0 0 0.25rem;
      padding-top: 0.5rem;
      border-top: 2px solid #e1e4e8;
    }
    h3 { font-size: 1rem; margin: 1rem 0 0.5rem; color: #333; }
    section:first-of-type h2 { border-top: none; padding-top: 0; }
    .subtitle, .region-desc, .section-desc {
      color: #555;
      margin-top: 0;
      margin-bottom: 1rem;
    }
    .subtitle { margin-bottom: 1.5rem; }
    .breadcrumb {
      font-size: 0.875rem;
      color: #57606a;
      margin-bottom: 1.25rem;
    }
    .breadcrumb a {
      color: #0969da;
      text-decoration: none;
    }
    .breadcrumb a:hover { text-decoration: underline; }
    ul { list-style: none; padding: 0; margin: 0 0 1rem; }
    li { margin-bottom: 0.75rem; }
    .region-grid {
      display: grid;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }
    .pref-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1rem;
    }
    a.card, a.map-link {
      display: block;
      padding: 1rem 1.25rem;
      background: #fff;
      border: 1px solid #d0d7de;
      border-radius: 8px;
      color: #0969da;
      text-decoration: none;
      font-weight: 600;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    a.card:hover, a.map-link:hover {
      border-color: #0969da;
      box-shadow: 0 2px 8px rgba(9, 105, 218, 0.12);
    }
    a.pref-card {
      display: block;
      padding: 0.85rem 1rem;
      background: #fff;
      border: 1px solid #d0d7de;
      border-radius: 8px;
      color: #0969da;
      text-decoration: none;
      font-weight: 600;
      text-align: center;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    a.pref-card:hover {
      border-color: #0969da;
      box-shadow: 0 2px 8px rgba(9, 105, 218, 0.12);
    }
    .desc {
      display: block;
      margin-top: 0.25rem;
      font-size: 0.875rem;
      font-weight: 400;
      color: #57606a;
    }
"""


def _copy_map_files(source: Path, dest: Path, maps: list[tuple[str, str, str]]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for filename, _, _ in maps:
        src = source / filename
        if not src.exists():
            raise FileNotFoundError(f"Map not found: {src}")
        shutil.copy2(src, dest / filename)
        sidecar = source / f"{Path(filename).stem}.geojson"
        if sidecar.exists():
            shutil.copy2(sidecar, dest / sidecar.name)


def copy_maps() -> None:
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir()

    tohoku_dir = SITE_DIR / "tohoku"
    _copy_map_files(TOHOKU_MAPS_SOURCE, tohoku_dir, TOHOKU_UNIFIED_MAPS)

    for pref in TOHOKU_PREFECTURES:
        _copy_map_files(pref["source"], tohoku_dir / pref["id"], pref["maps"])

    for region in STANDALONE_REGIONS:
        _copy_map_files(region["source"], SITE_DIR / region["id"], region["maps"])


def write_cname() -> None:
    (SITE_DIR / "CNAME").write_text(f"{CUSTOM_DOMAIN}\n", encoding="utf-8")


def _breadcrumb(items: list[tuple[str, str | None]]) -> str:
    parts = []
    for label, href in items:
        if href:
            parts.append(f'<a href="{href}">{label}</a>')
        else:
            parts.append(f"<span>{label}</span>")
    return '<nav class="breadcrumb" aria-label="パンくず">' + " › ".join(parts) + "</nav>"


def _render_map_links(maps: list[tuple[str, str, str]], href_prefix: str = "") -> str:
    return "\n".join(
        f"""    <li>
      <a class="map-link" href="{href_prefix}{filename}">
        {label}
        <span class="desc">{desc}</span>
      </a>
    </li>"""
        for filename, label, desc in maps
    )


def _write_html(path: Path, *, title: str, h1: str, subtitle: str, breadcrumb: str, body: str) -> None:
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{SITE_CSS}
  </style>
</head>
<body>
{breadcrumb}
  <h1>{h1}</h1>
  <p class="subtitle">{subtitle}</p>
{body}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def write_top_index() -> None:
    cards = "\n".join(
        f"""    <a class="card" href="{region['id']}/">
      {region['title']}
      <span class="desc">{region['subtitle']}</span>
    </a>"""
        for region in TOP_REGIONS
    )
    body = f"""  <div class="region-grid">
{cards}
  </div>"""
    _write_html(
        SITE_DIR / "index.html",
        title="ドラッグストア調査マップ",
        h1="ドラッグストア調査マップ",
        subtitle="地域を選んでインタラクティブマップを確認できます。",
        breadcrumb="",
        body=body,
    )


def write_tohoku_index() -> None:
    pref_cards = "\n".join(
        f'      <a class="pref-card" href="{pref["id"]}/">{pref["title"]}</a>'
        for pref in TOHOKU_PREFECTURES
    )
    body = f"""  <section>
    <h2>6県統合マップ</h2>
    <p class="section-desc">東北6県を1枚の地図で確認</p>
    <ul>
{_render_map_links(TOHOKU_UNIFIED_MAPS)}
    </ul>
  </section>
  <section>
    <h2>県別マップ</h2>
    <p class="section-desc">各県の個別調査結果</p>
    <div class="pref-grid">
{pref_cards}
    </div>
  </section>"""
    _write_html(
        SITE_DIR / "tohoku" / "index.html",
        title="東北地方 — ドラッグストア調査マップ",
        h1="東北地方",
        subtitle="東北6県の統合マップと県別マップ",
        breadcrumb=_breadcrumb([("トップ", "../index.html"), ("東北地方", None)]),
        body=body,
    )


def write_tohoku_prefecture_indices() -> None:
    for pref in TOHOKU_PREFECTURES:
        body = f"""  <ul>
{_render_map_links(pref["maps"])}
    </ul>"""
        _write_html(
            SITE_DIR / "tohoku" / pref["id"] / "index.html",
            title=f"{pref['title']} — ドラッグストア調査マップ",
            h1=pref["title"],
            subtitle=pref["subtitle"],
            breadcrumb=_breadcrumb(
                [
                    ("トップ", "../../index.html"),
                    ("東北地方", "../index.html"),
                    (pref["title"], None),
                ]
            ),
            body=body,
        )


def write_standalone_indices() -> None:
    for region in STANDALONE_REGIONS:
        body = f"""  <ul>
{_render_map_links(region["maps"])}
    </ul>"""
        _write_html(
            SITE_DIR / region["id"] / "index.html",
            title=f"{region['title']} — ドラッグストア調査マップ",
            h1=region["title"],
            subtitle=region["subtitle"],
            breadcrumb=_breadcrumb([("トップ", "../index.html"), (region["title"], None)]),
            body=body,
        )


def write_source_tohoku_index() -> None:
    """ローカル開発用: tohoku/maps/index.html を東北ページと同期"""
    pref_cards = "\n".join(
        f'      <a class="pref-card" href="../../prefectures/{slug}/maps/{PREFECTURES[slug]["name"]}ドラッグストア地図.html">{PREFECTURES[slug]["name"]}</a>'
        for slug in TOHOKU_SLUGS
    )
    body = f"""  <section>
    <h2>6県統合マップ</h2>
    <p class="section-desc">東北6県を1枚の地図で確認</p>
    <ul>
{_render_map_links(TOHOKU_UNIFIED_MAPS)}
    </ul>
  </section>
  <section>
    <h2>県別マップ</h2>
    <p class="section-desc">各県の個別調査結果（ローカル: prefectures 配下の HTML へ直接リンク）</p>
    <div class="pref-grid">
{pref_cards}
    </div>
  </section>
  <p class="section-desc">公開サイト用の階層ナビは <code>python scripts/build_site.py</code> 実行後の <code>_site/</code> を参照してください。</p>"""
    _write_html(
        TOHOKU_MAPS_SOURCE / "index.html",
        title="東北地方 — ドラッグストア調査マップ",
        h1="東北地方",
        subtitle="東北6県の統合マップと県別マップ",
        breadcrumb="",
        body=body,
    )


def write_indices() -> None:
    write_top_index()
    write_tohoku_index()
    write_tohoku_prefecture_indices()
    write_standalone_indices()
    write_source_tohoku_index()


def main() -> None:
    copy_maps()
    write_cname()
    write_indices()
    print(f"Built site at {SITE_DIR}")


if __name__ == "__main__":
    main()

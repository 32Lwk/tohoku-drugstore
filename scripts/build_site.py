"""GitHub Pages 用サイトを組み立てる。"""

from __future__ import annotations

import shutil
from pathlib import Path

from shared.config import PREFECTURES, TOHOKU_SLUGS

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "_site"
CUSTOM_DOMAIN = "maps.medicine.yutok.dev"

MAP_TYPES = [
    ("{name}ドラッグストア地図.html", "ドラッグストア地図", "チェーン別店舗位置（ピンマップ）"),
    ("{name}ドラッグストア密度コロプレスマップ.html", "ドラッグストア密度コロプレスマップ", "市区町村別の店舗密度"),
    ("{name}高齢化率コロプレスマップ.html", "高齢化率コロプレスマップ", "市区町村別の高齢化率"),
]

REGIONS = [
    {
        "id": "tohoku",
        "title": "東北地方（統合）",
        "subtitle": "東北6県の統合マップ",
        "source": ROOT / "tohoku" / "maps",
        "maps": [
            ("東北ドラッグストア地図.html", "東北ドラッグストア地図", "チェーン別店舗位置（ピンマップ）"),
            ("東北ドラッグストア密度コロプレスマップ.html", "東北ドラッグストア密度コロプレスマップ", "市区町村別の店舗密度"),
            ("東北高齢化率コロプレスマップ.html", "東北高齢化率コロプレスマップ", "市区町村別の高齢化率（2020年国勢調査）"),
        ],
    },
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

TOHOKU_PREFECTURE_REGIONS = []
for slug in TOHOKU_SLUGS:
    pref_name = PREFECTURES[slug]["name"]
    TOHOKU_PREFECTURE_REGIONS.append(
        {
            "id": f"tohoku-{slug.split('_', 1)[0]}",
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


def copy_maps() -> None:
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir()

    all_regions = REGIONS + TOHOKU_PREFECTURE_REGIONS
    for region in all_regions:
        dest = SITE_DIR / region["id"]
        dest.mkdir()
        source: Path = region["source"]
        for filename, _, _ in region["maps"]:
            src = source / filename
            if not src.exists():
                raise FileNotFoundError(f"Map not found: {src}")
            shutil.copy2(src, dest / filename)


def write_cname() -> None:
    (SITE_DIR / "CNAME").write_text(f"{CUSTOM_DOMAIN}\n", encoding="utf-8")


def _render_map_list(region: dict) -> str:
    return "\n".join(
        f"""    <li>
      <a href="{region['id']}/{filename}">
        {label}
        <span class="desc">{desc}</span>
      </a>
    </li>"""
        for filename, label, desc in region["maps"]
    )


def write_index() -> None:
    sections = []
    for region in REGIONS:
        sections.append(
            f"""  <section>
    <h2>{region['title']}</h2>
    <p class="region-desc">{region['subtitle']}</p>
    <ul>
{_render_map_list(region)}
    </ul>
  </section>"""
        )

    pref_blocks = []
    for region in TOHOKU_PREFECTURE_REGIONS:
        pref_blocks.append(
            f"""    <div class="pref-block">
      <h3>{region['title']}</h3>
      <ul>
{_render_map_list(region)}
      </ul>
    </div>"""
        )

    sections.append(
        f"""  <section>
    <h2>東北6県（県別）</h2>
    <p class="region-desc">各県の個別マップ</p>
{chr(10).join(pref_blocks)}
  </section>"""
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ドラッグストア調査マップ</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Meiryo", "Yu Gothic", sans-serif;
      max-width: 760px;
      margin: 0 auto;
      padding: 2rem 1.5rem;
      line-height: 1.6;
      color: #222;
      background: #f7f9fb;
    }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    h2 {{
      font-size: 1.15rem;
      margin: 0 0 0.25rem;
      padding-top: 0.5rem;
      border-top: 2px solid #e1e4e8;
    }}
    h3 {{ font-size: 1rem; margin: 1rem 0 0.5rem; color: #333; }}
    section:first-of-type h2 {{ border-top: none; padding-top: 0; }}
    .subtitle, .region-desc {{
      color: #555;
      margin-top: 0;
      margin-bottom: 1rem;
    }}
    .subtitle {{ margin-bottom: 1.5rem; }}
    ul {{ list-style: none; padding: 0; margin: 0 0 1rem; }}
    li {{ margin-bottom: 0.75rem; }}
    .pref-block {{ margin-bottom: 0.5rem; }}
    a {{
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
    }}
    a:hover {{
      border-color: #0969da;
      box-shadow: 0 2px 8px rgba(9, 105, 218, 0.12);
    }}
    .desc {{
      display: block;
      margin-top: 0.25rem;
      font-size: 0.875rem;
      font-weight: 400;
      color: #57606a;
    }}
  </style>
</head>
<body>
  <h1>ドラッグストア調査マップ</h1>
  <p class="subtitle">地域別のインタラクティブマップを確認できます。</p>
{chr(10).join(sections)}
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    copy_maps()
    write_cname()
    write_index()
    print(f"Built site at {SITE_DIR}")


if __name__ == "__main__":
    main()

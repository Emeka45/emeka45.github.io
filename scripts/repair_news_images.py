from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "news"
IMAGES = NEWS / "images"
SITE = "https://emeka45-github-io.pages.dev"


def repair_article(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    title_match = re.search(r"<h1>(.*?)</h1>", raw, re.I | re.S)
    if not title_match:
        return False
    stem = path.stem
    candidates = [
        IMAGES / f"{stem}-source.jpg",
        IMAGES / f"{stem}.jpg",
        IMAGES / f"{stem}.jpeg",
        IMAGES / f"{stem}.webp",
        IMAGES / f"{stem}.png",
    ]
    image = next((p for p in candidates if p.exists() and p.stat().st_size > 10000), None)
    if image is None:
        return False

    relative = f"news/images/{image.name}"
    # Article files live inside /news/, so the correct relative image URL is
    # images/<file>, not ../news/images/<file> (which becomes /news/news/images/).
    article_src = f"images/{image.name}"
    absolute = f"{SITE}/{relative}"
    title = html.escape(re.sub(r"<[^>]+>", "", title_match.group(1)), quote=True)

    og = f'<meta property="og:image" content="{absolute}">'
    if re.search(r'<meta[^>]+property=["\']og:image["\'][^>]*>', raw, re.I):
        raw = re.sub(r'<meta[^>]+property=["\']og:image["\'][^>]*>', og, raw, count=1, flags=re.I)
    else:
        raw = raw.replace("</title>", f"</title>{og}<meta name=\"twitter:card\" content=\"summary_large_image\">", 1)

    hero = f'<figure class="news-hero-image" style="margin:1.25rem 0 1.5rem;"><img src="{article_src}" alt="{title}" loading="eager" decoding="async" style="display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:16px;"><figcaption style="margin-top:.5rem;font-size:.85rem;opacity:.7;">Lead image</figcaption></figure>'
    if re.search(r'<figure[^>]+class=["\']news-hero-image["\'][^>]*>.*?</figure>', raw, re.I | re.S):
        raw = re.sub(r'<figure[^>]+class=["\']news-hero-image["\'][^>]*>.*?</figure>', hero, raw, count=1, flags=re.I | re.S)
    else:
        raw = raw.replace("</h1>", f"</h1>{hero}", 1)

    path.write_text(raw, encoding="utf-8")
    print("REPAIRED IMAGE:", path.name, "->", article_src)
    return True


count = 0
for article in sorted(NEWS.glob("*.html")):
    if article.name.startswith("index"):
        continue
    try:
        count += int(repair_article(article))
    except Exception as exc:
        print("REPAIR FAILED:", article.name, exc)

print("Repaired articles:", count)

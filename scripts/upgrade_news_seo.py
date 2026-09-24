from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "news"
INDEX = NEWS / "index.json"
SITE = "https://emeka45-github-io.pages.dev"
AUTHOR_URL = f"{SITE}/"


def text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()


def clean_category(value: str) -> str:
    value = text(value)
    return re.sub(r"^←\\s*C\\. O\\. Eric Newsroom\\s*", "", value, flags=re.I).strip() or "News"


def iso_from_visible_date(raw: str, fallback: dt.datetime) -> str:
    match = re.search(r"<p>(?:[^<]+) · (\d{2}) (\w{3}) (\d{4})</p>", raw, re.I)
    if match:
        try:
            parsed = dt.datetime.strptime(" ".join(match.groups()), "%d %b %Y").replace(tzinfo=dt.timezone.utc)
            return parsed.isoformat()
        except ValueError:
            pass
    return fallback.isoformat()


def article_schema(path: Path, raw: str) -> dict:
    title_m = re.search(r"<h1>(.*?)</h1>", raw, re.S | re.I)
    summary_m = re.search(r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']*)[\"']", raw, re.I)
    image_m = re.search(r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']", raw, re.I)
    title = text(title_m.group(1)) if title_m else path.stem
    description = html.unescape(summary_m.group(1)) if summary_m else ""
    image = image_m.group(1) if image_m else None
    published = iso_from_visible_date(raw, dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc))
    modified = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat()
    canonical = f"{SITE}/news/{path.name}"
    return {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "description": description,
        "url": canonical,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "datePublished": published,
        "dateModified": modified,
        "author": {"@type": "Person", "name": "C. O. Eric", "url": AUTHOR_URL},
        "publisher": {"@type": "Organization", "name": "C. O. Eric", "url": SITE},
        **({"image": [image]} if image else {}),
    }


def inject_schema(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    schema = article_schema(path, raw)
    block = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + '</script>'
    raw = re.sub(r'<script type="application/ld\+json">.*?</script>', '', raw, flags=re.I | re.S)
    raw = raw.replace("</head>", block + "</head>", 1)
    path.write_text(raw, encoding="utf-8")


def rebuild_index() -> None:
    items = []
    for path in NEWS.glob("*.html"):
        try:
            raw = path.read_text(encoding="utf-8")
            title_m = re.search(r"<h1>(.*?)</h1>", raw, re.S | re.I)
            summary_m = re.search(r"<p><strong>(.*?)</strong></p>", raw, re.S | re.I)
            category_m = re.search(r"<p>(.*?) · ", raw, re.S | re.I)
            schema_m = re.search(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S | re.I)
            schema = json.loads(schema_m.group(1)) if schema_m else article_schema(path, raw)
            item = {
                "file": path.name,
                "title": text(title_m.group(1)) if title_m else path.stem,
                "summary": text(summary_m.group(1)) if summary_m else "",
                "category": clean_category(category_m.group(1)) if category_m else "News",
                "date": dt.datetime.fromisoformat(schema["datePublished"].replace("Z", "+00:00")).strftime("%d %b %Y"),
            }
            image_m = re.search(r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']", raw, re.I)
            if image_m:
                item["image"] = image_m.group(1)
            items.append(item)
        except Exception as exc:
            print("SEO skipped", path, exc)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    INDEX.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    count = 0
    for path in NEWS.glob("*.html"):
        inject_schema(path)
        count += 1
    rebuild_index()
    print(f"News SEO upgraded: {count} articles")


if __name__ == "__main__":
    main()

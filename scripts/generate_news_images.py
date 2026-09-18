from __future__ import annotations

import base64
import datetime as dt
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "news"
IMAGES = NEWS / "images"
INDEX = NEWS / "index.json"
REPORT = ROOT / "newsroom-data" / "image-report.json"
MODEL = "gemini-2.5-flash-image"
MAX_IMAGES_PER_RUN = 20


def clean_text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()


def story_data(path: Path):
    raw = path.read_text(encoding="utf-8")
    title_match = re.search(r"<h1>(.*?)</h1>", raw, re.I | re.S)
    summary_match = re.search(r"<p><strong>(.*?)</strong></p>", raw, re.I | re.S)
    category_match = re.search(r"<p>([^<·]+) · [^<]+</p>", raw, re.I | re.S)
    if not title_match:
        return None
    title = clean_text(title_match.group(1))
    summary = clean_text(summary_match.group(1)) if summary_match else ""
    category = clean_text(category_match.group(1)) if category_match else "News"
    return raw, title, summary, category


def image_name(path: Path) -> str:
    return f"{path.stem}.png"


def photo_name(path: Path) -> str:
    return f"{path.stem}.jpg"


def source_photo_name(path: Path) -> str:
    return f"{path.stem}-source.jpg"


def fallback_name(path: Path) -> str:
    return f"{path.stem}.svg"


def generate_fallback_svg(title: str, summary: str, category: str) -> bytes:
    safe_title = html.escape(title[:105])
    safe_summary = html.escape(summary[:180])
    safe_category = html.escape(category.upper()[:24])
    palette = {"gaming": (91, 50, 214), "anime": (236, 72, 153), "technology": (14, 116, 144), "ai": (124, 58, 237), "science": (5, 150, 105), "world": (37, 99, 235), "nigeria politics": (0, 92, 76), "religion & faith": (146, 94, 24), "education": (37, 99, 235), "business & economy": (15, 118, 110), "security & crime": (127, 29, 29), "health": (5, 150, 105), "agriculture": (34, 120, 50), "sports": (15, 100, 160), "entertainment & lifestyle": (180, 65, 120)}
    r, g, b = palette.get(category.strip().lower(), (17, 24, 39))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="t d"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="rgb({r},{g},{b})"/><stop offset="1" stop-color="#111827"/></linearGradient></defs><rect width="1600" height="900" fill="url(#bg)"/><circle cx="1280" cy="180" r="240" fill="#fff" opacity=".10"/><circle cx="280" cy="760" r="300" fill="#fff" opacity=".06"/><path d="M0 710 C330 590 480 820 820 690 S1270 500 1600 620 V900 H0Z" fill="#000" opacity=".22"/><rect x="92" y="82" width="270" height="54" rx="27" fill="#fff" opacity=".94"/><text x="227" y="118" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="23" font-weight="700" fill="#111827">C. O. ERIC NEWSROOM</text><text id="t" x="100" y="650" font-family="Arial,Helvetica,sans-serif" font-size="27" font-weight="800" fill="#fff" opacity=".85">{safe_category}</text><text x="100" y="710" font-family="Arial,Helvetica,sans-serif" font-size="48" font-weight="800" fill="#fff">{safe_title}</text><text id="d" x="100" y="765" font-family="Arial,Helvetica,sans-serif" font-size="24" fill="#fff" opacity=".78">{safe_summary}</text><text x="100" y="838" font-family="Arial,Helvetica,sans-serif" font-size="18" fill="#fff" opacity=".55">Editorial fallback artwork</text></svg>'''
    return svg.encode("utf-8")


def generate_image(title: str, summary: str, category: str, api_key: str) -> bytes:
    prompt = f"""Create a polished original editorial news illustration for the C. O. Eric Newsroom. Headline: {title}. Category: {category}. Summary: {summary}. Wide 16:9 editorial hero composition, professional and realistic, communicate the central subject, no identifiable real-person portrait, no logos, trademarks, watermarks, captions, headlines, readable text, UI screenshots or invented statistics, no graphic violence or sexual content."""
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["Image"]}}
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read())
            for candidate in data.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        return base64.b64decode(inline["data"])
            raise RuntimeError("Gemini returned no image data")
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                detail = str(exc)
            if exc.code in (429,):
                raise RuntimeError(f"HTTP {exc.code}: {detail}")
            if exc.code not in (500, 502, 503, 504):
                raise RuntimeError(f"HTTP {exc.code}: {detail}")
            if attempt == 2:
                raise RuntimeError(f"HTTP {exc.code}: {detail}")
            time.sleep(10 * (attempt + 1))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    raise RuntimeError("Gemini image generation failed")


def extract_source_urls(raw: str):
    urls = []
    for match in re.findall(r'href=["\'](https?://[^"\']+)["\']', raw, re.I):
        url = html.unescape(match)
        host = urllib.parse.urlparse(url).netloc.lower()
        # Google News is an aggregator, not the publisher's image host. Its
        # og:image can be generic Google/News artwork, which is exactly the
        # misleading image seen on some newsroom cards.
        blocked_hosts = {
            "news.google.com",
            "google.com",
            "www.google.com",
            "emeka45.github.io",
            "emeka45-github-io.pages.dev",
        }
        if host and host not in blocked_hosts and url not in urls:
            urls.append(url)
    return urls[:8]


def download_source_photo(source_url: str):
    request = urllib.request.Request(source_url, headers={"User-Agent": "Mozilla/5.0 (compatible; COEricNewsroom/2.1)"})
    with urllib.request.urlopen(request, timeout=25) as response:
        page = response.read(2_500_000).decode("utf-8", errors="replace")
    candidates = []
    patterns = [
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
    ]
    for pattern in patterns:
        candidates.extend(re.findall(pattern, page, re.I))
    base = source_url
    for image_url in candidates:
        image_url = urllib.parse.urljoin(base, html.unescape(image_url))
        if not image_url.startswith("http"):
            continue
        try:
            image_request = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 (compatible; COEricNewsroom/2.1)"})
            with urllib.request.urlopen(image_request, timeout=25) as image_response:
                image = image_response.read(8_000_000)
            content_type = image_response.headers.get("Content-Type", "")
            if len(image) > 15000 and ("image/" in content_type or image[:4] == b"\x89PNG" or image[:2] == b"\xff\xd8"):
                return image, {"provider": "Original news source", "source_url": source_url, "image_url": image_url}
        except Exception:
            continue
    raise RuntimeError("source page has no downloadable og:image/twitter:image")


def search_openverse_photo(title: str, category: str):
    queries = [title, f"{title.split(':')[0]} {category}", category]
    for text in queries:
        query = urllib.parse.quote(text[:180])
        endpoint = f"https://api.openverse.org/v1/images/?q={query}&page_size=20&source=wikimedia,flickr"
        request = urllib.request.Request(endpoint, headers={"User-Agent": "COEricAI-Newsroom/2.1"})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.loads(response.read())
            for result in data.get("results", []):
                image_url = result.get("url") or result.get("thumbnail")
                if not image_url or not image_url.startswith("http"):
                    continue
                try:
                    image_request = urllib.request.Request(image_url, headers={"User-Agent": "COEricAI-Newsroom/2.1"})
                    with urllib.request.urlopen(image_request, timeout=25) as image_response:
                        image = image_response.read(8_000_000)
                    if len(image) > 15000:
                        return image, {"provider": "Openverse", "creator": result.get("creator") or "Unknown creator", "license": result.get("license") or "Unknown license", "source_url": result.get("foreign_landing_url") or result.get("url") or image_url}
                except Exception:
                    continue
        except Exception:
            continue
    raise RuntimeError("Openverse returned no usable photo")


def add_image_to_article(raw: str, title: str, relative_image: str, caption: str) -> str:
    escaped_title = html.escape(title, quote=True)
    image_tag = f'<meta property="og:image" content="https://emeka45-github-io.pages.dev/{relative_image}"><meta name="twitter:card" content="summary_large_image">'
    if 'property="og:image"' not in raw:
        raw = raw.replace("</title>", "</title>" + image_tag, 1)
    hero = f'<figure class="news-hero-image" style="margin:1.25rem 0 1.5rem;"><img src="../{relative_image}" alt="{escaped_title}" loading="eager" decoding="async" style="display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:16px;"><figcaption style="margin-top:.5rem;font-size:.85rem;opacity:.7;">{html.escape(caption)}</figcaption></figure>'
    if "news-hero-image" not in raw:
        raw = raw.replace("</h1>", "</h1>" + hero, 1)
    else:
        raw = re.sub(r'(<figure class="news-hero-image".*?</figure>)', hero, raw, count=1, flags=re.S)
    return raw


def update_index():
    items = []
    for path in NEWS.glob("*.html"):
        try:
            raw = path.read_text(encoding="utf-8")
            title_match = re.search(r"<h1>(.*?)</h1>", raw, re.S | re.I)
            summary_match = re.search(r"<p><strong>(.*?)</strong></p>", raw, re.S | re.I)
            category_match = re.search(r"<p>([^<·]+) · [^<]+</p>", raw, re.S | re.I)
            if not title_match:
                continue
            title = clean_text(title_match.group(1)); summary = clean_text(summary_match.group(1)) if summary_match else ""; category = clean_text(category_match.group(1)) if category_match else "News"
            candidates = [IMAGES / f"{path.stem}.png", IMAGES / f"{path.stem}.jpg", IMAGES / f"{path.stem}.jpeg", IMAGES / f"{path.stem}.webp", IMAGES / f"{path.stem}-source.jpg", IMAGES / f"{path.stem}.svg"]
            existing = next((p for p in candidates if p.exists() and p.stat().st_size > 1000), None)
            image = f"news/images/{existing.name}" if existing else "news/images/story-default.svg"
            items.append({"file": path.name, "title": title, "summary": summary, "category": category, "date": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%d %b %Y"), "image": image})
        except Exception as exc:
            print("Index skipped", path, exc)
    items.sort(key=lambda item: item["file"], reverse=True)
    INDEX.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    IMAGES.mkdir(parents=True, exist_ok=True)
    missing = []
    for path in sorted(NEWS.glob("*.html"), reverse=True):
        if path.name.startswith("index"):
            continue
        real_files = [IMAGES / image_name(path), IMAGES / photo_name(path), IMAGES / f"{path.stem}.jpeg", IMAGES / f"{path.stem}.webp", IMAGES / source_photo_name(path)]
        if any(p.exists() and p.stat().st_size > 10000 for p in real_files):
            continue
        data = story_data(path)
        if data:
            missing.append((path, data))
    selected = missing[:MAX_IMAGES_PER_RUN]
    generated, source_photos, photos, fallbacks, failures = [], [], [], [], []
    for path, (raw, title, summary, category) in selected:
        # First choice: the actual lead image exposed by one of the article's cited publishers.
        try:
            for source_url in extract_source_urls(raw):
                try:
                    image, meta = download_source_photo(source_url)
                    target = IMAGES / source_photo_name(path)
                    target.write_bytes(image)
                    path.write_text(add_image_to_article(raw, title, f"images/{target.name}", f"Lead image from the cited news source · {urllib.parse.urlparse(source_url).netloc}"), encoding="utf-8")
                    source_photos.append({"article": path.name, "image": str(target.relative_to(ROOT)), "bytes": len(image), **meta})
                    print("SOURCE PHOTO OK:", path.name, source_url)
                    break
                except Exception as source_exc:
                    print("SOURCE PHOTO FAILED:", source_url, str(source_exc))
            else:
                raise RuntimeError("No cited publisher supplied a downloadable lead image")
            if source_photos and source_photos[-1]["article"] == path.name:
                continue
        except Exception:
            pass
        try:
            print("Generating AI image for:", title)
            image = generate_image(title, summary, category, api_key)
            target = IMAGES / image_name(path)
            target.write_bytes(image)
            path.write_text(add_image_to_article(raw, title, f"images/{target.name}", "AI-generated editorial illustration."), encoding="utf-8")
            generated.append({"article": path.name, "image": str(target.relative_to(ROOT)), "bytes": len(image)})
            continue
        except Exception as exc:
            message = str(exc)
            print("AI IMAGE FAILED:", path.name, message)
        try:
            image, meta = search_openverse_photo(title, category)
            target = IMAGES / photo_name(path)
            target.write_bytes(image)
            caption = f"Illustrative photo via Openverse · {meta['creator']} · {meta['license']}"
            path.write_text(add_image_to_article(raw, title, f"images/{target.name}", caption), encoding="utf-8")
            photos.append({"article": path.name, "image": str(target.relative_to(ROOT)), "bytes": len(image), **meta})
            continue
        except Exception as photo_exc:
            print("REAL PHOTO FALLBACK FAILED:", path.name, str(photo_exc))
        try:
            svg = generate_fallback_svg(title, summary, category)
            fallback = IMAGES / fallback_name(path)
            fallback.write_bytes(svg)
            path.write_text(add_image_to_article(raw, title, f"images/{fallback.name}", "Editorial fallback artwork while photo services are unavailable."), encoding="utf-8")
            fallbacks.append({"article": path.name, "image": str(fallback.relative_to(ROOT)), "bytes": len(svg), "reason": "No source, AI or Openverse image available"})
        except Exception as fallback_exc:
            failures.append({"article": path.name, "error": str(fallback_exc)})
    update_index()
    report = {"finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "model": MODEL, "max_images_per_run": MAX_IMAGES_PER_RUN, "missing_before_run": len(missing), "attempted": len(selected), "generated": generated, "source_photos": source_photos, "openverse_photos": photos, "fallbacks": fallbacks, "failures": failures, "remaining_missing_after_run": max(0, len(missing) - len(generated) - len(source_photos) - len(photos) - len(fallbacks))}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

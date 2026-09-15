from __future__ import annotations

import base64
import datetime as dt
import html
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "news"
IMAGES = NEWS / "images"
INDEX = NEWS / "index.json"
REPORT = ROOT / "newsroom-data" / "image-report.json"
MODEL = "gemini-2.5-flash-image"
MAX_IMAGES_PER_RUN = 4


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


def fallback_name(path: Path) -> str:
    return f"{path.stem}.svg"


def generate_fallback_svg(title: str, summary: str, category: str) -> bytes:
    """Create a lightweight story-specific editorial illustration when image API quota is unavailable."""
    safe_title = html.escape(title[:105])
    safe_summary = html.escape(summary[:180])
    safe_category = html.escape(category.upper()[:24])
    palette = {
        "gaming": (91, 50, 214, 255),
        "anime": (236, 72, 153, 255),
        "technology": (14, 116, 144, 255),
        "ai": (124, 58, 237, 255),
        "science": (5, 150, 105, 255),
        "world": (37, 99, 235, 255),
    }
    r, g, b, _ = palette.get(category.strip().lower(), (17, 24, 39, 255))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="t d">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="rgb({r},{g},{b})"/><stop offset="1" stop-color="#111827"/></linearGradient><filter id="glow"><feGaussianBlur stdDeviation="32"/></filter></defs>
<rect width="1600" height="900" fill="url(#bg)"/><circle cx="1280" cy="180" r="240" fill="#fff" opacity=".10" filter="url(#glow)"/><circle cx="280" cy="760" r="300" fill="#fff" opacity=".06"/>
<path d="M0 710 C330 590 480 820 820 690 S1270 500 1600 620 V900 H0Z" fill="#000" opacity=".22"/>
<rect x="92" y="82" width="270" height="54" rx="27" fill="#fff" opacity=".94"/><text x="227" y="118" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="23" font-weight="700" fill="#111827">C. O. ERIC NEWSROOM</text>
<text x="100" y="650" font-family="Arial,Helvetica,sans-serif" font-size="27" font-weight="800" fill="#fff" opacity=".85">{safe_category}</text>
<text id="t" x="100" y="710" font-family="Arial,Helvetica,sans-serif" font-size="48" font-weight="800" fill="#fff">{safe_title}</text>
<text id="d" x="100" y="765" font-family="Arial,Helvetica,sans-serif" font-size="24" fill="#fff" opacity=".78">{safe_summary}</text>
<text x="100" y="838" font-family="Arial,Helvetica,sans-serif" font-size="18" fill="#fff" opacity=".55">Editorial artwork · automatically generated</text>
</svg>'''
    return svg.encode("utf-8")


def generate_image(title: str, summary: str, category: str, api_key: str) -> bytes:
    prompt = f"""Create a polished original editorial news illustration for the C. O. Eric Newsroom.

Headline: {title}
Category: {category}
Summary: {summary}

Visual requirements:
- Compose the scene as a wide editorial hero image; keep the main subject centered and leave useful space around it for a website crop.
- Modern professional editorial-news aesthetic.
- Visually communicate the central subject without reproducing a copyrighted news photograph.
- Do not depict real people as identifiable exact portraits.
- No logos, trademarks, watermarks, captions, headlines, readable text, UI screenshots, or invented statistics.
- No graphic violence or sexual content.
- Strong focal subject, clean composition, realistic lighting, publication-quality detail.
- The image must stand on its own and should not contain words."""
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["Image"]}}
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    last_error = None
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
            last_error = RuntimeError(f"HTTP {exc.code}: {detail}")
            if exc.code not in (429, 500, 502, 503, 504):
                raise last_error
            if exc.code == 429:
                raise last_error
            time.sleep(10 * (attempt + 1))
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise
            time.sleep(5)
    raise last_error


def add_image_to_article(raw: str, title: str, relative_image: str, is_fallback: bool = False) -> str:
    escaped_title = html.escape(title, quote=True)
    image_tag = f'<meta property="og:image" content="https://emeka45-github-io.pages.dev/{relative_image}"><meta name="twitter:card" content="summary_large_image">'
    if 'property="og:image"' not in raw:
        raw = raw.replace("</title>", "</title>" + image_tag, 1)
    caption = "Editorial artwork · automatic fallback while AI image generation is unavailable." if is_fallback else "AI-generated editorial illustration."
    hero = f'<figure class="news-hero-image" style="margin:1.25rem 0 1.5rem;"><img src="../{relative_image}" alt="{escaped_title}" loading="eager" decoding="async" style="display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:16px;"><figcaption style="margin-top:.5rem;font-size:.85rem;opacity:.7;">{caption}</figcaption></figure>'
    if "news-hero-image" not in raw:
        raw = raw.replace("</h1>", "</h1>" + hero, 1)
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
            png = IMAGES / image_name(path); svg = IMAGES / fallback_name(path)
            image = f"news/images/{png.name}" if png.exists() else (f"news/images/{svg.name}" if svg.exists() else "news/images/story-default.svg")
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
        target = IMAGES / image_name(path); fallback = IMAGES / fallback_name(path)
        if (target.exists() and target.stat().st_size > 1000) or (fallback.exists() and fallback.stat().st_size > 1000):
            continue
        data = story_data(path)
        if data:
            missing.append((path, target, fallback, data))
    selected = missing[:MAX_IMAGES_PER_RUN]
    generated, fallbacks, failures = [], [], []
    for path, target, fallback, (raw, title, summary, category) in selected:
        try:
            print("Generating AI image for:", title)
            image = generate_image(title, summary, category, api_key)
            target.write_bytes(image)
            path.write_text(add_image_to_article(raw, title, f"images/{target.name}"), encoding="utf-8")
            generated.append({"article": path.name, "image": str(target.relative_to(ROOT)), "bytes": len(image)})
        except Exception as exc:
            message = str(exc)
            print("AI IMAGE FAILED:", path.name, message)
            if "HTTP 429" in message or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
                svg = generate_fallback_svg(title, summary, category)
                fallback.write_bytes(svg)
                path.write_text(add_image_to_article(raw, title, f"images/{fallback.name}", True), encoding="utf-8")
                fallbacks.append({"article": path.name, "image": str(fallback.relative_to(ROOT)), "bytes": len(svg), "reason": "Gemini image quota unavailable"})
            else:
                failures.append({"article": path.name, "error": message})
    update_index()
    report = {"finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "model": MODEL, "missing_before_run": len(missing), "attempted": len(selected), "generated": generated, "fallbacks": fallbacks, "failures": failures, "remaining_missing_after_run": max(0, len(missing) - len(generated) - len(fallbacks))}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

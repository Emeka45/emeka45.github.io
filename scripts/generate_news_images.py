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


def generate_image(title: str, summary: str, category: str, api_key: str) -> bytes:
    prompt = f"""Create a polished original editorial news illustration for the C. O. Eric Newsroom.

Headline: {title}
Category: {category}
Summary: {summary}

Visual requirements:
- Wide landscape 16:9 composition suitable as a website article hero image.
- Modern professional editorial-news aesthetic.
- Visually communicate the central subject without reproducing a copyrighted news photograph.
- Do not depict real people as identifiable exact portraits.
- No logos, trademarks, watermarks, captions, headlines, readable text, UI screenshots, or invented statistics.
- No graphic violence or sexual content.
- Strong focal subject, clean composition, realistic lighting, publication-quality detail.
- The image must stand on its own and should not contain words."""

    # Gemini's current legacy GenerateContent REST API expects the image
    # configuration under generationConfig.responseFormat.image. Use the
    # v1beta endpoint, which is the documented endpoint for this API.
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["Image"],
            "responseFormat": {
                "image": {
                    "aspectRatio": "16:9"
                }
            }
        }
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
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
            time.sleep(10 * (attempt + 1))
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise
            time.sleep(5)
    raise last_error


def add_image_to_article(raw: str, title: str, relative_image: str) -> str:
    escaped_title = html.escape(title, quote=True)
    image_tag = (
        f'<meta property="og:image" content="https://emeka45-github-io.pages.dev/{relative_image}">'
        f'<meta name="twitter:card" content="summary_large_image">'
    )
    if 'property="og:image"' not in raw:
        raw = raw.replace("</title>", "</title>" + image_tag, 1)
    hero = (
        f'<figure class="news-hero-image" style="margin:1.25rem 0 1.5rem;">'
        f'<img src="../{relative_image}" alt="{escaped_title}" loading="eager" decoding="async" style="display:block;width:100%;height:auto;border-radius:16px;">'
        f'<figcaption style="margin-top:.5rem;font-size:.85rem;opacity:.7;">AI-generated editorial illustration.</figcaption>'
        f'</figure>'
    )
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
            title = clean_text(title_match.group(1))
            summary = clean_text(summary_match.group(1)) if summary_match else ""
            category = clean_text(category_match.group(1)) if category_match else "News"
            image = f"news/images/{image_name(path)}"
            items.append({
                "file": path.name,
                "title": title,
                "summary": summary,
                "category": category,
                "date": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%d %b %Y"),
                "image": image if (IMAGES / image_name(path)).exists() else "news/images/story-default.svg",
            })
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
        target = IMAGES / image_name(path)
        if target.exists() and target.stat().st_size > 1000:
            continue
        data = story_data(path)
        if data:
            missing.append((path, target, data))
    selected = missing[:MAX_IMAGES_PER_RUN]
    generated, failures = [], []
    for path, target, (raw, title, summary, category) in selected:
        try:
            print("Generating image for:", title)
            image = generate_image(title, summary, category, api_key)
            target.write_bytes(image)
            path.write_text(add_image_to_article(raw, title, f"images/{target.name}"), encoding="utf-8")
            generated.append({"article": path.name, "image": str(target.relative_to(ROOT)), "bytes": len(image)})
        except Exception as exc:
            failures.append({"article": path.name, "error": str(exc)})
            print("IMAGE FAILED:", path.name, exc)
    update_index()
    report = {
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": MODEL,
        "missing_before_run": len(missing),
        "attempted": len(selected),
        "generated": generated,
        "failures": failures,
        "remaining_missing_after_run": max(0, len(missing) - len(generated)),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

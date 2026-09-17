from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

AI_MODEL = "gemini-3.5-flash-lite"
MIN_WORDS = 500
TARGET_MIN = 600
TARGET_MAX = 1000
NEWS_DIR = Path("news")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1
        elif tag in {"p", "div", "article", "section", "h1", "h2", "h3", "li", "br"} and self.skip == 0:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1
        elif tag in {"p", "div", "article", "section", "h1", "h2", "h3", "li"} and self.skip == 0:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip == 0:
            self.parts.append(data)


def visible_text(markup: str) -> str:
    parser = TextExtractor()
    parser.feed(markup)
    text = html.unescape("".join(parser.parts))
    return re.sub(r"\s+", " ", text).strip()


def word_count(markup: str) -> int:
    return len(re.findall(r"\b\w+[\w'-]*\b", visible_text(markup)))


def source_records(markup: str):
    records = []
    seen = set()
    for href, label in re.findall(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', markup, re.I | re.S):
        href = html.unescape(href)
        if href in seen:
            continue
        seen.add(href)
        name = visible_text(label) or urllib.parse.urlparse(href).netloc
        records.append({"name": name, "url": href})
    return records[:4]


def fetch_source(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; C.O.Eric-Newsroom/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read(250000)
        text = visible_text(raw.decode("utf-8", errors="ignore"))
        return text[:12000]
    except Exception as exc:
        print(f"Source fetch failed for {url}: {exc}")
        return ""


def call_gemini(title: str, summary: str, category: str, sources: list[dict]) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    evidence = []
    for source in sources:
        text = fetch_source(source["url"])
        if text:
            evidence.append({"name": source["name"], "url": source["url"], "text": text})

    if len(evidence) < 2:
        raise RuntimeError("Fewer than two source pages could be retrieved")

    prompt = f'''You are expanding an existing C. O. Eric AI Newsroom article.

Title: {title}
Category: {category}
Existing summary: {summary}

Rewrite the article into a substantive, source-grounded report of about {TARGET_MIN}-{TARGET_MAX} words when the evidence supports it. Do not pad the story. Use 400-600 words only if the evidence genuinely cannot support a longer report.

Requirements:
- Use ONLY facts supported by the supplied source extracts.
- Preserve the central event and do not change its meaning.
- Add useful context, chronology, key details, statements, figures, dates, locations, consequences and next steps only where supported.
- Use several paragraphs and useful <h2> headings for a longer report.
- Do not invent facts, quotes, statistics, dates, reactions or URLs.
- Do not fabricate quotations. Prefer paraphrase.
- Write an original synthesis rather than copying source wording.
- For political material, remain neutral and descriptive.
- Include useful inline links using ONLY the exact supplied source URLs.
- Return ONLY valid JSON: {{"body_html":"..."}}
- body_html may contain <p>, <h2>, <ul>, <li>, <strong>, <em> and <a> tags. No html/head/body/script/style/img tags.

SOURCE EVIDENCE:
{json.dumps(evidence, ensure_ascii=False)}'''

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{AI_MODEL}:generateContent?key={urllib.parse.quote(key)}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    data = json.dumps(payload).encode()
    last_error = None
    for attempt in range(3):
        request = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read())
            return json.loads(result["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            delay = 8 * (2 ** attempt)
            print(f"Gemini HTTP {exc.code}; retrying in {delay}s")
            time.sleep(delay)
    raise last_error


def expand_file(path: Path) -> bool:
    markup = path.read_text(encoding="utf-8")
    match = re.search(r'<h1>(.*?)</h1>', markup, re.I | re.S)
    if not match:
        return False
    title = visible_text(match.group(1))
    summary_match = re.search(r'<p><strong>(.*?)</strong></p>', markup, re.I | re.S)
    summary = visible_text(summary_match.group(1)) if summary_match else ""
    body_match = re.search(r'</figure>(.*?)(?:<hr><h2>Sources</h2>|<h2>Sources</h2>)', markup, re.I | re.S)
    if not body_match:
        return False
    existing_body = body_match.group(1)
    if word_count(existing_body) >= MIN_WORDS:
        return False

    category_match = re.search(r'<p>([^<]+) · [^<]+</p>', markup, re.I)
    category = visible_text(category_match.group(1)) if category_match else "News"
    sources = source_records(markup)
    if len(sources) < 2:
        print(f"Skipping {path.name}: fewer than two cited sources")
        return False

    print(f"Expanding {path.name}: {word_count(existing_body)} words")
    result = call_gemini(title, summary, category, sources)
    body_html = result.get("body_html", "").strip()
    if not body_html:
        raise RuntimeError("Gemini returned an empty body")
    if word_count(body_html) < 350:
        raise RuntimeError(f"Gemini returned only {word_count(body_html)} words")

    # Replace only the story body between the hero figure and Sources section.
    updated = markup[: body_match.start(1)] + "<p><strong>" + html.escape(summary) + "</strong></p>" + body_html + markup[body_match.end(1):]
    path.write_text(updated, encoding="utf-8")
    print(f"Expanded to {word_count(body_html)} words")
    return True


def main():
    changed = 0
    checked = 0
    for path in sorted(NEWS_DIR.glob("*.html")):
        checked += 1
        try:
            if expand_file(path):
                changed += 1
        except Exception as exc:
            print(f"ERROR {path.name}: {exc}")
    print(f"Existing-news expansion checked={checked} changed={changed}")


if __name__ == "__main__":
    main()

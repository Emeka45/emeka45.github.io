from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import urllib.error
import email.utils
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
INDEX = ARTICLES / "index.json"
REPORT_DIR = ROOT / "articles-data"
REPORT = REPORT_DIR / "run-report.json"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
SITE = "https://emeka45.github.io"
CATEGORIES = [
    "Psychology & Human Behaviour", "Relationships & Family", "Lifestyle",
    "Money & Work", "Education", "Health & Wellness", "Technology & Modern Life",
    "Nigerian & African Society", "Culture & Entertainment", "Religion & Meaning",
    "Practical Explainers", "Personal Development"
]
TOPIC_SEEDS = [
    ("Psychology & Human Behaviour", "Why small everyday routines can feel more comforting than big changes"),
    ("Relationships & Family", "The quiet habits that help people feel listened to in a conversation"),
    ("Lifestyle", "How people are redefining what a balanced day actually looks like"),
    ("Money & Work", "Why a realistic budget often works better than a perfect one"),
    ("Education", "How to build a study routine that survives a busy week"),
    ("Health & Wellness", "What to consider before turning a wellness trend into a daily habit"),
    ("Technology & Modern Life", "How to make a smartphone feel less distracting without abandoning it"),
    ("Nigerian & African Society", "How shared responsibilities shape everyday life in Nigerian households"),
    ("Culture & Entertainment", "Why familiar stories keep finding new audiences"),
    ("Religion & Meaning", "How people make space for reflection in a busy modern life"),
    ("Practical Explainers", "What people should understand before trusting a viral online claim"),
    ("Personal Development", "Why steady progress can be more useful than waiting for motivation"),
]

def load_index():
    if INDEX.exists():
        try:
            data = json.loads(INDEX.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []
    return []

def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:90].strip("-") or "article"

def request_article(topic, category, existing_titles):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it as a GitHub Actions secret.")
    prompt = f"""You are the independent long-form features desk for C. O. Eric, not the breaking-news desk.
Write one original, engaging, well-structured feature article about the topic below. Use the readable, conversational editorial FORMAT of a quality lifestyle publication: curiosity-led headline, compelling opening, a clear central idea, descriptive section headings, specific examples, useful context, and a satisfying ending. Do not imitate or reproduce any publisher's wording.

TOPIC: {topic}
CATEGORY: {category}
SITE: C. O. Eric
DATE: {dt.date.today().isoformat()}

EDITORIAL REQUIREMENTS
- Aim for 900–1,300 words when the subject supports it; never pad or repeat ideas.
- Open with a relatable situation or a sharp observation, then explain why the subject matters.
- Use 4–7 useful H2 subheadings and readable paragraphs.
- Make the article about the requested subject, not automatically about generations or age groups.
- Use a warm, intelligent, human voice; avoid robotic transitions, clichés, clickbait promises and generic filler.
- Be genuinely useful and original. Explain nuance and acknowledge meaningful limitations.
- Do not invent surveys, statistics, studies, experts, quotations, source URLs or personal experiences.
- If a specific factual claim requires current evidence and you cannot substantiate it, omit it or clearly describe it as general context rather than a verified fact.
- For health, legal, money and safety subjects, be cautious, distinguish general information from professional advice, and avoid unsupported definitive claims.
- No plagiarism, close paraphrasing, fabricated citations, deceptive claims, explicit sexual content or graphic gore.
- If you provide references, use only URLs you know are real and directly relevant. Prefer a short source list to invented inline links. If unsure, return an empty sources array.
- Write clean HTML for body_html using only p, h2, h3, ul, ol, li, strong, em, blockquote, and a tags. Do not include a full document, scripts, styles, images, or forms.
- title must be clear and appealing, not misleading. summary must be 140–220 characters. meta_description should be 140–160 characters where possible.
- Avoid duplicating these existing article titles: {json.dumps(existing_titles[-80:], ensure_ascii=False)}

Return ONLY valid JSON with this schema:
{{"publish":true,"reason":"...","title":"...","category":"...","summary":"...","meta_description":"...","body_html":"...","sources":[{{"title":"...","url":"https://..."}}],"tags":["..."]}}
Set publish=false if the topic cannot be responsibly handled as an original useful article.
"""
    payload = {
        "systemInstruction": {"parts": [{"text": "You are a careful professional feature editor. Output valid JSON only. Never fabricate evidence."}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.75}
    }
    # Try a short, ordered model fallback list. A quota limit can apply to one
    # model while another model in the same project may still have capacity.
    models = []
    for candidate in (MODEL, "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"):
        if candidate not in models:
            models.append(candidate)
    last_error = None
    for model in models:
        endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + urllib.parse.quote(model, safe="") + ":generateContent"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
            method="POST"
        )
        print(f"Trying Gemini model: {model}")
        # Retry transient service/rate-limit errors, then fall back to another model.
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    data = json.loads(response.read().decode("utf-8"))
                candidates = data.get("candidates") or []
                if not candidates:
                    feedback = data.get("promptFeedback", {})
                    raise RuntimeError(
                        "Gemini returned no article candidate. "
                        + json.dumps(feedback, ensure_ascii=False)[:700]
                    )
                parts = candidates[0].get("content", {}).get("parts", [])
                raw = next((part.get("text") for part in parts if isinstance(part, dict) and part.get("text")), None)
                if not raw:
                    finish = candidates[0].get("finishReason", "unknown")
                    raise RuntimeError(f"Gemini returned no text (finishReason={finish}).")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Gemini returned invalid JSON: {exc}") from exc
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                message = error_body
                try:
                    error_json = json.loads(error_body)
                    message = error_json.get("error", {}).get("message", error_body)
                    status = str(error_json.get("error", {}).get("status", ""))
                except (ValueError, AttributeError):
                    status = ""
                detail = str(message)[:900]
                lower = (detail + " " + status).lower()
                if exc.code == 429 and any(term in lower for term in (
                    "quota", "resource_exhausted", "requests per day",
                    "daily limit", "limit: 0", "billing"
                )):
                    raise RuntimeError(
                        "Gemini API quota/rate limit is exhausted for this key or project "
                        f"(HTTP 429). Wait for the quota reset or check the key's API quota. Details: {detail}"
                    ) from exc
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f"Gemini API request failed (HTTP {exc.code}): {detail}") from exc
                delay = min(60, 15 * (2 ** attempt))
                retry_after = exc.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(5, min(90, int(retry_after)))
                    except ValueError:
                        try:
                            retry_at = email.utils.parsedate_to_datetime(retry_after)
                            if retry_at.tzinfo is None:
                                retry_at = retry_at.replace(tzinfo=dt.timezone.utc)
                            delay = max(5, min(90, int((retry_at - dt.datetime.now(dt.timezone.utc)).total_seconds())))
                        except (TypeError, ValueError, OverflowError):
                            pass
                print(f"Gemini transient HTTP {exc.code}; retrying in {delay}s (attempt {attempt + 1}/3). Details: {detail[:300]}")
                time.sleep(delay)

    raise RuntimeError(
        "Article generation failed with all configured Gemini models. "
        "Check API model availability and free-tier quota. Last error: "
        + str(last_error or "No model returned a usable article.")[:700]
    )

def safe_body(raw, sources):
    allowed = {"p", "h2", "h3", "ul", "ol", "li", "strong", "em", "blockquote", "a"}
    source_urls = {s.get("url") for s in sources if isinstance(s, dict) and isinstance(s.get("url"), str)}
    # Accept only a small set of structural tags; rebuild all attributes rather than trusting model HTML.
    token_re = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*)>")
    out, pos = [], 0
    for match in token_re.finditer(str(raw or "")):
        out.append(html.escape(str(raw or "")[pos:match.start()]))
        closing, tag, attrs = match.groups()
        tag = tag.lower()
        if tag not in allowed:
            pos = match.end()
            continue
        if tag == "a" and not closing:
            href_match = re.search(r"""href\s*=\s*["']([^"']+)["']""", attrs, re.I)
            href = html.unescape(href_match.group(1)) if href_match else ""
            if href in source_urls and href.startswith("https://"):
                out.append('<a href="' + html.escape(href, quote=True) + '" rel="noopener noreferrer">')
            else:
                out.append("<span>")
        elif tag == "a" and closing:
            out.append("</a>")
        elif tag in {"ul", "ol", "p", "h2", "h3", "li", "strong", "em", "blockquote"}:
            out.append("</" + tag + ">" if closing else "<" + tag + ">")
        pos = match.end()
    out.append(html.escape(str(raw or "")[pos:]))
    cleaned = "".join(out)
    cleaned = re.sub(r"(?:<p>\s*</p>\s*)+", "", cleaned)
    return cleaned

def page_html(item):
    title = html.escape(item["title"])
    summary = html.escape(item["summary"])
    category = html.escape(item["category"])
    date = html.escape(item["date"])
    canonical = SITE + "/articles/" + urllib.parse.quote(item["file"])
    sources = item.get("sources", [])
    source_html = ""
    if sources:
        lis = []
        for source in sources:
            url = source.get("url", "")
            name = source.get("title") or url
            if isinstance(url, str) and url.startswith("https://"):
                lis.append('<li><a href="' + html.escape(url, quote=True) + '" rel="noopener noreferrer">' + html.escape(name) + '</a></li>')
        if lis:
            source_html = '<section class="sources"><h2>Sources & further reading</h2><ul>' + "".join(lis) + '</ul></section>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | C. O. Eric Articles</title><meta name="description" content="{html.escape(item.get("meta_description") or item["summary"], quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}"><meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:description" content="{summary}"><meta property="og:url" content="{html.escape(canonical, quote=True)}">
<style>:root{{--ink:#182033;--muted:#667085;--line:#e7e9ef;--accent:#6541c8;--paper:#fff;--bg:#f7f7fb}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:18px/1.8 Georgia,'Times New Roman',serif}}a{{color:var(--accent)}}header,main,footer{{width:min(850px,92%);margin:auto}}header{{padding:24px 0;border-bottom:1px solid var(--line);font:700 15px/1.5 system-ui,sans-serif}}header a{{text-decoration:none}}.hero{{padding:54px 0 30px}}.tag{{font:800 12px/1.4 system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}}h1{{font:800 clamp(2.2rem,7vw,4rem)/1.08 system-ui,sans-serif;letter-spacing:-.045em;margin:14px 0}}.dek{{font:20px/1.6 system-ui,sans-serif;color:#515b70}}.meta{{font:14px system-ui,sans-serif;color:var(--muted);margin-top:18px}}article{{background:var(--paper);padding:clamp(22px,5vw,56px);border:1px solid var(--line);border-radius:20px;box-shadow:0 12px 36px #1018280b}}article h2{{font:750 1.55rem/1.25 system-ui,sans-serif;letter-spacing:-.025em;margin-top:2em}}article h3{{font:700 1.2rem system-ui,sans-serif}}article p{{margin:0 0 1.25em}}article li{{margin:.4em 0}}.sources{{font:16px/1.6 system-ui,sans-serif;border-top:1px solid var(--line);margin-top:35px;padding-top:15px}}.sources h2{{font-size:1.2rem}}footer{{padding:30px 0 55px;font:14px system-ui,sans-serif;color:var(--muted)}}.back{{display:inline-block;margin-top:20px;font:700 14px system-ui,sans-serif}}@media(max-width:600px){{body{{font-size:17px}}.hero{{padding-top:35px}}article{{border-radius:14px}}}}</style></head>
<body><header><a href="../index.html">C. O. Eric</a> / <a href="../articles.html">Articles</a></header>
<main><div class="hero"><div class="tag">{category}</div><h1>{title}</h1><div class="dek">{summary}</div><div class="meta">By C. O. Eric · {date} · Feature article</div></div>
<article>{item["body_html"]}{source_html}</article><a class="back" href="../articles.html">← More articles</a></main>
<footer>© C. O. Eric · Original features and explainers. <a href="../editorial-policy.html">Editorial policy</a></footer></body></html>'''

def update_sitemap(filename):
    sitemap = ROOT / "sitemap.xml"
    url = SITE + "/articles/" + urllib.parse.quote(filename)
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        if url not in text:
            text = text.replace("</urlset>", "<url><loc>" + html.escape(url) + "</loc></url>\n</urlset>")
            sitemap.write_text(text, encoding="utf-8")

def main():
    ARTICLES.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    items = load_index()
    titles = [x.get("title", "") for x in items]
    requested_topic = os.environ.get("ARTICLE_TOPIC", "").strip()
    requested_category = os.environ.get("ARTICLE_CATEGORY", "").strip()
    if requested_category and requested_category not in CATEGORIES:
        requested_category = "Lifestyle"
    if requested_topic:
        category, topic = requested_category or "Lifestyle", requested_topic
    else:
        existing = {x.get("topic_key") for x in items}
        offset = dt.date.today().toordinal() % len(TOPIC_SEEDS)
        candidates = TOPIC_SEEDS[offset:] + TOPIC_SEEDS[:offset]
        category, topic = next((c, t) for c, t in candidates if slugify(t) not in existing) if any(slugify(t) not in existing for c, t in candidates) else candidates[0]
    report = {"date": dt.datetime.now(dt.timezone.utc).isoformat(), "topic": topic, "category": category, "published": False}
    try:
        article = request_article(topic, category, titles)
        if not article.get("publish"):
            report.update({"status": "held", "reason": article.get("reason", "Editorial review requested.")})
        elif not article.get("title") or not article.get("body_html") or len(re.sub(r"<[^>]+>", " ", article.get("body_html", "")).split()) < 450:
            report.update({"status": "held", "reason": "Generated article failed minimum completeness checks."})
        else:
            title = str(article["title"]).strip()
            base = slugify(title)
            slug = base
            used = {x.get("file") for x in items}
            suffix = 2
            while slug + ".html" in used:
                slug = f"{base}-{suffix}"
                suffix += 1
            sources = []
            for source in article.get("sources", [])[:8]:
                if isinstance(source, dict) and isinstance(source.get("url"), str) and source["url"].startswith("https://"):
                    sources.append({"title": str(source.get("title") or source["url"])[:180], "url": source["url"]})
            record = {
                "title": title[:180],
                "summary": str(article.get("summary") or "")[:300],
                "meta_description": str(article.get("meta_description") or article.get("summary") or "")[:220],
                "category": category,
                "date": dt.date.today().isoformat(),
                "file": slug + ".html",
                "topic_key": slugify(topic),
                "tags": [str(x)[:60] for x in article.get("tags", [])[:10]],
                "sources": sources,
                "body_html": safe_body(article["body_html"], sources)
            }
            if len(re.sub(r"<[^>]+>", " ", record["body_html"]).split()) < 450:
                raise ValueError("Article was too short after HTML sanitization.")
            (ARTICLES / record["file"]).write_text(page_html(record), encoding="utf-8")
            update_sitemap(record["file"])
            items.insert(0, {k: record[k] for k in ("title", "summary", "category", "date", "file", "tags")})
            items = items[:300]
            INDEX.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report.update({"status": "published", "published": True, "title": title, "file": record["file"], "word_count": len(re.sub(r"<[^>]+>", " ", record["body_html"]).split())})
    except Exception as exc:
        report.update({"status": "error", "error": str(exc)[:500]})
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

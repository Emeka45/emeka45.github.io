from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlparse

if __package__:
    from . import ai_newsroom
else:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ai_newsroom

_original_sanitize = ai_newsroom.sanitize_body_html

NIGERIA_CATEGORIES = {
    'Nigeria Politics', 'Education', 'Business & Economy', 'Security & Crime',
    'Health', 'Agriculture'
}


def nigeria_category(category: str) -> bool:
    return category.startswith('Nigeria ') or category in NIGERIA_CATEGORIES


def source_domain(item: dict) -> str:
    url = item.get('url', '')
    parsed = urlparse(url)
    host = parsed.netloc.lower().split('@')[-1].split(':')[0]
    if host.startswith('www.'):
        host = host[4:]
    if host in {'news.google.com', 'google.com'}:
        source = item.get('source') or item.get('publisher') or item.get('source_name')
        if source:
            return re.sub(r'[^a-z0-9.-]+', '-', str(source).lower()).strip('-')
    return host


def enrich_source_identity(item: dict) -> dict:
    item = dict(item)
    item['domain'] = source_domain(item)
    return item


def broader_corroboration(item, all_items):
    item = enrich_source_identity(item)
    matches = []
    for other_raw in all_items:
        other = enrich_source_identity(other_raw)
        if other['url'] == item['url'] or other['domain'] == item['domain']:
            continue
        same_category = other.get('category') == item.get('category')
        both_nigeria = nigeria_category(item.get('category', '')) and nigeria_category(other.get('category', ''))
        if not same_category and not both_nigeria:
            continue
        if not ai_newsroom.event_match(item, other):
            continue
        matches.append(other)
    matches.sort(key=lambda other: ai_newsroom.similarity(item, other), reverse=True)
    return matches[:3]


ai_newsroom.find_corroboration = broader_corroboration

EXPANDED_FEEDS = {
    'Nigeria - National & States': ['https://rss.punchng.com/v1/category/latest_news', 'https://thereporter.com.ng/rss/category/news'],
    'Nigeria - Law & Justice': ['https://news.google.com/rss/search?q=Nigeria+law+justice+court+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://thereporter.com.ng/rss/category/news'],
    'Nigeria - Energy & Power': ['https://news.google.com/rss/search?q=Nigeria+energy+power+electricity+oil+gas+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://rss.punchng.com/v1/category/business'],
    'Nigeria - Transport & Infrastructure': ['https://news.google.com/rss/search?q=Nigeria+transport+infrastructure+road+rail+airport+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://rss.punchng.com/v1/category/latest_news'],
    'Nigeria - Environment & Climate': ['https://news.google.com/rss/search?q=Nigeria+environment+climate+flood+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://thereporter.com.ng/rss/category/news'],
    'Nigeria - Jobs & Labour': ['https://news.google.com/rss/search?q=Nigeria+jobs+labour+employment+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://rss.punchng.com/v1/category/business'],
    'Nigeria - Finance & Markets': ['https://thereporter.com.ng/rss/category/finance-101', 'https://rss.punchng.com/v1/category/business'],
    'Nigeria - Culture & Heritage': ['https://news.google.com/rss/search?q=Nigeria+culture+heritage+arts+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://thereporter.com.ng/rss/category/Entertainment-&-Lifestyle'],
    'Nigeria - Tourism & Travel': ['https://news.google.com/rss/search?q=Nigeria+tourism+travel+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://thereporter.com.ng/rss/category/Entertainment-&-Lifestyle'],
    'Nigeria - Religion & Interfaith': ['https://news.google.com/rss/search?q=Nigeria+religion+interfaith+faith+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://rss.punchng.com/v1/category/latest_news'],
    'Nigeria - Youth & Society': ['https://news.google.com/rss/search?q=Nigeria+youth+society+community+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://thereporter.com.ng/rss/category/news'],
    'Nigeria - Real Estate & Housing': ['https://news.google.com/rss/search?q=Nigeria+real+estate+housing+property+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://rss.punchng.com/v1/category/business'],
    'Nigeria - Food & Consumer': ['https://news.google.com/rss/search?q=Nigeria+food+prices+consumer+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://rss.punchng.com/v1/category/business'],
}
ai_newsroom.FEEDS.update(EXPANDED_FEEDS)


def _source_parts(sources):
    normalized = []
    for source in sources or []:
        if isinstance(source, str):
            normalized.append({'url': source, 'title': source})
        elif isinstance(source, dict):
            normalized.append(source)
    return normalized


def sanitize_with_fallback(html: str, sources=None) -> str:
    source_records = _source_parts(sources)
    allowed_urls = [source.get('url', '') for source in source_records if source.get('url')]
    cleaned = _original_sanitize(html, allowed_urls)
    if source_records and 'Source:' not in cleaned:
        links = []
        for source in source_records[:3]:
            title = source.get('title') or source.get('name') or 'Source'
            url = source.get('url', '#')
            links.append(f'<li><a href="{url}" rel="noopener noreferrer">{title}</a></li>')
        if links:
            cleaned += '<p><strong>Sources</strong></p><ul>' + ''.join(links) + '</ul>'
    return cleaned


ai_newsroom.sanitize_body_html = sanitize_with_fallback


def detailed_ask_ai(sources):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is missing')

    prompt = '''You are the C. O. Eric AI Newsroom, a professional Nigeria-first digital newsroom.
Create a detailed, original news report ONLY when the supplied source records materially corroborate the same central event.

ARTICLE LENGTH AND DEPTH:
- Write a substantial report, normally about 600-1000 words when the available evidence supports that length.
- For a smaller story, use about 400-600 words rather than padding it with repetition.
- Never invent information just to reach a word count.
- Use multiple paragraphs, not one giant block.
- Start with a clear news lead explaining what happened and why it matters.
- Add factual context and relevant background that can be supported by the supplied sources.
- Explain important details, developments, statements, decisions, figures, dates, locations, or consequences when the sources provide them.
- End with what is known about the next step or what remains unresolved, if the sources support that.
- Use useful section headings when appropriate, especially for longer reports.

STRICT EVIDENCE RULES:
- At least two different publisher domains must materially support the same central event.
- Never treat two stories as corroboration merely because they mention the same person, place, company, government, or broad topic.
- The sources must overlap on the actual event, announcement, incident, transaction, study, decision, or development.
- Use only facts that are supported by the supplied source records.
- Do not invent facts, quotes, statistics, dates, people, places, reactions, or URLs.
- Do not fabricate quotes. If a source provides a quote, paraphrase it unless an exact short quotation is clearly necessary.
- Do not copy or lightly rewrite source wording. Write an original synthesis.
- Clearly distinguish confirmed facts from analysis or uncertainty.
- Do not turn speculation into fact.
- No sexually explicit or pornographic content. No graphic gore.
- Treat religious subjects neutrally and respectfully.
- For political stories, report positions and documented actions neutrally without endorsements or persuasion.

LINKING RULES:
- body_html MUST contain useful inline hyperlinks to supplied source URLs where relevant.
- Every href in body_html MUST exactly match one of the supplied source URLs.
- Do not create links to unsupplied pages.

HTML RULES:
- body_html should contain readable paragraphs using <p> tags.
- Use <h2> for useful subheadings when the story is long enough to benefit from them.
- Use <ul>/<li> only when a factual list genuinely improves readability.
- Do not include <html>, <head>, <body>, <script>, <style>, <img>, or form elements.

Return ONLY valid JSON with this schema:
{"publish":true|false,"reason":"...","category":"...","title":"...","summary":"...","body_html":"...","sources":[{"name":"...","url":"..."}],"confidence":0-100}

SOURCE RECORDS:
''' + json.dumps(sources, ensure_ascii=False)

    endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/' + ai_newsroom.AI_MODEL + ':generateContent?key=' + urllib.parse.quote(key)
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json'}
    }
    body = json.dumps(payload).encode()
    last_error = None
    for attempt in range(3):
        req = urllib.request.Request(endpoint, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
            return json.loads(data['candidates'][0]['content']['parts'][0]['text'])
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            retry_after = exc.headers.get('Retry-After')
            try:
                delay = max(8, min(60, int(retry_after))) if retry_after else 8 * (2 ** attempt)
            except ValueError:
                delay = 8 * (2 ** attempt)
            print(f'Detailed AI transient HTTP {exc.code}; retrying in {delay}s (attempt {attempt + 1}/3)')
            time.sleep(delay)
    raise last_error


ai_newsroom.ask_ai = detailed_ask_ai


def normalize_and_seo():
    if hasattr(ai_newsroom, 'apply_cloudflare_seo'):
        ai_newsroom.apply_cloudflare_seo('https://emeka45-github-io.pages.dev/news')


if __name__ == '__main__':
    ai_newsroom.main()
    normalize_and_seo()

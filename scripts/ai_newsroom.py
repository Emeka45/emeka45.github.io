from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / 'news'
DATA = ROOT / 'newsroom-data'
STATE = DATA / 'state.json'
REPORT = DATA / 'run-report.json'
INDEX = NEWS / 'index.json'
NEWS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

AI_MODEL = 'gemini-3.5-flash-lite'
MAX_AI_CANDIDATES_PER_RUN = 20
USER_AGENT = 'COEricAI-Newsroom/2.0'
BLOCKED_TERMS = {'porn', 'pornography', 'xxx', 'explicit sex', 'sexual explicit', 'sex tape', 'nude leak', 'onlyfans', 'erotic', 'sexual fetish'}

FEEDS = {
    'Nigeria Politics': ['https://rss.punchng.com/v1/category/politics', 'https://thereporter.com.ng/rss/category/politics'],
    'Religion & Faith': ['https://news.google.com/rss/search?q=Nigeria+Christianity+church+faith+when:7d&hl=en-NG&gl=NG&ceid=NG:en', 'https://nscia.com.ng/category/news/feed/'],
    'Education': ['https://rss.punchng.com/v1/category/education', 'https://thereporter.com.ng/rss/category/education'],
    'Business & Economy': ['https://rss.punchng.com/v1/category/business', 'https://thereporter.com.ng/rss/category/business'],
    'Security & Crime': ['https://thereporter.com.ng/rss/category/security', 'https://rss.punchng.com/v1/category/latest_news'],
    'Health': ['https://rss.punchng.com/v1/category/health', 'https://thereporter.com.ng/rss/category/health'],
    'Agriculture': ['https://thereporter.com.ng/rss/category/agriculture', 'https://rss.punchng.com/v1/category/business'],
    'Technology': ['https://feeds.arstechnica.com/arstechnica/index', 'https://www.theverge.com/rss/index.xml'],
    'AI': ['https://www.technologyreview.com/feed/', 'https://www.theverge.com/rss/ai/index.xml'],
    'Science': ['https://www.sciencedaily.com/rss/all.xml', 'https://phys.org/rss-feed/'],
    'Gaming': ['https://www.polygon.com/rss/index.xml', 'https://www.eurogamer.net/feed'],
    'Anime': ['https://www.animenewsnetwork.com/all/rss.xml', 'https://www.animenewsnetwork.com/news/rss.xml'],
    'Sports': ['https://rss.punchng.com/v1/category/sports', 'https://thereporter.com.ng/rss/category/sports-2'],
    'Entertainment & Lifestyle': ['https://rss.punchng.com/v1/category/entertainment', 'https://news.google.com/rss/search?q=Nigeria+entertainment+celebrity+music+when:7d&hl=en-NG&gl=NG&ceid=NG:en'],
    'World': ['https://feeds.bbci.co.uk/news/world/rss.xml', 'https://www.theguardian.com/world/rss'],
}
STOPWORDS = {'the','a','an','and','or','of','to','in','on','for','with','from','by','at','is','are','as','new','news','after','into','over','its','this','that','will','has','have','how','why','what','who','their','they','it','be','about','more','than','says','said','amid','among','over','could','would','also','first','latest','report','reports'}


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'seen': []}


def save_state(state):
    state['seen'] = list(dict.fromkeys(state.get('seen', [])))[-2000:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def parse_feed(category, url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        items = []
        nodes = root.findall('.//item')
        if not nodes:
            nodes = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        for node in nodes[:20]:
            title = (node.findtext('title') or node.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
            link = (node.findtext('link') or '').strip()
            if not link:
                atom_link = node.find('{http://www.w3.org/2005/Atom}link')
                if atom_link is not None:
                    link = (atom_link.attrib.get('href') or '').strip()
            summary = (node.findtext('description') or node.findtext('{http://www.w3.org/2005/Atom}summary') or node.findtext('{http://www.w3.org/2005/Atom}content') or '').strip()
            source_node = node.find('source')
            source = (source_node.text or '').strip() if source_node is not None else ''
            if not source:
                source_node = node.find('{http://www.w3.org/2005/Atom}author')
                if source_node is not None:
                    source = (source_node.findtext('{http://www.w3.org/2005/Atom}name') or '').strip()
            if title and link:
                items.append({'category': category, 'title': re.sub('<[^>]+>', ' ', title), 'summary': re.sub('<[^>]+>', ' ', summary), 'url': link, 'source': source, 'domain': urllib.parse.urlparse(link).netloc.lower().removeprefix('www.')})
        return items, None
    except Exception as exc:
        return [], str(exc)


def tokens(text):
    return {x for x in re.findall(r'[a-z0-9]{3,}', text.lower()) if x not in STOPWORDS}


def similarity(a, b):
    aa, bb = tokens(a['title'] + ' ' + a['summary']), tokens(b['title'] + ' ' + b['summary'])
    if not aa or not bb:
        return 0
    return len(aa & bb) / max(1, min(len(aa), len(bb)))


def event_match(a, b):
    at = tokens(a.get('title', ''))
    bt = tokens(b.get('title', ''))
    shared_title = at & bt
    title_overlap = len(shared_title) / max(1, min(len(at), len(bt)))
    if len(shared_title) >= 3 and title_overlap >= 0.50:
        return True
    combined = similarity(a, b)
    shared_all = tokens(a.get('title', '') + ' ' + a.get('summary', '')) & tokens(b.get('title', '') + ' ' + b.get('summary', ''))
    return combined >= 0.38 and len(shared_all) >= 5


def find_corroboration(item, all_items):
    matches = []
    for other in all_items:
        if other['url'] == item['url'] or other.get('domain') == item.get('domain'):
            continue
        if other.get('category') != item.get('category') and not (item.get('category', '').startswith('Nigeria ') and other.get('category', '').startswith('Nigeria ')):
            continue
        if event_match(item, other):
            matches.append(other)
    matches.sort(key=lambda other: similarity(item, other), reverse=True)
    return matches[:3]


def ask_ai(sources):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is missing')
    prompt = '''You are the C. O. Eric AI Newsroom, a broad Nigeria-first digital newsroom. Create a concise original news article only when the supplied source records materially corroborate the same central event.

STRICT RULES:
- At least two different publisher domains must materially support the same central event.
- Never treat two stories as corroboration merely because they mention the same person, place, company, government, or broad topic.
- The sources must overlap on the actual event, announcement, incident, transaction, study, decision, or development.
- Do not publish rumor, speculation, exaggeration, fabricated facts, fabricated quotes, or invented URLs.
- Do not copy or lightly rewrite source wording.
- No sexually explicit or pornographic content. No graphic gore.
- Distinguish confirmed facts from analysis.
- Use only the supplied source URLs.
- Treat religious subjects neutrally and respectfully.

LINKING RULES:
- body_html MUST contain at least one useful inline hyperlink to a supplied source URL.
- Every href in body_html MUST exactly match one of the supplied source URLs.

Return ONLY valid JSON with this schema:
{"publish":true|false,"reason":"...","category":"...","title":"...","summary":"...","body_html":"...","sources":[{"name":"...","url":"..."}],"confidence":0-100}

SOURCE RECORDS:
''' + json.dumps(sources, ensure_ascii=False)
    endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/' + AI_MODEL + ':generateContent?key=' + urllib.parse.quote(key)
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json'}}
    body = json.dumps(payload).encode()
    last_error = None
    for attempt in range(3):
        req = urllib.request.Request(endpoint, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
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
            print(f'AI transient HTTP {exc.code}; retrying in {delay}s (attempt {attempt + 1}/3)')
            time.sleep(delay)
    raise last_error


def contains_blocked(text):
    low = text.lower()
    return any(term in low for term in BLOCKED_TERMS)


def extract_links(body_html):
    return [html.unescape(u) for u in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>', body_html or '', flags=re.I)]


def sanitize_body_html(body_html, allowed_urls):
    allowed = set(allowed_urls)
    def replace_link(match):
        attrs, label = match.group(1), match.group(2)
        href_match = re.search(r'\bhref=["\']([^"\']+)["\']', attrs, flags=re.I)
        if not href_match or html.unescape(href_match.group(1)) not in allowed:
            return html.escape(re.sub(r'<[^>]+>', '', label))
        href = html.escape(html.unescape(href_match.group(1)), quote=True)
        text = re.sub(r'<[^>]+>', '', label).strip()
        return f'<a href="{href}" rel="nofollow noopener" target="_blank">{html.escape(text)}</a>'
    body_html = re.sub(r'<a\b([^>]*)>(.*?)</a>', replace_link, body_html or '', flags=re.I | re.S)
    body_html = re.sub(r'<\s*(script|iframe|object|embed|form)\b[^>]*>.*?<\s*/\s*\1\s*>', '', body_html, flags=re.I | re.S)
    body_html = re.sub(r'\s+on[a-z]+\s*=\s*["\'][^"\']*["\']', '', body_html, flags=re.I)
    return body_html


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:90] or 'story'


def clean_category(value):
    value = html.unescape(re.sub('<[^>]+>', '', value or '')).strip()
    return re.sub(r'^←\s*C\. O\. Eric Newsroom\s*', '', value, flags=re.I).strip() or 'News'


def update_index():
    items = []
    for p in NEWS.glob('*.html'):
        try:
            raw = p.read_text(encoding='utf-8')
            title = re.search(r'<h1>(.*?)</h1>', raw, re.S)
            summary = re.search(r'<p><strong>(.*?)</strong></p>', raw, re.S)
            category = re.search(r'<p>(.*?)\s*·\s*', raw, re.S)
            title_text = html.unescape(re.sub('<[^>]+>', '', title.group(1))) if title else p.stem
            summary_text = html.unescape(re.sub('<[^>]+>', '', summary.group(1))) if summary else ''
            category_text = clean_category(category.group(1) if category else 'News')
            image = NEWS / 'images' / f'{p.stem}-source.jpg'
            item = {
                'file': p.name,
                'title': title_text,
                'summary': summary_text,
                'category': category_text,
                'date': dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime('%d %b %Y'),
            }
            if image.exists():
                item['image'] = f'news/images/{image.name}'
            items.append(item)
        except Exception:
            continue
    items.sort(key=lambda x: x['file'], reverse=True)
    unique = []
    for item in items:
        if not any(event_match(item, old) for old in unique):
            unique.append(item)
    INDEX.write_text(json.dumps(unique[:100], ensure_ascii=False, indent=2), encoding='utf-8')


def publish(article):
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime('%Y-%m-%d')
    sid = hashlib.sha256((article['title'] + now.isoformat()).encode()).hexdigest()[:10]
    path = NEWS / f'{stamp}-{slug(article["title"])}-{sid}.html'
    sources_html = ''.join(f'<li><a href="{html.escape(s["url"], quote=True)}" rel="nofollow noopener" target="_blank">{html.escape(s["name"])}</a></li>' for s in article['sources'])
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(article['summary'], quote=True)}"><title>{html.escape(article['title'])} — C. O. Eric News</title></head><body><main><p><a href="../newsroom.html">← C. O. Eric Newsroom</a></p><p>{html.escape(article['category'])} · {now.strftime('%d %b %Y')}</p><h1>{html.escape(article['title'])}</h1><p><strong>{html.escape(article['summary'])}</strong></p>{article['body_html']}<hr><h2>Sources</h2><ul>{sources_html}</ul><p>This article was produced by the C. O. Eric AI Newsroom from the cited sources. It is published only after automated evidence and safety checks.</p></main></body></html>'''
    path.write_text(doc, encoding='utf-8')
    return path

import datetime as dt
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / 'news'
DATA = ROOT / 'newsroom-data'
STATE = DATA / 'state.json'
INDEX = NEWS / 'index.json'
NEWS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

FEEDS = {
    'Technology': 'https://feeds.arstechnica.com/arstechnica/index',
    'AI': 'https://www.technologyreview.com/feed/',
    'Science': 'https://www.sciencedaily.com/rss/top/science.xml',
    'Gaming': 'https://www.polygon.com/rss/index.xml',
    'Anime': 'https://www.animenewsnetwork.com/all/rss.xml',
    'World': 'https://feeds.bbci.co.uk/news/world/rss.xml',
}
BLOCKED_TERMS = ['porn', 'pornography', 'xxx', 'explicit sex', 'sexual explicit', 'sex tape', 'nude leak', 'onlyfans', 'erotic', 'sexual fetish']


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'COEricAI-Newsroom/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse_feed(category, url):
    try:
        root = ET.fromstring(fetch(url))
    except Exception as exc:
        print('Feed failed:', category, exc)
        return []
    out = []
    for item in root.findall('.//item')[:12]:
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        desc = re.sub(r'<[^>]+>', ' ', item.findtext('description') or '')
        desc = html.unescape(re.sub(r'\s+', ' ', desc)).strip()
        pub = (item.findtext('pubDate') or '').strip()
        if title and link:
            out.append({'category': category, 'title': title, 'url': link, 'summary': desc[:1200], 'published': pub})
    return out


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'seen': []}


def save_state(state):
    state['seen'] = state['seen'][-500:]
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def ask_ai(sources):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is not configured')
    prompt = '''You are the autonomous C. O. Eric Newsroom editor. Produce ONE original news article only if the evidence is strong enough.

HARD RULES:
- Never publish rumor, speculation, exaggeration, fabricated claims, fabricated quotes, or unsupported allegations as fact.
- Require at least TWO independent source records supplied below that materially support the central claim. If fewer than two independent sources support it, return publish=false.
- If sources materially conflict about the central fact, return publish=false.
- Do not invent facts, names, dates, numbers, quotes, URLs, or events.
- Do not copy or lightly rewrite source wording. Write a genuinely original synthesis.
- Do not publish sexually explicit or pornographic content, sexualized descriptions, or sexual-leak stories. If the story's central subject is sexual/explicit, return publish=false.
- Avoid graphic gore. If a story is sensitive but newsworthy, keep descriptions non-graphic.
- Distinguish confirmed facts from clearly labeled analysis. Prefer facts.
- Explain why the development matters.

Return ONLY valid JSON with this schema:
{"publish":true|false,"reason":"...","category":"...","title":"...","summary":"...","body_html":"...","sources":[{"name":"...","url":"..."}],"confidence":0-100}

SOURCE RECORDS:
''' + json.dumps(sources, ensure_ascii=False)
    endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + urllib.parse.quote(key)
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}}
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return json.loads(data['candidates'][0]['content']['parts'][0]['text'])


def contains_blocked(text):
    low = text.lower()
    return any(term in low for term in BLOCKED_TERMS)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:90] or 'story'


def update_index():
    items = []
    for p in NEWS.glob('*.html'):
        try:
            raw = p.read_text(encoding='utf-8')
            title = re.search(r'<h1>(.*?)</h1>', raw, re.S)
            summary = re.search(r'<p><strong>(.*?)</strong></p>', raw, re.S)
            category = re.search(r'<p>(.*?) · ', raw, re.S)
            items.append({'file': p.name, 'title': html.unescape(re.sub('<[^>]+>', '', title.group(1))) if title else p.stem, 'summary': html.unescape(re.sub('<[^>]+>', '', summary.group(1))) if summary else '', 'category': html.unescape(category.group(1)) if category else 'News', 'date': dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime('%d %b %Y')})
        except Exception:
            continue
    items.sort(key=lambda x: x['file'], reverse=True)
    INDEX.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2), encoding='utf-8')


def publish(article):
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime('%Y-%m-%d')
    sid = hashlib.sha256((article['title'] + now.isoformat()).encode()).hexdigest()[:10]
    path = NEWS / f'{stamp}-{slug(article["title"])}-{sid}.html'
    sources_html = ''.join(f'<li><a href="{html.escape(s["url"], quote=True)}" rel="nofollow noopener" target="_blank">{html.escape(s["name"])}</a></li>' for s in article['sources'])
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(article['summary'], quote=True)}"><title>{html.escape(article['title'])} — C. O. Eric News</title></head><body><main><p><a href="../newsroom.html">← C. O. Eric Newsroom</a></p><p>{html.escape(article['category'])} · {now.strftime('%d %b %Y')}</p><h1>{html.escape(article['title'])}</h1><p><strong>{html.escape(article['summary'])}</strong></p>{article['body_html']}<hr><h2>Sources</h2><ul>{sources_html}</ul><p>This article was produced by the C. O. Eric AI Newsroom from the cited sources. It is published only after automated evidence and safety checks.</p></main></body></html>'''
    path.write_text(doc, encoding='utf-8')
    return path


def main():
    state = load_state()
    candidates = []
    for cat, feed in FEEDS.items():
        candidates.extend(parse_feed(cat, feed))
    fresh = [x for x in candidates if x['url'] not in state['seen']]
    for item in fresh[:8]:
        related = [x for x in candidates if x['category'] == item['category'] and x['url'] != item['url']]
        sources = [item] + related[:4]
        if contains_blocked(item['title'] + ' ' + item['summary']):
            state['seen'].append(item['url'])
            continue
        try:
            article = ask_ai(sources)
        except Exception as exc:
            print('AI failed:', exc)
            continue
        state['seen'].append(item['url'])
        text = article.get('title', '') + ' ' + article.get('summary', '') + ' ' + re.sub('<[^>]+>', ' ', article.get('body_html', ''))
        srcs = article.get('sources', [])
        if article.get('publish') is True and article.get('confidence', 0) >= 85 and len(srcs) >= 2 and not contains_blocked(text):
            print('PUBLISHED', publish(article))
        else:
            print('HELD/REJECTED:', article.get('reason', 'quality gate failed'))
    save_state(state)
    update_index()

if __name__ == '__main__':
    main()

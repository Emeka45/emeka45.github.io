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
MAX_AI_CANDIDATES_PER_RUN = 4
USER_AGENT = 'COEricAI-Newsroom/1.5'
BLOCKED_TERMS = {'porn', 'pornography', 'xxx', 'explicit sex', 'sexual explicit', 'sex tape', 'nude leak', 'onlyfans', 'erotic', 'sexual fetish'}

FEEDS = {
    'Technology': ['https://feeds.arstechnica.com/arstechnica/index', 'https://www.theverge.com/rss/index.xml'],
    'AI': ['https://www.technologyreview.com/feed/', 'https://www.theverge.com/rss/ai/index.xml'],
    'Science': ['https://www.sciencedaily.com/rss/all.xml', 'https://phys.org/rss-feed/'],
    'Gaming': ['https://www.polygon.com/rss/index.xml', 'https://www.eurogamer.net/feed'],
    'Anime': ['https://www.animenewsnetwork.com/all/rss.xml'],
    'World': ['https://feeds.bbci.co.uk/news/world/rss.xml', 'https://www.theguardian.com/world/rss'],
}
STOPWORDS = {'the','a','an','and','or','of','to','in','on','for','with','from','by','at','is','are','as','new','news','after','into','over','its','this','that','will','has','have','how','why','what','who','their','they','it','be','about','more','than','says','said'}


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
        for node in root.findall('.//item')[:15]:
            title = (node.findtext('title') or '').strip()
            link = (node.findtext('link') or '').strip()
            summary = (node.findtext('description') or '').strip()
            if title and link:
                items.append({'category': category, 'title': re.sub('<[^>]+>', ' ', title), 'summary': re.sub('<[^>]+>', ' ', summary), 'url': link, 'domain': urllib.parse.urlparse(link).netloc.lower().removeprefix('www.')})
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


def find_corroboration(item, all_items):
    matches = []
    for other in all_items:
        if other['url'] == item['url'] or other['category'] != item['category'] or other['domain'] == item['domain']:
            continue
        if similarity(item, other) >= 0.18:
            matches.append(other)
    return matches[:3]


def ask_ai(sources):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is missing')
    prompt = '''You are the C. O. Eric AI Newsroom. Create a concise original news article only when the supplied source records materially corroborate the same central event.

STRICT RULES:
- Do not publish rumor, speculation, exaggeration, fabricated facts, fabricated quotes, or invented URLs.
- At least two different publisher domains must materially support the same central event.
- Do not copy or lightly rewrite source wording.
- No sexually explicit or pornographic content. No graphic gore.
- Distinguish confirmed facts from analysis.
- Use only the supplied source URLs.

LINKING RULES:
- body_html MUST contain at least one useful inline hyperlink to a supplied source URL.
- Use a normal HTML anchor such as <a href="EXACT_SUPPLIED_URL">relevant source text</a>.
- Every href in body_html MUST exactly match one of the supplied source URLs.
- Never invent, alter, shorten, redirect, or track URLs.
- Link naturally to the first useful mention of the announcement, company, game, study, event, or other subject.
- Do not add scripts, iframes, forms, or external assets.

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
    # Decode HTML entities so URLs such as ?a=1&amp;b=2 compare exactly with feed URLs.
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
    started = dt.datetime.now(dt.timezone.utc)
    state = load_state()
    candidates = []
    feed_count = 0
    feed_success = 0
    feed_failures = []
    for cat, feeds in FEEDS.items():
        for feed in feeds:
            items, error = parse_feed(cat, feed)
            feed_count += 1
            if error:
                feed_failures.append({'category': cat, 'url': feed, 'error': error})
            else:
                feed_success += 1
            candidates.extend(items)

    fresh = [x for x in candidates if x['url'] not in state.get('seen', [])]
    ranked = [(len(find_corroboration(item, candidates)), item) for item in fresh]
    ranked.sort(key=lambda x: x[0], reverse=True)

    print('Feeds checked:', feed_count, 'successful:', feed_success, 'failed:', len(feed_failures))
    print('Collected:', len(candidates), 'items; fresh:', len(fresh))
    published_count = 0
    held_count = 0
    corroborated_count = 0
    ai_attempts = 0
    ai_failures = 0
    rejection_reasons = []

    for _, item in ranked[:MAX_AI_CANDIDATES_PER_RUN]:
        if contains_blocked(item['title'] + ' ' + item['summary']):
            state['seen'].append(item['url'])
            rejection_reasons.append('blocked source content')
            print('REJECTED blocked source:', item['title'])
            continue

        corroborators = find_corroboration(item, candidates)
        if not corroborators:
            held_count += 1
            rejection_reasons.append('no independent corroboration yet')
            print('RETRY LATER — no independent corroboration:', item['title'])
            continue

        corroborated_count += 1
        sources = [item] + corroborators
        ai_attempts += 1
        try:
            article = ask_ai(sources)
        except Exception as exc:
            ai_failures += 1
            print('AI failed:', exc)
            continue

        allowed_urls = {s['url'] for s in sources}
        article['body_html'] = sanitize_body_html(article.get('body_html', ''), allowed_urls)
        body_links = extract_links(article['body_html'])
        text = article.get('title', '') + ' ' + article.get('summary', '') + ' ' + re.sub('<[^>]+>', ' ', article.get('body_html', ''))
        srcs = article.get('sources', []) if isinstance(article.get('sources', []), list) else []
        supplied_urls = allowed_urls
        returned_urls = {s.get('url') for s in srcs if isinstance(s, dict)}
        domains = {urllib.parse.urlparse(u).netloc.lower().removeprefix('www.') for u in returned_urls if u}
        body_link_valid = bool(body_links) and set(body_links).issubset(supplied_urls)
        valid = article.get('publish') is True and article.get('confidence', 0) >= 85 and len(srcs) >= 2 and len(domains) >= 2 and returned_urls.issubset(supplied_urls) and body_link_valid and not contains_blocked(text)

        if valid:
            print('PUBLISHED', publish(article))
            published_count += 1
            state['seen'].append(item['url'])
        else:
            held_count += 1
            reason = article.get('reason', 'quality/link safety gate failed')
            if not body_link_valid:
                reason = 'article did not contain a valid inline link to a supplied source'
            rejection_reasons.append(reason)
            print('HELD/REJECTED:', reason)

    save_state(state)
    update_index()
    report = {
        'started_utc': started.isoformat(),
        'finished_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'model': AI_MODEL,
        'max_ai_candidates_per_run': MAX_AI_CANDIDATES_PER_RUN,
        'feed_count': feed_count,
        'feed_success_count': feed_success,
        'feed_failure_count': len(feed_failures),
        'feed_failures': feed_failures,
        'total_items': len(candidates),
        'fresh_items': len(fresh),
        'corroborated_candidates': corroborated_count,
        'ai_attempts': ai_attempts,
        'ai_failures': ai_failures,
        'held_or_rejected': held_count,
        'published_count': published_count,
        'rejection_reasons': rejection_reasons[-50:],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('RUN REPORT:', json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()

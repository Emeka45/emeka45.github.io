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
REPORT = DATA / 'run-report.json'
NEWS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

FEEDS = {
    'Technology': ['https://feeds.arstechnica.com/arstechnica/index', 'https://www.theverge.com/rss/index.xml'],
    'AI': ['https://www.technologyreview.com/feed/', 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml'],
    'Science': ['https://www.sciencedaily.com/rss/top/science.xml', 'https://phys.org/rss-feed/'],
    'Gaming': ['https://www.polygon.com/rss/index.xml', 'https://www.eurogamer.net/feed'],
    'Anime': ['https://www.animenewsnetwork.com/all/rss.xml', 'https://www.crunchyroll.com/news/rss'],
    'World': ['https://feeds.bbci.co.uk/news/world/rss.xml', 'https://www.theguardian.com/world/rss'],
}
BLOCKED_TERMS = ['porn', 'pornography', 'xxx', 'explicit sex', 'sexual explicit', 'sex tape', 'nude leak', 'onlyfans', 'erotic', 'sexual fetish']
STOPWORDS = {'about','after','again','against','being','could','first','from','have','into','more','most','other','over','said','same','some','than','that','their','there','these','they','this','those','through','under','what','when','where','which','while','with','would','will','your','news','new','says','has','its','are','and','for','the','was','were','you','how','why','who','today','latest','official'}


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'COEricAI-Newsroom/1.3'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse_feed(category, url):
    try:
        root = ET.fromstring(fetch(url))
    except Exception as exc:
        print('Feed failed:', category, url, exc)
        return [], str(exc)
    out = []
    for item in root.findall('.//item')[:15]:
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        desc = re.sub(r'<[^>]+>', ' ', item.findtext('description') or '')
        desc = html.unescape(re.sub(r'\s+', ' ', desc)).strip()
        pub = (item.findtext('pubDate') or '').strip()
        if title and link:
            domain = urllib.parse.urlparse(link).netloc.lower().removeprefix('www.')
            out.append({'category': category, 'title': title, 'url': link, 'summary': desc[:1200], 'published': pub, 'domain': domain})
    return out, None


def load_state():
    if STATE.exists():
        try:
            data = json.loads(STATE.read_text())
            return data if isinstance(data, dict) else {'seen': []}
        except Exception:
            pass
    return {'seen': []}


def save_state(state):
    state['seen'] = state.get('seen', [])[-1000:]
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def keywords(text):
    words = re.findall(r'[a-z0-9]{4,}', text.lower())
    return {w for w in words if w not in STOPWORDS}


def similarity(a, b):
    ka = keywords(a['title'] + ' ' + a['summary'])
    kb = keywords(b['title'] + ' ' + b['summary'])
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / max(1, min(len(ka), len(kb)))


def find_corroboration(item, candidates):
    matches = []
    for other in candidates:
        if other['url'] == item['url'] or other['domain'] == item['domain'] or other['category'] != item['category']:
            continue
        score = similarity(item, other)
        if score >= 0.18:
            matches.append((score, other))
    matches.sort(key=lambda x: x[0], reverse=True)
    return [other for _, other in matches[:4]]


def ask_ai(sources):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is not configured')
    prompt = '''You are the autonomous C. O. Eric Newsroom editor. Produce ONE original news article only if the evidence is strong enough.

HARD RULES:
- Never publish rumor, speculation, exaggeration, fabricated claims, fabricated quotes, or unsupported allegations as fact.
- At least TWO source records below must come from DIFFERENT publisher domains and materially support the SAME central event or claim.
- If the records are merely about the same broad topic but do not corroborate the same event, return publish=false.
- If sources materially conflict about the central fact, return publish=false.
- Do not invent facts, names, dates, numbers, quotes, URLs, or events.
- Do not copy or lightly rewrite source wording. Write a genuinely original synthesis.
- Do not publish sexually explicit or pornographic content, sexualized descriptions, or sexual-leak stories. If the story's central subject is sexual/explicit, return publish=false.
- Avoid graphic gore. If a story is sensitive but newsworthy, keep descriptions non-graphic.
- Distinguish confirmed facts from clearly labeled analysis. Prefer facts.
- Explain why the development matters.
- Only cite sources supplied below. Never invent a source or URL.

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

    for _, item in ranked[:24]:
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

        text = article.get('title', '') + ' ' + article.get('summary', '') + ' ' + re.sub('<[^>]+>', ' ', article.get('body_html', ''))
        srcs = article.get('sources', []) if isinstance(article.get('sources', []), list) else []
        supplied_urls = {s['url'] for s in sources}
        returned_urls = {s.get('url') for s in srcs if isinstance(s, dict)}
        domains = {urllib.parse.urlparse(u).netloc.lower().removeprefix('www.') for u in returned_urls if u}
        valid = article.get('publish') is True and article.get('confidence', 0) >= 85 and len(srcs) >= 2 and len(domains) >= 2 and returned_urls.issubset(supplied_urls) and not contains_blocked(text)

        if valid:
            print('PUBLISHED', publish(article))
            published_count += 1
            state['seen'].append(item['url'])
        else:
            held_count += 1
            reason = article.get('reason', 'quality gate failed')
            rejection_reasons.append(reason)
            print('HELD/REJECTED:', reason)

    save_state(state)
    update_index()
    report = {
        'started_utc': started.isoformat(),
        'finished_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
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

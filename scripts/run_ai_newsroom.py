import datetime as dt
import html
import json
import re
from pathlib import Path

import ai_newsroom

_original_sanitize = ai_newsroom.sanitize_body_html

# Add a wider Nigeria-first beat map without weakening the existing
# two-publisher corroboration gate. Google News RSS is used only for beats
# where a stable dedicated Nigerian RSS pair is not available; the feed still
# resolves to the original publisher URLs that the article cites.
EXPANDED_FEEDS = {
    'Nigeria - National & States': [
        'https://rss.punchng.com/v1/category/latest_news',
        'https://thereporter.com.ng/rss/latest-posts',
    ],
    'Nigeria - Law & Justice': [
        'https://news.google.com/rss/search?q=Nigeria+law+justice&hl=en-NG&gl=NG&ceid=NG:en',
        'https://thereporter.com.ng/rss/category/news',
    ],
    'Nigeria - Energy & Power': [
        'https://news.google.com/rss/search?q=Nigeria+energy+electricity+power&hl=en-NG&gl=NG&ceid=NG:en',
        'https://rss.punchng.com/v1/category/business',
    ],
    'Nigeria - Transport & Infrastructure': [
        'https://news.google.com/rss/search?q=Nigeria+transport+infrastructure+roads+rail&hl=en-NG&gl=NG&ceid=NG:en',
        'https://rss.punchng.com/v1/category/latest_news',
    ],
    'Nigeria - Environment & Climate': [
        'https://news.google.com/rss/search?q=Nigeria+environment+climate+flooding&hl=en-NG&gl=NG&ceid=NG:en',
        'https://thereporter.com.ng/rss/category/news',
    ],
    'Nigeria - Jobs & Labour': [
        'https://news.google.com/rss/search?q=Nigeria+jobs+labour+workers+employment&hl=en-NG&gl=NG&ceid=NG:en',
        'https://rss.punchng.com/v1/category/business',
    ],
    'Nigeria - Finance & Markets': [
        'https://thereporter.com.ng/rss/category/finance-101',
        'https://rss.punchng.com/v1/category/business',
    ],
    'Nigeria - Culture & Heritage': [
        'https://news.google.com/rss/search?q=Nigeria+culture+heritage+arts&hl=en-NG&gl=NG&ceid=NG:en',
        'https://thereporter.com.ng/rss/category/Entertainment-&-Lifestyle',
    ],
    'Nigeria - Tourism & Travel': [
        'https://news.google.com/rss/search?q=Nigeria+tourism+travel&hl=en-NG&gl=NG&ceid=NG:en',
        'https://thereporter.com.ng/rss/category/Entertainment-&-Lifestyle',
    ],
    'Nigeria - Religion & Interfaith': [
        'https://news.google.com/rss/search?q=Nigeria+religion+church+mosque+interfaith&hl=en-NG&gl=NG&ceid=NG:en',
        'https://christianitynigeria.com/feed/',
    ],
    'Nigeria - Youth & Society': [
        'https://news.google.com/rss/search?q=Nigeria+youth+society+community&hl=en-NG&gl=NG&ceid=NG:en',
        'https://thereporter.com.ng/rss/category/news',
    ],
    'Nigeria - Real Estate & Housing': [
        'https://news.google.com/rss/search?q=Nigeria+housing+real+estate+rent&hl=en-NG&gl=NG&ceid=NG:en',
        'https://rss.punchng.com/v1/category/business',
    ],
    'Nigeria - Food & Consumer': [
        'https://news.google.com/rss/search?q=Nigeria+food+prices+consumers+markets&hl=en-NG&gl=NG&ceid=NG:en',
        'https://rss.punchng.com/v1/category/business',
    ],
}

# Keep the original international/technology/sports/anime beats and add the
# expanded Nigeria beats alongside them.
ai_newsroom.FEEDS.update(EXPANDED_FEEDS)


def sanitize_with_fallback_link(body_html, allowed_urls):
    cleaned = _original_sanitize(body_html, allowed_urls)
    if ai_newsroom.extract_links(cleaned):
        return cleaned
    allowed = list(allowed_urls)
    if not allowed:
        return cleaned
    source_url = allowed[0]
    safe_url = html.escape(source_url, quote=True)
    return cleaned + ('<p>Read the original source report: '
                      f'<a href="{safe_url}" rel="nofollow noopener" target="_blank">source report</a>.</p>')


def normalize_publication_index():
    root = Path(__file__).resolve().parents[1]
    news = root / 'news'
    index = news / 'index.json'
    items = []
    for path in news.glob('*.html'):
        try:
            raw = path.read_text(encoding='utf-8')
            title = re.search(r'<h1>(.*?)</h1>', raw, re.S)
            summary = re.search(r'<p><strong>(.*?)</strong></p>', raw, re.S)
            meta = re.search(r'<p>([A-Za-z][A-Za-z &\-]+) · ', raw, re.S)
            category = html.unescape(re.sub(r'<[^>]+>', '', meta.group(1))).strip() if meta else 'News'
            category = category.replace('← C. O. Eric Newsroom', '').strip() or 'News'
            items.append({'file': path.name,
                          'title': html.unescape(re.sub(r'<[^>]+>', '', title.group(1))).strip() if title else path.stem,
                          'summary': html.unescape(re.sub(r'<[^>]+>', '', summary.group(1))).strip() if summary else '',
                          'category': category,
                          'date': dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime('%d %b %Y')})
        except Exception:
            continue
    items.sort(key=lambda x: x['file'], reverse=True)
    index.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def add_article_seo():
    root = Path(__file__).resolve().parents[1]
    news = root / 'news'
    for path in news.glob('*.html'):
        try:
            raw = path.read_text(encoding='utf-8')
            title_match = re.search(r'<title>(.*?)</title>', raw, re.S | re.I)
            title = title_match.group(1).strip() if title_match else 'C. O. Eric News'
            canonical = f'https://emeka45-github-io.pages.dev/news/{path.name}'
            seo = (f'<meta name="robots" content="index,follow">'
                   f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">'
                   f'<meta property="og:title" content="{html.escape(title, quote=True)}">')
            if '<link rel="canonical"' in raw:
                raw = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">', raw, count=1)
            else:
                raw = raw.replace('</title>', '</title>' + seo, 1)
            path.write_text(raw, encoding='utf-8')
        except Exception:
            continue


ai_newsroom.sanitize_body_html = sanitize_with_fallback_link

if __name__ == '__main__':
    ai_newsroom.main()
    normalize_publication_index()
    add_article_seo()

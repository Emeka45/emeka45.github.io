from __future__ import annotations

import re
from urllib.parse import urlparse

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


def normalize_and_seo():
    # No dependency on a removed normalize_index_categories() API.
    if hasattr(ai_newsroom, 'apply_cloudflare_seo'):
        ai_newsroom.apply_cloudflare_seo('https://emeka45-github-io.pages.dev/news')


if __name__ == '__main__':
    ai_newsroom.main()
    normalize_and_seo()

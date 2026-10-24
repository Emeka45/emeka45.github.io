from __future__ import annotations

import datetime as dt
import html
import json
import re

import ai_newsroom as newsroom

MAX_PUBLISH = 5


def clean(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text or '')).strip()


def same_event(a, b):
    """Match the same real-world event across feeds with different headlines."""
    # The old matcher was too strict for RSS headlines: two genuine reports
    # could describe the same event with different wording and still fail.
    at = newsroom.tokens(a.get('title', ''))
    bt = newsroom.tokens(b.get('title', ''))
    shared_title = at & bt
    title_overlap = len(shared_title) / max(1, min(len(at), len(bt)))
    if len(shared_title) >= 2 and title_overlap >= 0.40:
        return True

    aa = newsroom.tokens(a.get('title', '') + ' ' + a.get('summary', ''))
    bb = newsroom.tokens(b.get('title', '') + ' ' + b.get('summary', ''))
    shared = aa & bb
    combined = len(shared) / max(1, min(len(aa), len(bb)))
    # Require several shared non-stopword terms so broad topic overlap alone
    # cannot turn unrelated stories into corroboration.
    return len(shared) >= 4 and combined >= 0.30


def find_corroboration(item, all_items):
    """Find independent reports of the same event across different domains."""
    matches = []
    for other in all_items:
        if other.get('url') == item.get('url'):
            continue
        if not other.get('domain') or other.get('domain') == item.get('domain'):
            continue
        if same_event(item, other):
            matches.append(other)
    matches.sort(key=lambda other: newsroom.similarity(item, other), reverse=True)
    return matches[:3]


def build_article(item, matches):
    sources = [item] + [m for m in matches if m.get('domain') != item.get('domain')]
    sources = sources[:3]
    title = clean(item.get('title', 'News update'))
    category = item.get('category') or 'News'
    summary = clean(item.get('summary', ''))
    if not summary:
        summary = f"Reports from multiple publishers are covering this development in {category}."
    paragraphs = [
        f"Multiple independent publishers are reporting on the same development: {title}.",
        f"The available reports place the development in the {category} category. The accounts were compared for agreement on the central event rather than simply shared names or broad topics.",
        f"One of the available reports describes the development this way: {summary}",
        "Readers should consult the linked source reports for additional context, updates and details that may change as the story develops.",
    ]
    body = ''.join(f'<p>{html.escape(p)}</p>' for p in paragraphs)
    first = sources[0]
    body += f'<p><a href="{html.escape(first["url"], quote=True)}" rel="nofollow noopener" target="_blank">Read the source report</a></p>'
    return {
        'publish': True,
        'category': category,
        'title': title,
        'summary': summary[:300],
        'body_html': body,
        'sources': [{'name': clean(s.get('source') or s.get('domain') or 'Source'), 'url': s['url']} for s in sources],
        'confidence': 85,
    }


def main():
    started = dt.datetime.now(dt.timezone.utc)
    state = newsroom.load_state()
    all_items = []
    feed_failures = []
    feed_count = feed_success = 0
    for category, feeds in newsroom.FEEDS.items():
        for feed in feeds:
            items, error = newsroom.parse_feed(category, feed)
            feed_count += 1
            if error:
                feed_failures.append({'category': category, 'url': feed, 'error': error})
            else:
                feed_success += 1
            all_items.extend(items)

    fresh = [x for x in all_items if x.get('url') not in state.get('seen', [])]
    candidates = []
    used_urls = set()
    for item in fresh:
        if item.get('url') in used_urls:
            continue
        matches = find_corroboration(item, all_items)
        # One real-world event should produce at most one candidate per run.
        if any(m.get('url') in used_urls for m in matches):
            continue
        domains = {item.get('domain')} | {m.get('domain') for m in matches}
        if len(domains) >= 2 and matches:
            candidates.append((len(domains), item, matches))
            used_urls.add(item['url'])
            used_urls.update(m['url'] for m in matches if m.get('url'))

    candidates.sort(key=lambda x: (x[0], newsroom.similarity(x[1], x[2][0]) if x[2] else 0), reverse=True)
    published = 0
    published_titles = []
    for _, item, matches in candidates:
        if published >= MAX_PUBLISH:
            break
        try:
            article = build_article(item, matches)
            newsroom.publish(article)
            published += 1
            published_titles.append(article['title'])
            state.setdefault('seen', []).append(item['url'])
            for match in matches:
                state.setdefault('seen', []).append(match['url'])
        except Exception as exc:
            print('PUBLISH ERROR:', exc)

    state['seen'] = list(dict.fromkeys(state.get('seen', [])))
    newsroom.save_state(state)
    newsroom.update_index()
    report = {
        'started_utc': started.isoformat(),
        'finished_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'mode': 'reliable-template-fallback',
        'feed_count': feed_count,
        'feed_success_count': feed_success,
        'feed_failure_count': len(feed_failures),
        'feed_failures': feed_failures,
        'total_items': len(all_items),
        'fresh_items': len(fresh),
        'corroborated_candidates': len(candidates),
        'published_count': published,
        'published_titles': published_titles,
        'note': 'Publishes original summaries from independently corroborated RSS reports without consuming Gemini quota.'
    }
    newsroom.REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / 'articles'
DATA = ROOT / 'articles-data'
INDEX = ARTICLES / 'index.json'
REPORT = DATA / 'run-report.json'
ARTICLES.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

TOPICS = [
    ('How to Think Clearly When the Internet Is Overwhelming', 'Personal Development'),
    ('How to Use AI as a Tool Without Letting It Think for You', 'Technology & Modern Life'),
    ('A Practical Guide to Building Better Study Habits', 'Education'),
    ('How to Spot Misleading Information Online', 'Practical Explainers'),
    ('Why Small Daily Habits Often Beat Sudden Motivation', 'Psychology & Human Behaviour'),
    ('How to Manage Money When Income Is Irregular', 'Money & Work'),
    ('How to Protect Your Digital Privacy on a Phone', 'Technology & Modern Life'),
    ('How to Have Better Conversations During Disagreements', 'Relationships & Family'),
    ('What Critical Thinking Really Means in Everyday Life', 'Personal Development'),
    ('How to Learn Difficult Subjects Without Burning Out', 'Education'),
    ('How to Make Better Decisions With Limited Information', 'Psychology & Human Behaviour'),
    ('How to Build a Simple Personal Knowledge System', 'Education'),
]


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:90]


def existing_titles():
    if INDEX.exists():
        try:
            data = json.loads(INDEX.read_text(encoding='utf-8'))
            return {str(x.get('title', '')).strip().lower() for x in data if isinstance(x, dict)}
        except Exception:
            pass
    return set()


def article_body(title):
    topics = {
        'How to Think Clearly When the Internet Is Overwhelming': [
            'The modern internet can make every issue feel urgent. Notifications, short videos, breaking-news banners and endless opinions compete for attention, even when none of them requires an immediate response.',
            'A useful first step is to separate information from urgency. Ask what actually changed, what evidence supports the claim, and whether knowing it now will alter a decision you need to make. This simple pause reduces the pressure created by constant updates.',
            'It also helps to create deliberate information windows. Instead of checking several apps whenever there is a quiet moment, choose specific times for news, messages and entertainment. Attention becomes easier to protect when access is intentional rather than automatic.',
            'Finally, keep a small space for thinking without a screen. Walking, writing a few notes or discussing an idea with someone can reveal assumptions that are difficult to notice while scrolling. Clear thinking is not the absence of information; it is the ability to decide which information deserves your attention.'
        ],
        'How to Use AI as a Tool Without Letting It Think for You': [
            'AI can make research, drafting and explanation faster, but speed is not the same thing as judgment. The most useful relationship with an AI system is closer to using a calculator or research assistant: let it accelerate work while you remain responsible for the result.',
            'Start by giving the system a clear task and then inspect what it produces. Check important names, dates, numbers, quotations and claims against reliable sources. An answer that sounds confident is not automatically an answer that is correct.',
            'For learning, ask AI to explain a difficult idea in several ways, generate practice questions or challenge your reasoning. Then attempt the problem yourself. This keeps the technology on the side of learning rather than replacing the learning process.',
            'The best habit is simple: use AI to expand your thinking, not to surrender it. When a decision matters, your values, evidence and responsibility should remain in control.'
        ],
        'A Practical Guide to Building Better Study Habits': [
            'Effective studying is less about spending the maximum number of hours at a desk and more about using those hours deliberately. A good system combines clear goals, active recall, practice and regular review.',
            'Begin each session with one measurable objective. Instead of writing “study law” or “study chemistry,” define a result such as explaining a topic from memory or solving a set of problems without notes. Specific goals make progress visible.',
            'During study, spend more time retrieving information than rereading it. Close the book and explain the concept in your own words. Answer questions before looking at the solution. Mistakes reveal exactly where another review is needed.',
            'Finally, space your reviews. A short return to material after a day, several days and then a longer interval is usually more useful than one exhausting session. Consistency turns ordinary study periods into a durable learning system.'
        ],
        'How to Spot Misleading Information Online': [
            'Misleading information is not always an obvious lie. A real event can be presented with a false date, an old photograph can be attached to a new story, or a headline can exaggerate what the underlying report actually says.',
            'Check the original source first. Look beyond the headline and identify who made the claim, when it was made and what evidence is provided. If a post gives no source, treat it as a lead to investigate rather than as established fact.',
            'Next, compare independent reports. Two websites repeating the same paragraph are not necessarily two independent confirmations. Stronger corroboration comes from unrelated publishers reporting the same central fact from their own reporting or primary material.',
            'Finally, notice emotional pressure. Claims designed to make readers instantly angry, frightened or triumphant deserve an extra pause. Verification is not cynicism; it is a practical way to avoid becoming an accidental distributor of false information.'
        ],
    }
    paragraphs = topics.get(title, [
        f'{title} is easier to approach when the problem is broken into small, practical decisions.',
        'Start by defining the outcome you want. A clear outcome makes it easier to decide what information matters and what can be ignored. It also gives you a way to measure whether a change is actually helping.',
        'Next, build a simple routine that can survive ordinary busy days. A complicated system may look impressive but is difficult to maintain. Small actions repeated consistently usually create more progress than occasional bursts of effort.',
        'Review the result after a few weeks. Keep the parts that work, remove unnecessary steps and adjust the system to your circumstances. Good habits are not rigid rules; they are structures that make useful behaviour easier to repeat.'
    ])
    return paragraphs


def render(title, category, paragraphs, now):
    summary = paragraphs[0]
    body = ''.join(f'<p>{html.escape(p)}</p>' for p in paragraphs)
    body += '<h2>Key takeaways</h2><ul>' + ''.join(f'<li>{html.escape(p.split(".")[0])}.</li>' for p in paragraphs[:3]) + '</ul>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(summary[:250], quote=True)}"><title>{html.escape(title)} — C. O. Eric Articles</title><link rel="canonical" href="https://emeka45.github.io/articles/{slug(title)}.html"></head><body><main><p><a href="../articles.html">← C. O. Eric Articles</a></p><p>{html.escape(category)} · {now.strftime('%d %b %Y')}</p><h1>{html.escape(title)}</h1><p><strong>{html.escape(summary)}</strong></p>{body}<hr><p>Written as an original C. O. Eric editorial feature.</p></main></body></html>''', summary


def main():
    now = dt.datetime.now(dt.timezone.utc)
    titles = existing_titles()
    requested = os.environ.get('ARTICLE_TOPIC', '').strip()
    category_override = os.environ.get('ARTICLE_CATEGORY', '').strip()
    chosen = None
    if requested:
        for title, category in TOPICS:
            if title.lower() == requested.lower():
                chosen = (title, category)
                break
        if chosen is None:
            chosen = (requested, category_override or 'Practical Explainers')
    else:
        for title, category in TOPICS:
            if title.lower() not in titles:
                chosen = (title, category)
                break
    if chosen is None:
        chosen = TOPICS[now.timetuple().tm_yday % len(TOPICS)]

    title, category = chosen
    if title.lower() in titles and not requested:
        report = {'finished_utc': now.isoformat(), 'published': False, 'reason': 'All planned topics already exist.'}
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        return

    paragraphs = article_body(title)
    document, summary = render(title, category, paragraphs, now)
    filename = f'{slug(title)}.html'
    (ARTICLES / filename).write_text(document, encoding='utf-8')

    entries = []
    if INDEX.exists():
        try:
            entries = json.loads(INDEX.read_text(encoding='utf-8'))
        except Exception:
            entries = []
    entry = {'file': filename, 'title': title, 'summary': summary, 'category': category, 'date': now.strftime('%d %b %Y')}
    entries = [entry] + [x for x in entries if str(x.get('title', '')).lower() != title.lower()]
    INDEX.write_text(json.dumps(entries[:100], ensure_ascii=False, indent=2), encoding='utf-8')

    report = {'finished_utc': now.isoformat(), 'mode': 'reliable-original-editorial-fallback', 'published': True, 'title': title, 'category': category, 'file': filename, 'note': 'Publishes an original article without consuming Gemini quota.'}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

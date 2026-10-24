from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
DATA = ROOT / "articles-data"
INDEX = ARTICLES / "index.json"
REPORT = DATA / "run-report.json"
ARTICLES.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

TOPICS = [
    ("How to Think Clearly When the Internet Is Overwhelming", "Personal Development"),
    ("How to Use AI as a Tool Without Letting It Think for You", "Technology & Modern Life"),
    ("A Practical Guide to Building Better Study Habits", "Education"),
    ("How to Spot Misleading Information Online", "Practical Explainers"),
    ("Why Small Daily Habits Often Beat Sudden Motivation", "Psychology & Human Behaviour"),
    ("How to Manage Money When Income Is Irregular", "Money & Work"),
    ("How to Protect Your Digital Privacy on a Phone", "Technology & Modern Life"),
    ("How to Have Better Conversations During Disagreements", "Relationships & Family"),
    ("What Critical Thinking Really Means in Everyday Life", "Personal Development"),
    ("How to Learn Difficult Subjects Without Burning Out", "Education"),
    ("How to Make Better Decisions With Limited Information", "Psychology & Human Behaviour"),
    ("How to Build a Simple Personal Knowledge System", "Education"),
]

CONTENT = {
"How to Think Clearly When the Internet Is Overwhelming": [
"The modern internet puts breaking news, personal opinions, advertising and entertainment in one continuous stream. Because every item competes for attention, it can become difficult to tell an important development from something designed merely to keep people scrolling.",
"Start by asking three questions when a claim catches your attention: What exactly is being claimed? What evidence is offered? Who is in a position to know? These questions turn a quick emotional reaction into a small investigation. For news, look for the original statement, report or document rather than relying only on a screenshot or a dramatic headline.",
"Separate urgency from importance. A message marked urgent may not require action, while a quiet notice about a deadline may matter a great deal. Decide whether the information changes a decision you must make today. If it does not, save it for a planned reading period instead of interrupting your work.",
"Create boundaries that fit your real routine. Turn off non-essential notifications, choose a few reliable sources, and check them at set times. When a topic is complicated, read beyond the headline and compare independent reporting. Repeated copies of one claim do not count as independent confirmation.",
"Finally, leave room for thought away from the feed. Write down what you know, what remains uncertain and what evidence would change your mind. Clear thinking is not knowing everything; it is being able to weigh information, acknowledge uncertainty and choose what deserves your attention."
],
"How to Use AI as a Tool Without Letting It Think for You": [
"AI tools can explain unfamiliar subjects, organise notes, suggest drafts and help generate practice questions. Their speed is useful, but a fluent answer is not proof that its facts or reasoning are correct. The user still needs to decide what to trust and how to use the result.",
"Give the system a specific task and enough context. Instead of asking it to do an entire project vaguely, explain the goal, audience, constraints and preferred format. For complex work, break the task into stages and review each result before moving forward.",
"Check high-impact claims independently. Verify dates, legal rules, medical guidance, quotations, calculations and named sources against reliable primary material or qualified professionals. Ask the AI to identify uncertainty and provide sources, but do not assume that a citation is genuine until you open it.",
"For learning, use AI as a tutor rather than a substitute. Ask for an explanation, attempt the problem yourself, and then request feedback on your reasoning. Practice questions and alternative explanations can expose gaps in understanding better than simply copying a finished answer.",
"Protect private information and follow the rules of your school, workplace or publisher. Avoid submitting passwords, financial details or confidential records to services unless you understand their data practices. The best use of AI is to improve your own judgement and output while keeping responsibility with you."
],
"A Practical Guide to Building Better Study Habits": [
"Effective studying depends less on the number of hours spent with a book open than on what the learner can recall and apply afterwards. A manageable system combines clear objectives, active recall, practice and spaced review.",
"Begin every session with a measurable target. Instead of writing 'study chemistry', decide to explain a reaction from memory, solve ten problems or outline a legal principle with its elements. A concrete target makes it easier to begin and gives the session a clear finish line.",
"Use active recall. Read a short section, close the material and explain the main ideas in your own words. Then answer questions or solve problems without looking at the answer first. Checking afterwards helps reveal the exact point that needs another review.",
"Spread practice across several days rather than relying only on one long session before an examination. Review difficult material after a day, revisit it a few days later, and test it again after a longer interval. Mix related problem types once the basics are understood so you learn to choose the right method.",
"Plan around real constraints. Short focused sessions are more sustainable than a timetable that leaves no room for work, travel or rest. Put the phone away when it is not needed, sleep adequately and keep a brief record of topics that still cause difficulty. Consistency and feedback make the system stronger over time."
],
"How to Spot Misleading Information Online": [
"Misleading online content is not always entirely fabricated. It may use an old photograph for a new event, remove a quotation from its context, present an allegation as a proven fact or use a headline that goes beyond what the report actually establishes.",
"Find the original source. Open the article rather than judging from a screenshot, identify the author or organisation, and check the publication date. For a public announcement, look for the original statement, official document, data release or full recording where possible.",
"Compare independent reporting. Several websites repeating the same wire report or social-media post may all depend on one source. Stronger confirmation comes from genuinely separate reporting, primary documents or direct evidence. If credible sources disagree, describe the disagreement instead of pretending it has been settled.",
"Check images and videos in context. Search for earlier appearances of the image, look for landmarks and signs, and compare the claimed date and location with the original upload. Cropped clips can omit important context, so seek the full recording before drawing a conclusion.",
"Be especially careful when a post pressures you to share immediately, promises secret knowledge or tries to trigger intense anger or fear. If you cannot verify a claim, do not forward it as fact. Waiting, checking and correcting a mistake are signs of responsible participation, not weakness."
],
"Why Small Daily Habits Often Beat Sudden Motivation": [
"Motivation can help someone begin a task, but it changes with mood, sleep, stress and circumstances. A habit reduces the number of decisions required by linking an action to a regular cue, making progress less dependent on feeling inspired.",
"Choose a behaviour small enough to repeat on an ordinary difficult day. Reading two pages, reviewing five flashcards or taking a short walk can be a useful starting point. The aim at first is to establish a reliable pattern, not to achieve the maximum possible result in one burst.",
"Attach the action to something that already happens. For example, review tomorrow's priorities after dinner or revise vocabulary after brushing your teeth. Make the environment supportive: place the book where you will see it, prepare materials in advance and reduce the steps between you and the action.",
"Track consistency without turning a missed day into a reason to quit. A simple calendar mark can show whether the routine is becoming regular. If you repeatedly miss the same cue, investigate the obstacle and redesign the plan rather than blaming yourself.",
"Increase the difficulty only after the starting version feels manageable. Habits do not replace ambition; they give ambition a practical structure. Small repeated actions accumulate, while occasional extreme efforts are hard to sustain. Review the routine periodically and keep what genuinely helps."
],
"How to Manage Money When Income Is Irregular": [
"When income changes from week to week, a budget based on one optimistic month can quickly become unreliable. A safer approach begins with the money that is actually available and gives priority to essential costs before optional spending.",
"List necessary expenses such as food, housing, transport, utilities, medication and work-related costs. Record their due dates and minimum amounts. Separate these essentials from flexible spending so that a lower-income period does not catch you unaware of a bill that cannot easily be postponed.",
"Build the plan around a conservative income estimate rather than your best month. When money arrives, allocate it to upcoming essentials first. If possible, set aside a small amount for irregular expenses and emergencies; even a modest reserve can reduce the need to borrow when a phone breaks or transport costs rise.",
"Track spending in a notebook or a simple phone spreadsheet. Review the records weekly and look for recurring costs that can be reduced without harming health, safety or your ability to earn. Avoid high-interest borrowing for routine expenses when a safer alternative or payment arrangement is available.",
"Make the budget adjustable. If income falls short, contact providers early, prioritise urgent needs and seek trustworthy local advice rather than paying an upfront fee to a supposed grant or investment scheme. The goal is not a perfect spreadsheet; it is a clear picture of obligations, choices and the next practical step."
],
"How to Protect Your Digital Privacy on a Phone": [
"A phone can hold messages, photos, location history, financial apps and access to other accounts. Protecting it is not one setting but a set of practical layers: secure the device, limit app access, protect accounts and think carefully before sharing information.",
"Start with the screen lock. Use a strong PIN or password that someone cannot easily guess, enable automatic locking and keep the operating system and apps updated. Turn on the phone's built-in lost-device feature and learn how to lock or erase it remotely if it disappears. Do not share your unlock code casually.",
"Review permissions for location, microphone, camera, contacts, SMS and files. An app should have access only when its features genuinely need it. Where available, choose 'only while using' or one-time access for location, and remove permissions from apps you no longer use. Uninstall apps from sources you do not trust.",
"Secure important accounts with unique passwords and two-step verification where available. A reputable password manager can help you avoid reusing passwords. Be suspicious of messages asking you to sign in through unexpected links; open the official app or type the known address yourself. Never send a verification code to a stranger.",
"Use public Wi-Fi carefully, avoid installing unknown APK files and check what information a photo or post reveals before publishing it. Back up important files to a place you control. No single setting guarantees privacy, but these layers make it harder for a lost phone, a deceptive message or an overly curious app to expose your information."
],
"How to Have Better Conversations During Disagreements": [
"Disagreement becomes difficult when people feel they must defend their identity instead of examining the issue. A productive conversation does not require identical opinions; it requires enough respect and clarity for each person to understand what is actually being disputed.",
"Begin by identifying the specific issue. Replace broad statements such as 'you never listen' with an observable example and its effect. Describe your own concern without assuming you know the other person's intention. This makes it easier to discuss behaviour rather than attack character.",
"Listen for the strongest version of the other person's point. Summarise what you heard and ask whether you understood correctly before responding. Clarifying questions can reveal whether the disagreement is about facts, priorities, definitions or different experiences.",
"Slow the conversation when emotions rise. A short pause is more useful than insults, threats or a rapid series of old complaints. If either person needs a break, agree on when to return to the topic. A pause should create room to think, not become a way to avoid every difficult discussion.",
"End with a practical next step where possible. You might agree to check a fact, change one behaviour, set a boundary or accept that the issue remains unresolved. In situations involving intimidation or abuse, personal safety matters more than preserving a conversation; seek support from someone trustworthy."
],
"What Critical Thinking Really Means in Everyday Life": [
"Critical thinking is the habit of evaluating a claim before accepting it. It does not mean rejecting everything or trying to win every argument. It means asking what the evidence supports, which assumptions are being made and whether another explanation fits the facts.",
"Separate observations from interpretations. 'The payment arrived two days late' is an observation; 'the person intended to cheat me' is an interpretation that needs more evidence. Keeping the two apart helps people respond to what is known without ignoring reasonable concerns.",
"Look for evidence that could prove your first impression wrong. People naturally notice information that supports what they already believe. Deliberately asking 'what would change my mind?' can expose missing facts and prevent confidence from growing faster than the evidence.",
"Consider the source and the method. A personal story can be sincere but may not represent everyone; a statistic may be accurate but misleading without its date, sample or comparison. For important decisions, prefer original records and multiple independent sources over a confident social-media post.",
"Use the conclusion that the evidence justifies, not the strongest conclusion imaginable. Sometimes the correct answer is 'not enough information yet'. Critical thinking improves decisions because it makes uncertainty visible and leaves room to update a view when better evidence arrives."
],
"How to Learn Difficult Subjects Without Burning Out": [
"A difficult subject can feel impossible when every unfamiliar term appears to depend on another unfamiliar idea. The solution is to identify the foundations, break the material into manageable pieces and test understanding regularly instead of repeatedly reading a large chapter from beginning to end.",
"Start with a map of the topic. List the main concepts, definitions and skills, then identify which ones are prerequisites for the rest. If one foundation is weak, repair it before moving on. A short explanation or worked example can make later material much easier to understand.",
"Study actively in short blocks. After reading a section, close the book and explain it aloud, draw a diagram or solve a question. Compare your attempt with the material and note the exact point where your reasoning failed. That is a more useful guide for the next session than simply highlighting more text.",
"Use examples and gradually increase difficulty. Work through a model answer, attempt a similar problem with notes, and then try one independently. Mix in older questions so you practise recognising which method applies. Ask a teacher, classmate or trusted learning resource about a specific point when you are stuck.",
"Protect recovery as part of the plan. Sleep, breaks, movement and realistic goals help attention last. If you fall behind, choose the highest-priority concepts rather than trying to make up every missed hour in one night. Sustainable progress is more valuable than a cycle of exhaustion and avoidance."
],
"How to Make Better Decisions With Limited Information": [
"Many real decisions must be made before every fact is available. Waiting for perfect certainty can itself have a cost, but acting on a guess can create avoidable harm. A useful process distinguishes what is known, what is uncertain and what can still be checked in time.",
"Define the decision and the deadline. Write down the outcome you want and the constraints you cannot ignore, such as cost, safety, time or obligations to other people. This prevents a decision from drifting into an endless search for information that will not change the result.",
"Compare a small number of realistic options, including doing nothing for now. For each option, consider likely benefits, costs, worst plausible outcome and how reversible the choice is. A reversible low-cost decision can often be tested quickly; a decision with lasting consequences deserves more verification.",
"Seek information that could change the choice rather than collecting facts indiscriminately. Ask a knowledgeable person, inspect primary evidence and check assumptions that carry the most risk. Be alert to wishful thinking and to pressure from anyone who benefits from your decision.",
"Set a review point. If new evidence appears, update the plan rather than defending the first choice simply because you made it. Good decisions are not guaranteed to produce perfect outcomes; they use the available evidence carefully, limit avoidable risks and remain open to correction."
],
"How to Build a Simple Personal Knowledge System": [
"Useful information is easy to lose when it is scattered across screenshots, browser tabs, notebooks and chat messages. A personal knowledge system gives important notes a reliable home and makes it possible to find them when a task or question returns.",
"Choose one main capture location that works on your devices. It might be a notes app, a folder of text documents or a paper notebook. The best tool is one you can use consistently, including when internet access is limited. Avoid building a complicated system before you know what you need to store.",
"Capture enough context to make a note understandable later. Record the main idea, why it matters, the source and the date when freshness matters. Save a link to the original material rather than copying an entire copyrighted article. Mark uncertain ideas as questions instead of treating them as established facts.",
"Organise for retrieval, not perfection. A few broad categories and descriptive titles are often enough. Use search, tags or a short index for projects that recur. When collecting material for a report or examination, separate source notes from your own conclusions so you can trace where a claim came from.",
"Review the system briefly each week. Turn useful notes into an action, a summary, a study question or a draft; delete duplicates and archive finished projects. A knowledge system earns its place by helping you think and act, not by accumulating the largest possible pile of saved information."
]
}

def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:90] or "article"


def load_index():
    if not INDEX.exists():
        return []
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def article_body(title: str) -> list[str]:
    return CONTENT.get(title, [])


def validate_article(title: str, paragraphs: list[str]) -> list[str]:
    errors = []
    if len(paragraphs) < 5:
        errors.append("At least five topic-specific paragraphs are required.")
    if any(len(p.split()) < 25 for p in paragraphs):
        errors.append("Every paragraph must contain at least 25 words.")
    if not paragraphs or title.lower() in paragraphs[0].lower():
        errors.append("The opening must be a real summary, not a repeated title.")
    if len(" ".join(paragraphs).split()) < 250:
        errors.append("Article body must contain at least 250 words.")
    if len(set(paragraphs)) != len(paragraphs):
        errors.append("Repeated paragraphs detected.")
    return errors


def render(title: str, category: str, paragraphs: list[str], now: dt.datetime):
    summary = paragraphs[0]
    body = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    takeaways = paragraphs[1:4]
    body += "<h2>Key takeaways</h2><ul>" + "".join(
        f"<li>{html.escape(p.split('. ', 1)[0] + '.')}</li>" for p in takeaways
    ) + "</ul>"
    canonical = f"https://emeka45.github.io/articles/{slug(title)}.html"
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{html.escape(summary[:250], quote=True)}">
<title>{html.escape(title)} — C. O. Eric Articles</title><link rel="canonical" href="{canonical}">
<style>body{{margin:0;color:#202638;background:#f7f8fc;font:18px/1.8 system-ui,sans-serif}}main{{max-width:780px;margin:36px auto;padding:0 20px}}a{{color:#6041bd}}h1{{font-size:clamp(2.2rem,7vw,3.6rem);line-height:1.12;letter-spacing:-.04em}}h2{{margin-top:2em}}.meta{{color:#667085;font-size:.9rem}}.lead{{font-size:1.12rem;color:#40495b}}li{{margin:.5em 0}}footer{{margin-top:3em;border-top:1px solid #ddd;padding-top:1em;color:#667085;font-size:.9rem}}</style>
</head><body><main><p><a href="../articles.html">← C. O. Eric Articles</a></p>
<p class="meta">{html.escape(category)} · {now.strftime('%d %b %Y')}</p><h1>{html.escape(title)}</h1>
<p class="lead"><strong>{html.escape(summary)}</strong></p>{body}
<footer>Written as an original C. O. Eric editorial feature. Review important decisions against trusted, up-to-date sources.</footer>
</main></body></html>"""
    return document, summary


def main():
    now = dt.datetime.now(dt.timezone.utc)
    entries = load_index()
    titles = {str(x.get("title", "")).strip().lower() for x in entries if isinstance(x, dict)}
    requested = os.environ.get("ARTICLE_TOPIC", "").strip()
    category_override = os.environ.get("ARTICLE_CATEGORY", "").strip()
    if requested:
        chosen = next(((t, c) for t, c in TOPICS if t.lower() == requested.lower()), None)
        if chosen is None:
            report = {"finished_utc": now.isoformat(), "published": False, "reason": "Requested topic is not in the reviewed topic catalogue; refusing to publish generic filler.", "requested_topic": requested}
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit(2)
    else:
        # Repair previously published filler/short articles before creating a new topic.
        chosen = None
        for candidate_title, candidate_category in TOPICS:
            old_entry = next((x for x in entries if str(x.get("title", "")).strip().lower() == candidate_title.lower()), None)
            if old_entry:
                old_path = ARTICLES / str(old_entry.get("file", ""))
                old_text = ""
                if old_path.is_file():
                    old_text = re.sub(r"<[^>]+>", " ", old_path.read_text(encoding="utf-8", errors="replace"))
                    old_text = html.unescape(re.sub(r"\\s+", " ", old_text)).strip()
                # Existing generic filler is replaced by the reviewed topic-specific article.
                if len(old_text.split()) < 430:
                    chosen = (candidate_title, candidate_category)
                    break
            else:
                chosen = (candidate_title, candidate_category)
                break
    if chosen is None:
        report = {"finished_utc": now.isoformat(), "published": False, "reason": "All reviewed topics already exist and pass the repair check; no duplicate article was created."}
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    title, category = chosen
    if category_override and requested:
        category = category_override
    paragraphs = article_body(title)
    errors = validate_article(title, paragraphs)
    if errors:
        report = {"finished_utc": now.isoformat(), "published": False, "title": title, "quality_errors": errors}
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    document, summary = render(title, category, paragraphs, now)
    filename = f"{slug(title)}.html"
    (ARTICLES / filename).write_text(document, encoding="utf-8")
    entry = {"file": filename, "title": title, "summary": summary, "category": category, "date": now.strftime("%d %b %Y")}
    entries = [entry] + [x for x in entries if str(x.get("title", "")).strip().lower() != title.lower()]
    INDEX.write_text(json.dumps(entries[:100], ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"finished_utc": now.isoformat(), "mode": "topic-specific-editorial-library", "published": True, "title": title, "category": category, "file": filename, "word_count": len(" ".join(paragraphs).split()), "quality_checks": "passed", "note": "Only reviewed topic-specific content is published; generic fallback content is disabled."}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

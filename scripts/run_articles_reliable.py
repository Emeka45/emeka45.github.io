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
    ("How to Evaluate an Online Course Before Paying", "Education"),
    ("How to Prepare for a Job Interview With Confidence", "Money & Work"),
    ("Understanding Your Digital Footprint and Online Reputation", "Technology & Modern Life"),
    ("How to Recognise Common Online Job Scams", "Practical Explainers"),
    ("A Practical Guide to Setting Healthy Boundaries", "Relationships & Family"),
    ("How to Make Better Use of Your Community Library", "Education"),
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
],
"How to Evaluate an Online Course Before Paying": [
"Online courses can make useful skills easier to access, but attractive adverts do not guarantee that a course is current, well taught or worth its price. Before paying, identify the exact skill you want to learn and the level of competence you expect to reach.",
"Read the syllabus carefully and check whether it explains the topics, practical exercises and expected workload. A course that promises mastery in a few hours may be overselling its results. Look for sample lessons so you can judge the teaching style and whether explanations are understandable.",
"Check who created the course and what relevant experience they can demonstrate. Independent reviews can help, but look for detailed feedback about assignments, support and outcomes rather than relying only on star ratings or testimonials displayed by the seller.",
"Find out what the price includes. Confirm whether access is permanent or time-limited, whether certificates cost extra, how refunds work and whether you need additional software or subscriptions. Read the payment and cancellation terms before entering card or account details.",
"Compare the course with free or lower-cost alternatives, including libraries, public learning platforms and reputable tutorials. Choose based on clear learning outcomes, credible instruction and practical value, not countdown timers or pressure to buy immediately."
],
"How to Prepare for a Job Interview With Confidence": [
"An interview is a structured conversation about the work an employer needs done and the evidence that you can do it. Preparation helps you explain your experience clearly, ask useful questions and decide whether the role is suitable for you.",
"Study the job description and identify the main responsibilities and required skills. For each important requirement, prepare a brief example from employment, school, volunteering or personal projects. Explain the situation, the action you took and the result without exaggerating your contribution.",
"Research the organisation using reliable public information. Understand its services, customers and recent priorities, then prepare a few thoughtful questions about the role, training, expectations and how performance is assessed. Avoid pretending to know facts you have not verified.",
"Plan the practical details early. Confirm the interview time, location or meeting link, test your phone or computer if it is online, and choose neat clothing appropriate to the setting. Allow time for transport and keep copies of relevant documents ready.",
"During the interview, listen to each question and take a moment to organise your answer. If you do not understand something, ask for clarification. Be honest about gaps in your experience and explain how you would learn. Afterward, review what went well and what you can improve."
],
"Understanding Your Digital Footprint and Online Reputation": [
"Every public post, comment, photograph and profile can contribute to the impression someone forms about a person or organisation online. A digital footprint is not always harmful, but it can reveal more than intended and may remain accessible after the original post is deleted.",
"Start by searching your name and common usernames in a private browser window. Review the public information that appears, including old profiles, tagged photographs and comments. Check privacy settings on accounts you still use and remove material you no longer want to share where possible.",
"Think about the audience before posting. A joke understood by close friends may be confusing outside that group, while a photograph can reveal a location, school, workplace or routine. Avoid publishing other people's personal information or images without permission.",
"Remember that privacy settings reduce visibility but do not guarantee secrecy. Someone may save, forward or screenshot material before it is removed. Treat direct messages and private groups with care, especially when they contain sensitive details or documents.",
"Build a positive footprint as well as reducing unwanted exposure. Keep professional profiles accurate, share work you are comfortable standing behind and correct misleading information when you can. A thoughtful online presence is built through consistent choices, not through trying to appear perfect."
],
"How to Recognise Common Online Job Scams": [
"Fake job offers often target people who need work urgently. They may promise unusually high pay for simple tasks, claim that no experience is needed, or pressure applicants to pay before they can begin. A professional-looking advert does not prove that the employer is genuine.",
"Be cautious when a recruiter asks for registration, training, equipment or activation fees before providing a verifiable job. Legitimate hiring processes vary, but demands for urgent transfers to personal accounts or cryptocurrency wallets are serious warning signs.",
"Check the employer independently. Find its official website and contact details rather than relying only on links supplied in a message. Search for the job title and company name alongside terms such as complaint or scam, and contact the organisation through a channel you located yourself.",
"Protect identity and financial information during recruitment. Do not send passwords, one-time verification codes or full banking credentials. Share identity documents only when you have verified who is requesting them and understand why they are needed.",
"If you suspect a scam, stop communicating, preserve messages and payment records, and contact your bank or payment provider promptly if money was sent. Report the account or advert through the relevant platform and warn others without reposting unverified personal accusations."
],
"A Practical Guide to Setting Healthy Boundaries": [
"Boundaries describe what a person can accept, what they are responsible for and how they will respond when a limit is crossed. They are not a way to control another person's choices; they help make expectations and responsibilities clearer.",
"Begin by noticing situations that repeatedly leave you overwhelmed, resentful or uncomfortable. Identify the specific behaviour and the limit you need. A useful boundary is concrete, realistic and connected to something you can control, such as your time, privacy or availability.",
"Communicate the limit calmly and directly. For example, explain when you are available to help, what information you prefer to keep private or which conversations you will pause if insults begin. Clear language is usually more effective than hints or threats.",
"Consistency matters more than lengthy explanations. If you say you cannot answer work messages late at night, decide how you will handle messages that arrive then. Some people may need time to adjust, but repeated pressure does not mean the boundary is unreasonable.",
"Boundaries should allow room for mutual respect and practical compromise. Review them when circumstances change, and listen to the needs of others without abandoning your own safety. If a situation involves threats, coercion or abuse, seek trusted support and prioritise safety."
],
"How to Make Better Use of Your Community Library": [
"A community library can offer more than shelves of books. Depending on the location, it may provide reference materials, study space, newspapers, internet access, children's activities and guidance from staff who know the available resources.",
"Start by learning the library's membership rules, opening hours and borrowing limits. Ask whether registration requires identification, whether there are fees and how renewals or overdue items are handled. Knowing the basic rules makes it easier to use the service confidently.",
"Tell a librarian what you are trying to find rather than searching only by a broad subject. Staff may know useful catalogues, reference works, local archives or trustworthy online databases that are difficult to discover through a general search engine.",
"Use the library as a place for focused learning. Set a clear goal for each visit, bring a list of questions and record the title or source of useful information. Respect shared study spaces and follow local rules about devices, food and noise.",
"Support the library by returning borrowed materials on time, treating shared resources carefully and sharing accurate information about its services. If a book or resource is missing, ask whether an inter-library request or another legitimate source is available."
],
}


EXTENSIONS = {
"How to Think Clearly When the Internet Is Overwhelming": ["Keep a short evidence note with the claim, source, date and unanswered questions. This is useful when a story is developing because early reports can change. Revisit the note only when meaningful new evidence appears, rather than repeatedly refreshing a feed that has no new information.", "Set a stopping rule for research. Decide how long to investigate and what level of evidence is enough for the decision. A routine purchase may need limited checking, while a safety or financial decision deserves more care. Match the effort to the possible consequences."],
"How to Use AI as a Tool Without Letting It Think for You": ["For important work, ask the system to explain the reasoning behind a recommendation and compare it with the original evidence. Review every factual statement before submitting or publishing the result, and make sure the final work reflects your own understanding rather than language you cannot explain.", "Watch for invented references, outdated instructions, missing exceptions and assumptions about your circumstances. For sensitive matters, use AI to organise information or prepare questions, then consult an appropriate professional or authoritative source before acting."],
"A Practical Guide to Building Better Study Habits": ["Keep an error log. For each missed question, record whether the problem came from forgetting a fact, misunderstanding a concept, choosing the wrong method or rushing. Review the log before the next session and choose practice that addresses the cause; repeating questions without understanding the error can create an illusion of progress.", "Make the study environment repeatable. Decide where materials will be kept, what you will do when a session begins and how you will record the next task. If interruptions are unavoidable, leave a short restart note so you can return to the exact point where you stopped."],
"How to Spot Misleading Information Online": ["Check numbers and charts as carefully as words. A percentage without a denominator can make a small change look dramatic, while a graph with an unusual baseline can exaggerate a difference. Look for the original dataset, period covered and population measured before sharing a statistical claim.", "Label developing claims as confirmed by primary evidence, independently reported, attributed to a source or unverified. These labels help prevent uncertain information from becoming more definite each time it is repeated. Update or correct a post when stronger evidence changes the picture."],
"Why Small Daily Habits Often Beat Sudden Motivation": ["Design a minimum version for difficult days. If your normal routine is a thirty-minute study session, the minimum might be opening the notes and reviewing one concept. This keeps the cue familiar without pretending every day will be equally productive.", "Review the routine weekly. A streak is only a measurement, not the goal itself. If a habit consumes time without improving the outcome you intended, adjust it. A good habit should make life more manageable, not become another source of guilt."],
"How to Manage Money When Income Is Irregular": ["Separate money by purpose as soon as it arrives. Even without separate accounts, a written allocation can distinguish housing, food, transport, savings and flexible spending. Keep the plan realistic: assigning every naira before essential costs are known can create pressure to borrow when an unexpected bill appears.", "Be wary of guaranteed-return offers, instant loans with unclear charges or jobs that require payment before work begins. Read the total repayment amount and fees before accepting credit. If you cannot explain how an offer works, pause and seek independent advice."],
"How to Protect Your Digital Privacy on a Phone": ["Review account recovery options as carefully as passwords. Keep recovery email addresses and phone numbers current, save backup codes somewhere separate from the device and remove old devices you no longer control from account sessions. If a phone is lost, secure the main email account first.", "Before installing an app, check its developer, update history and requested permissions. Read reviews for patterns rather than relying on one comment. An app asking for contacts, SMS or accessibility access without a clear reason deserves extra scrutiny."],
"How to Have Better Conversations During Disagreements": ["Some disagreements are negotiations about practical arrangements. Identify what each person needs, what is flexible and what is not. Suggest a specific trial arrangement and agree when to review it; a small experiment can be easier to assess than an argument about who is generally right.", "Do not confuse agreement with understanding. You can accurately describe another person's position and still disagree. If no shared solution is possible, state the point of difference and decide what boundary or next step is necessary."],
"What Critical Thinking Really Means in Everyday Life": ["Watch for reasoning traps. A claim is not true simply because many people repeat it, and expertise in one field does not make every opinion authoritative. Be cautious of false choices that present only two options when several alternatives may exist.", "Apply standards proportionate to risk. A low-cost everyday choice may need limited checking, but decisions involving health, legal rights, large payments or personal safety require stronger evidence. Record important assumptions and revisit them when circumstances change."],
"How to Learn Difficult Subjects Without Burning Out": ["Ask for help with a precise question. Show the step where your understanding breaks down and explain what you have already tried. A teacher or study partner can then respond to the actual difficulty. Keep unresolved questions in one place so a single confusing point does not derail the whole session.", "Measure progress by what you can do without assistance. Completing a chapter is not the same as explaining it or applying it to a new example. Short self-tests provide evidence of learning and help you choose the next topic more accurately than counting pages."],
"How to Make Better Decisions With Limited Information": ["Separate facts, estimates and assumptions in your notes. A fact should be traceable to evidence; an estimate should show its basis; an assumption should be labelled as unverified. This makes it easier to see which part of the decision would change if new information arrived.", "Ask what would make you stop or reverse the decision. Set a spending limit, time limit or condition that triggers another review. A decision process is safer when it includes not only a reason to proceed but also a clear signal to pause."],
"How to Build a Simple Personal Knowledge System": ["Use a consistent note format: descriptive title, main point, source link, date accessed and your own comment. Keep quotations clearly marked and preserve enough source information to find the original. This makes later writing more accurate and reduces accidental plagiarism.", "Do not confuse collecting with understanding. Each week, turn one note into something useful: a question, a summary in your own words, a decision or a small task. Archive notes that no longer matter; the system should support real work, not become an endless filing project."],
"How to Evaluate an Online Course Before Paying": ["Look closely at assessment. A course may contain many videos but offer little opportunity to practise. Check whether learners complete realistic assignments, receive useful feedback and can see examples of successful work. For practical subjects, a project or demonstration may be more informative than a certificate alone.", "Check access and support before enrolling. Find out whether lessons work on a phone and with limited data, whether subtitles or downloadable materials are available, and how questions are answered. Confirm that examples and requirements are relevant to your location and goals."],
"How to Prepare for a Job Interview With Confidence": ["Prepare for questions about availability, pay expectations and work arrangements. Know the minimum conditions you can accept, and ask how the employer defines hours, targets, probation and payment dates. A genuine employer should explain the basic terms without demanding an unexplained payment from an applicant.", "After the interview, note difficult questions while the experience is fresh and practise stronger answers. If you receive an offer, read the terms carefully and verify the organisation before sharing sensitive documents. Confidence comes from preparation and honest communication, not memorised speeches."],
"Understanding Your Digital Footprint and Online Reputation": ["Review older accounts as well as profiles you use daily. Forgotten forums, public document links and unused applications can still expose personal details. Close accounts you no longer need, remove public access to old files and update recovery settings before abandoning an account.", "Think about context and permanence when sharing opinions or achievements. Keep professional profiles accurate and current. If incorrect information about you appears online, preserve evidence, contact the platform through its official process and avoid escalating matters with threats or unsupported claims."],
"How to Recognise Common Online Job Scams": ["Watch for recruitment messages that move quickly from an interview to requests for money or sensitive documents. Check whether the email domain matches the employer's real website and whether the recruiter can be verified through an independently found company contact. A copied logo is not proof.", "If you have paid, contact your bank or payment provider immediately and preserve receipts, account names, phone numbers and messages. Do not pay a second person who promises recovery for an advance fee; recovery scams often target the same victims."],
"A Practical Guide to Setting Healthy Boundaries": ["Expect that a boundary may need to be repeated, especially when a pattern has existed for a long time. Keep the message brief and focus on the action you will take rather than trying to force agreement. You can end a call that becomes abusive or decline an unsafe request.", "Review boundaries as responsibilities change. A limit that works during a quiet period may need adjustment during exams, caregiving or demanding work. Communicate changes early and make room for reasonable reciprocal needs without surrendering safety or dignity."],
"How to Make Better Use of Your Community Library": ["Ask whether the library provides digital catalogues, learning databases, public computers or services that can be used outside the building. Some libraries also host reading groups and literacy programmes. A short conversation with staff can reveal services that are not obvious from the shelves.", "Use more than one source when researching. Library books can provide background, while current official publications may be needed for recent rules or statistics. Record author, title, publisher and date so you can locate the source again."]
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
    return CONTENT.get(title, []) + EXTENSIONS.get(title, [])


def validate_article(title: str, paragraphs: list[str]) -> list[str]:
    errors = []
    if len(paragraphs) < 5:
        errors.append("At least five topic-specific paragraphs are required.")
    if any(len(p.split()) < 25 for p in paragraphs):
        errors.append("Every paragraph must contain at least 25 words.")
    if not paragraphs or title.lower() in paragraphs[0].lower():
        errors.append("The opening must be a real summary, not a repeated title.")
    if len(" ".join(paragraphs).split()) < 300:
        errors.append("Article body must contain at least 300 words for a full feature.")
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

    # On scheduled runs, repair all existing placeholder/short articles in one
    # pass so the site does not need a separate workflow run for each bad page.
    if not requested:
        repaired = []
        entry_by_title = {str(x.get("title", "")).strip().lower(): x for x in entries if isinstance(x, dict)}
        for candidate_title, candidate_category in TOPICS:
            old_entry = entry_by_title.get(candidate_title.lower())
            if not old_entry:
                continue
            old_path = ARTICLES / str(old_entry.get("file", ""))
            if not old_path.is_file():
                continue
            old_text = html.unescape(re.sub(r"<[^>]+>", " ", old_path.read_text(encoding="utf-8", errors="replace")))
            old_text = re.sub(r"\s+", " ", old_text).strip()
            if len(old_text.split()) >= 300:
                continue
            paragraphs = article_body(candidate_title)
            errors = validate_article(candidate_title, paragraphs)
            if errors:
                continue
            document, summary = render(candidate_title, candidate_category, paragraphs, now)
            filename = f"{slug(candidate_title)}.html"
            (ARTICLES / filename).write_text(document, encoding="utf-8")
            old_entry.update({"file": filename, "title": candidate_title, "summary": summary, "category": candidate_category, "date": now.strftime("%d %b %Y")})
            repaired.append({"title": candidate_title, "file": filename, "word_count": len(" ".join(paragraphs).split())})
        if repaired:
            entries.sort(key=lambda x: (str(x.get("date", "")), str(x.get("title", ""))), reverse=True)
            INDEX.write_text(json.dumps(entries[:100], ensure_ascii=False, indent=2), encoding="utf-8")
            report = {"finished_utc": now.isoformat(), "mode": "batch-quality-repair", "published": True, "repaired_count": len(repaired), "repaired_articles": repaired, "quality_checks": "passed", "note": "Existing short/template articles were replaced with topic-specific editorial content."}
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
    if requested:
        chosen = next(((t, c) for t, c in TOPICS if t.lower() == requested.lower()), None)
        if chosen is None:
            report = {"finished_utc": now.isoformat(), "published": False, "reason": "Requested topic is not in the reviewed topic catalogue; refusing to publish generic filler.", "requested_topic": requested}
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit(2)
    else:
        # Repair low-quality existing entries first; only then create a new topic.
        chosen = None
        for candidate_title, candidate_category in TOPICS:
            old_entry = next((x for x in entries if str(x.get("title", "")).strip().lower() == candidate_title.lower()), None)
            if not old_entry:
                continue
            old_path = ARTICLES / str(old_entry.get("file", ""))
            old_text = ""
            if old_path.is_file():
                old_text = re.sub(r"<[^>]+>", " ", old_path.read_text(encoding="utf-8", errors="replace"))
                old_text = html.unescape(re.sub(r"\s+", " ", old_text)).strip()
            if len(old_text.split()) < 300:
                chosen = (candidate_title, candidate_category)
                break
        if chosen is None:
            chosen = next(((t, category) for t, category in TOPICS if t.lower() not in titles), None)
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

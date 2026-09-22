from __future__ import annotations
import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"academic-jobs-data"/"updates.json"
OUT.parent.mkdir(parents=True,exist_ok=True)
UA="COEricAcademicJobs/1.0"
MODEL="gemini-3.5-flash-lite"

SOURCES=[
 {"kind":"academic","name":"JAMB","url":"https://www.jamb.gov.ng/"},
 {"kind":"academic","name":"NECO","url":"https://neco.gov.ng/"},
 {"kind":"academic","name":"WAEC Nigeria","url":"https://www.waecnigeria.org/"},
 {"kind":"academic","name":"NUC","url":"https://www.nuc.edu.ng/"},
 {"kind":"academic","name":"Federal Ministry of Education Scholarship Portal","url":"https://scholarship.education.gov.ng/"},
 {"kind":"academic","name":"NYSC","url":"https://www.nysc.gov.ng/"},
 {"kind":"academic","name":"NABTEB","url":"https://nabteb.gov.ng/"},
 {"kind":"jobs","name":"Jobberman Nigeria","url":"https://www.jobberman.com/jobs"},
 {"kind":"jobs","name":"MyJobMag Nigeria","url":"https://www.myjobmag.com/"},
]

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read().decode("utf-8","ignore")
    text=re.sub(r"<script\b[^>]*>.*?</script>"," ",raw,flags=re.I|re.S)
    text=re.sub(r"<style\b[^>]*>.*?</style>"," ",text,flags=re.I|re.S)
    text=re.sub(r"<[^>]+>"," ",text)
    text=html.unescape(re.sub(r"\s+"," ",text)).strip()
    return raw,text

def source_record(s):
    try:
        raw,text=fetch(s["url"])
        return {**s,"text":text[:14000],"raw":raw[:400000]}
    except Exception as e:
        return {**s,"text":"","raw":"","error":str(e)}

def ask_ai(records):
    key=os.environ.get("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is missing")
    prompt="""You are the C. O. Eric Academic & Jobs updater. Build a small set of factual, useful updates from the supplied CURRENT source pages.

Rules:
- Use ONLY facts explicitly present in the supplied source text.
- Never invent vacancies, dates, salaries, eligibility, deadlines, employers, links or application instructions.
- For academic updates, prefer official announcements, registration information, deadlines, admissions information, scholarship notices and student services.
- For jobs, publish only job opportunities that are explicitly visible in the supplied job-board text. Preserve the job-board application URL when available.
- If a source has no clear useful update, omit it.
- Do not state that a vacancy is still open unless the source indicates it.
- No political persuasion or political commentary.
- No sexually explicit content.
- Return at most 20 items total.
- Each item must have kind academic|jobs, title, summary, source_name, source_url, published_or_checked, and original_link. original_link MUST be one of the supplied URLs unless a specific job URL is explicitly present in the source record.
- For jobs, include location and work_type only when explicitly present.
- For academic items, include deadline only when explicitly present.
- Use concise original wording.

Return ONLY JSON:
{"updates":[{"kind":"academic|jobs","title":"...","summary":"...","source_name":"...","source_url":"...","published_or_checked":"...","original_link":"...","location":"...","work_type":"...","deadline":"..."}]}

SOURCE RECORDS:
"""
    payload={"contents":[{"parts":[{"text":prompt+json.dumps([{k:v for k,v in r.items() if k!="raw"} for r in records],ensure_ascii=False)}]}],
             "generationConfig":{"responseMimeType":"application/json"}}
    endpoint="https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent?key="+urllib.parse.quote(key)
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=90) as r:
        data=json.loads(r.read())
    return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])

records=[source_record(s) for s in SOURCES]
result=ask_ai(records)
updates=[]
for item in result.get("updates",[])[:20]:
    if item.get("kind") not in ("academic","jobs") or not item.get("title") or not item.get("summary"): continue
    item["checked_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    if not item.get("original_link"): item["original_link"]=item.get("source_url","")
    updates.append(item)

OUT.write_text(json.dumps({"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"updates":updates},ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Wrote {len(updates)} verified-source academic/jobs updates to {OUT}")

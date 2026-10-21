#!/usr/bin/env python3
"""Update the Video Hub from curated YouTube channels."""
from __future__ import annotations
import html, json, os, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_FILE=ROOT/"video_sources.json"
INDEX_FILE=ROOT/"videos"/"index.json"
REPORT_FILE=ROOT/"newsroom-data"/"video-report.json"
MAX_NEW_VIDEOS=30
MAX_PER_CHANNEL=5
MAX_SELECTED_PER_CHANNEL=2
MAX_SHORTS_PER_RUN=10
USER_AGENT="C-O-Eric-Video-Hub/3.0"
ATOM={"a":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}

KNOWLEDGE_TERMS=("how","why","explained","explainer","science","technology","ai","artificial intelligence","engineering","experiment","documentary","history","discovery","nature","wildlife","space","future","innovation","behind the scenes","making","build","repair","fix","guide","tutorial","demonstration","process","business","money","economy","entrepreneur","startup","design","infrastructure","environment","climate","health","culture","society","interview","deep dive","case study","facts","myth","craft","practical","invention","architecture","education","learning","study")
MEDIA_TERMS=("anime","donghua","animation","manga","amv","anime music video","gospel","worship","christian","jesus","church","praise","word of god","music","song","singer","concert","performance","official audio","lyrics","lofi","vevo","colors","afrobeats","african music")
PROMO_TERMS=("reaction","red carpet","official trailer","official teaser","teaser trailer","movie clip","tv spot")
MEDIA_CATEGORIES=("anime","donghua","amv","gospel","worship","music","african music")

def fetch(url:str,timeout:int=25)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json,application/xml,text/xml"})
    with urllib.request.urlopen(req,timeout=timeout) as response:return response.read()

def resolve_channel_id(source:dict)->tuple[str|None,str]:
    explicit=str(source.get("channel_id","")).strip()
    if explicit.startswith("UC"):return explicit,"configured"
    key=os.environ.get("YOUTUBE_API_KEY","").strip()
    if key:
        try:
            q=urllib.parse.urlencode({"part":"id","forHandle":source["handle"],"maxResults":"1","key":key})
            data=json.loads(fetch("https://www.googleapis.com/youtube/v3/channels?"+q).decode())
            items=data.get("items") or []
            if items and items[0].get("id"):return items[0]["id"],"youtube_api"
        except Exception:pass
    handle=str(source.get("handle","")).strip()
    if handle:
        try:
            page=fetch("https://www.youtube.com/"+urllib.parse.quote(handle.lstrip("/"),safe="@")).decode("utf-8",errors="replace")
            for pattern in (r'"channelId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"',r'"externalId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"',r'youtube\.com/channel/(UC[A-Za-z0-9_-]{22})'):
                match=re.search(pattern,page)
                if match:return match.group(1),"youtube_handle"
        except Exception:pass
    return None,"unresolved"

def score_video(title:str,category:str,is_short:bool)->int:
    text=f"{title} {category}".lower()
    media=any(term in text for term in MEDIA_TERMS) or any(term in category.lower() for term in MEDIA_CATEGORIES)
    score=50 if not is_short else 18
    score+=sum(7 for term in KNOWLEDGE_TERMS if term in text)
    if media:
        score+=45
        score+=sum(6 for term in MEDIA_TERMS if term in text)
        score-=sum(12 for term in PROMO_TERMS if term in text)
    else:
        score-=sum(30 for term in PROMO_TERMS if term in text)
    return score

def parse_feed(channel_id:str,source:dict)->list[dict]:
    root=ET.fromstring(fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={urllib.parse.quote(channel_id)}"))
    entries=[]
    for entry in root.findall("a:entry",ATOM)[:MAX_PER_CHANNEL]:
        video_id=(entry.findtext("yt:videoId",default="",namespaces=ATOM) or "").strip()
        title=(entry.findtext("a:title",default="",namespaces=ATOM) or "").strip()
        published=(entry.findtext("a:published",default="",namespaces=ATOM) or "").strip()
        updated=(entry.findtext("a:updated",default="",namespaces=ATOM) or "").strip()
        link=next((x.get("href") for x in entry.findall("a:link",ATOM) if x.get("rel")=="alternate"),"")
        if not video_id or not title or not link:continue
        is_short="/shorts/" in link.lower()
        clean=html.unescape(title)
        score=score_video(clean,source["category"],is_short)
        if score<25:continue
        entries.append({"video_id":video_id,"title":clean,"category":source["category"],"channel":source["name"],"channel_id":channel_id,"channel_url":f"https://www.youtube.com/channel/{channel_id}","url":link,"embed_url":f"https://www.youtube-nocookie.com/embed/{video_id}","thumbnail":f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg","published_at":published or updated,"source":"YouTube channel feed","is_short":is_short,"selection_priority":score})
    return entries

def parse_iso(value:str)->datetime:
    try:return datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception:return datetime.min.replace(tzinfo=timezone.utc)

def fallback_description(item:dict)->str:
    return f'{item["channel"]} — {item["title"]}. Watch the original video on YouTube.'

def ai_description(item:dict)->str:
    key=os.environ.get("GEMINI_API_KEY","").strip()
    if not key:return fallback_description(item)
    prompt=("Write one concise editorial description for a video card. Only paraphrase information explicitly present in the title, channel and category. Do not invent facts. 15-30 words. Plain text only.\n"+f'Category: {item["category"]}\nChannel: {item["channel"]}\nTitle: {item["title"]}')
    body=json.dumps({"contents":[{"parts":[{"text":prompt}]}]}).encode()
    url="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key="+urllib.parse.quote(key)
    req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json","User-Agent":USER_AGENT},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=25) as response:data=json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip() or fallback_description(item)
    except Exception:return fallback_description(item)

def load_index()->dict:
    try:return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:return {"updated_at":None,"videos":[]}

def main()->None:
    INDEX_FILE.parent.mkdir(parents=True,exist_ok=True);REPORT_FILE.parent.mkdir(parents=True,exist_ok=True)
    config=json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    allowed={str(s.get("name","")).strip() for s in config}
    index=load_index();videos=[v for v in index.get("videos",[]) if v.get("channel") in allowed];existing={v.get("video_id") for v in videos if v.get("video_id")}
    discovered=[];errors=[];methods={}
    for source in config:
        cid,method=resolve_channel_id(source);methods[source["name"]]=method
        if not cid:errors.append({"channel":source["name"],"error":"Could not resolve stable YouTube channel ID"});continue
        try:discovered.extend(parse_feed(cid,source))
        except Exception as exc:errors.append({"channel":source["name"],"error":str(exc)})
    discovered.sort(key=lambda v:(v.get("selection_priority",0),parse_iso(v.get("published_at",""))),reverse=True)
    selected=[];selected_ids=set();by_channel={};shorts=0;duplicates=0
    for item in discovered:
        vid=item["video_id"];channel=item["channel"]
        if vid in existing or vid in selected_ids:duplicates+=1;continue
        if by_channel.get(channel,0)>=MAX_SELECTED_PER_CHANNEL:continue
        if item.get("is_short") and shorts>=MAX_SHORTS_PER_RUN:continue
        selected.append(item);selected_ids.add(vid);by_channel[channel]=by_channel.get(channel,0)+1
        if item.get("is_short"):shorts+=1
        if len(selected)>=MAX_NEW_VIDEOS:break
    for item in selected:
        item["description"]=ai_description(item);item["published_by_pipeline_at"]=datetime.now(timezone.utc).isoformat();item.pop("selection_priority",None)
    before=len(videos);videos.extend(selected);videos.sort(key=lambda v:parse_iso(v.get("published_at","")),reverse=True);videos=videos[:150]
    index["updated_at"]=datetime.now(timezone.utc).isoformat();index["videos"]=videos;INDEX_FILE.write_text(json.dumps(index,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    report={"finished_utc":datetime.now(timezone.utc).isoformat(),"max_new_videos_per_run":MAX_NEW_VIDEOS,"max_selected_per_channel":MAX_SELECTED_PER_CHANNEL,"max_shorts_per_run":MAX_SHORTS_PER_RUN,"channels_configured":len(config),"channels_resolved":len(config)-len(errors),"resolver_methods":methods,"channels_with_errors":errors,"discovered":len(discovered),"published":len(selected),"shorts_published":shorts,"duplicates_skipped":duplicates,"pruned_feed_videos":max(0,before+len(selected)-len(videos)),"total_stored":len(videos),"published_video_ids":[x["video_id"] for x in selected]}
    REPORT_FILE.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=="__main__":main()

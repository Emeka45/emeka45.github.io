#!/usr/bin/env python3
"""Discover recent videos from curated YouTube channels and update the Video Hub.

Channel discovery uses stable YouTube channel IDs, optional YouTube Data API
resolution, and Wikidata as a no-key fallback. The selection pipeline favors
full-length videos, trailers, announcements and launches over Shorts.
"""

from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "video_sources.json"
INDEX_FILE = ROOT / "videos" / "index.json"
REPORT_FILE = ROOT / "newsroom-data" / "video-report.json"
MAX_NEW_VIDEOS = 20
MAX_PER_CHANNEL = 5
MAX_SHORTS_PER_RUN = 6
USER_AGENT = "C-O-Eric-Video-Hub/1.2 (+https://emeka45-github-io.pages.dev/videos.html)"
ATOM = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html,application/atom+xml,application/xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def resolve_channel_id(source: dict) -> tuple[str | None, str]:
    explicit = str(source.get("channel_id", "")).strip()
    if explicit.startswith("UC"):
        return explicit, "configured"

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if api_key:
        query = urllib.parse.urlencode(
            {"part": "id", "forHandle": source["handle"], "maxResults": "1", "key": api_key}
        )
        try:
            data = json.loads(fetch("https://www.googleapis.com/youtube/v3/channels?" + query).decode())
            items = data.get("items") or []
            if items and items[0].get("id"):
                return items[0]["id"], "youtube_api"
        except Exception:
            pass

    search_q = urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "search": source["name"],
            "language": "en",
            "format": "json",
            "limit": "5",
        }
    )
    try:
        results = json.loads(fetch("https://www.wikidata.org/w/api.php?" + search_q).decode())
        for result in results.get("search", []):
            qid = result.get("id", "")
            if not qid.startswith("Q"):
                continue
            entity = json.loads(
                fetch(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json").decode()
            )
            claims = entity.get("entities", {}).get(qid, {}).get("claims", {}).get("P2397", [])
            for claim in claims:
                value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(value, str) and value.startswith("UC"):
                    return value, "wikidata"
    except Exception:
        pass

    return None, "unresolved"


def parse_feed(channel_id: str, source: dict) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={urllib.parse.quote(channel_id)}"
    root = ET.fromstring(fetch(url))
    entries = []
    for entry in root.findall("a:entry", ATOM)[:MAX_PER_CHANNEL]:
        video_id = (entry.findtext("yt:videoId", default="", namespaces=ATOM) or "").strip()
        title = (entry.findtext("a:title", default="", namespaces=ATOM) or "").strip()
        published = (entry.findtext("a:published", default="", namespaces=ATOM) or "").strip()
        updated = (entry.findtext("a:updated", default="", namespaces=ATOM) or "").strip()
        link = next(
            (x.get("href") for x in entry.findall("a:link", ATOM) if x.get("rel") == "alternate"),
            "",
        )
        if not video_id or not title or not link:
            continue

        is_short = "/shorts/" in link.lower()
        clean_title = html.unescape(title)
        title_lower = clean_title.lower()
        priority = 0
        if not is_short:
            priority += 100
        if any(term in title_lower for term in (
            "official trailer", "official teaser", "launch trailer", "announcement trailer",
            "release date", "first look", "official announcement", "gameplay trailer",
            "teaser trailer", "reveal trailer"
        )):
            priority += 30
        if any(term in title_lower for term in ("trailer", "teaser", "announcement", "launch", "reveal")):
            priority += 10

        entries.append(
            {
                "video_id": video_id,
                "title": clean_title,
                "category": source["category"],
                "channel": source["name"],
                "channel_id": channel_id,
                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                "url": link,
                "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}",
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "published_at": published or updated,
                "source": "YouTube channel feed",
                "is_short": is_short,
                "selection_priority": priority,
            }
        )
    return entries


def parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def fallback_description(item: dict) -> str:
    return (
        f'{item["channel"]} — {item["title"]}. '
        "Watch the original video on YouTube."
    )


def ai_description(item: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return fallback_description(item)

    prompt = (
        "Write one concise editorial description for a website video card. "
        "You may ONLY paraphrase information explicitly present in the video title, "
        "channel name and category. Do not infer plot, gameplay, characters, dates, "
        "release status, opinions, quotes or other facts. If the title gives little "
        "information, keep the description simple. 15-30 words. Return plain text only.\n"
        f'Category: {item["category"]}\nChannel: {item["channel"]}\nTitle: {item["title"]}'
    )
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.5-flash-lite:generateContent?key="
        + urllib.parse.quote(api_key)
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or fallback_description(item)
    except Exception:
        return fallback_description(item)


def load_index() -> dict:
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"updated_at": None, "videos": []}


def main() -> None:
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    config = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    index = load_index()
    videos = index.get("videos", [])
    existing = {v.get("video_id") for v in videos if v.get("video_id")}

    discovered = []
    channel_errors = []
    resolver_methods = {}
    for source in config:
        channel_id, method = resolve_channel_id(source)
        resolver_methods[source["name"]] = method
        if not channel_id:
            channel_errors.append(
                {"channel": source["name"], "error": "Could not resolve stable YouTube channel ID"}
            )
            continue
        try:
            discovered.extend(parse_feed(channel_id, source))
        except Exception as exc:
            channel_errors.append({"channel": source["name"], "error": str(exc)})

    discovered.sort(
        key=lambda v: (v.get("selection_priority", 0), parse_iso(v["published_at"])),
        reverse=True,
    )

    selected = []
    selected_ids = set()
    duplicates_skipped = 0
    shorts_selected = 0

    for item in discovered:
        if item["video_id"] in existing or item["video_id"] in selected_ids:
            duplicates_skipped += 1
            continue
        if item.get("is_short") and shorts_selected >= MAX_SHORTS_PER_RUN:
            continue
        selected.append(item)
        selected_ids.add(item["video_id"])
        if item.get("is_short"):
            shorts_selected += 1
        if len(selected) >= MAX_NEW_VIDEOS:
            break

    for item in selected:
        item["description"] = ai_description(item)
        item["published_by_pipeline_at"] = datetime.now(timezone.utc).isoformat()
        # Internal selection metadata is useful for diagnostics but unnecessary in the UI.
        item.pop("selection_priority", None)

    videos.extend(selected)
    videos.sort(key=lambda v: parse_iso(v.get("published_at", "")), reverse=True)
    videos = videos[:100]
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index["videos"] = videos
    INDEX_FILE.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report = {
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "max_new_videos_per_run": MAX_NEW_VIDEOS,
        "max_shorts_per_run": MAX_SHORTS_PER_RUN,
        "channels_configured": len(config),
        "channels_resolved": len(config) - len(channel_errors),
        "resolver_methods": resolver_methods,
        "channels_with_errors": channel_errors,
        "discovered": len(discovered),
        "published": len(selected),
        "shorts_published": shorts_selected,
        "duplicates_skipped": duplicates_skipped,
        "total_stored": len(videos),
        "published_video_ids": [x["video_id"] for x in selected],
    }
    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

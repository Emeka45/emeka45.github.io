#!/usr/bin/env python3
"""Monitor configured RSS/Atom feeds and maintain a metadata-only anime release index.

The monitor never downloads video or subtitle payloads. It records source-page URLs,
release metadata, and rights declarations supplied by a repository maintainer.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MAX_FEED_BYTES = 5 * 1024 * 1024
USER_AGENT = "Emeka45-AnimeReleaseMonitor/1.0 (+https://emeka45.github.io/)"
RESOLUTION_RE = re.compile(r"(?<!\d)(240|360|480|540|576|720|1080|1440|2160)\s*p(?!\d)", re.I)
SEASON_EPISODE_RE = re.compile(r"\bS\d{1,2}\s*E\d{1,3}\b", re.I)
EPISODE_RE = re.compile(r"\b(?:episode|ep\.?|e)\s*[-#:]?\s*(\d{1,4})(?!\d)", re.I)
ENGLISH_SUB_RE = re.compile(r"(?:english\s*(?:sub(?:title)?s?)?|eng\s*sub|en\s*sub|\[en\])", re.I)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def plain_text(value: str, limit: int = 500) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value or "")
        result = " ".join(parser.parts)
    except Exception:
        result = re.sub(r"<[^>]*>", " ", value or "")
    return html.unescape(" ".join(result.split()))[:limit]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in element.iter():
        if child is element:
            continue
        if _local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def _entry_link(element: ET.Element) -> str:
    for child in element:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "alternate")
        if href and rel in ("alternate", ""):
            return href
        if child.text and child.text.strip():
            return child.text.strip()
    return _child_text(element, "link")


def _safe_https_url(value: str, field: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{field} must be a public HTTPS URL")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or "." not in host:
        raise ValueError(f"{field} must use a public hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError(f"{field} cannot point to a private or reserved IP address")
    return value


def validate_sources(document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("schema_version") != 1:
        raise ValueError("sources file must use schema_version 1")
    sources = document.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")
    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f"source {index + 1} must be an object")
        source_id = str(source.get("id", "")).strip()
        name = str(source.get("name", "")).strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", source_id):
            raise ValueError(f"source {index + 1} has an invalid id")
        if source_id in seen_ids:
            raise ValueError(f"duplicate source id: {source_id}")
        seen_ids.add(source_id)
        if not name:
            raise ValueError(f"source {source_id} requires a name")
        feed_url = _safe_https_url(str(source.get("feed_url", "")), f"{source_id}.feed_url")
        rights_status = source.get("rights_status", "metadata_only")
        if rights_status not in {"metadata_only", "redistribution_authorized"}:
            raise ValueError(f"source {source_id} has an unsupported rights_status")
        item: dict[str, Any] = {
            "id": source_id,
            "name": name,
            "feed_url": feed_url,
            "rights_status": rights_status,
        }
        if source.get("homepage_url"):
            item["homepage_url"] = _safe_https_url(str(source["homepage_url"]), f"{source_id}.homepage_url")
        if source.get("license"):
            item["license"] = str(source["license"]).strip()[:160]
        if rights_status == "redistribution_authorized":
            if not item.get("license"):
                raise ValueError(f"authorized source {source_id} requires a license")
            evidence = source.get("rights_evidence_url")
            if not evidence:
                raise ValueError(f"authorized source {source_id} requires rights_evidence_url")
            item["rights_evidence_url"] = _safe_https_url(str(evidence), f"{source_id}.rights_evidence_url")
        normalized.append(item)
    return normalized


def parse_episode(title: str) -> str | None:
    season_match = SEASON_EPISODE_RE.search(title)
    if season_match:
        return re.sub(r"\s+", "", season_match.group(0)).upper()
    episode_match = EPISODE_RE.search(title)
    return str(int(episode_match.group(1))) if episode_match else None


def parse_release_hints(title: str) -> dict[str, Any]:
    resolutions = sorted({int(value) for value in RESOLUTION_RE.findall(title)})
    languages = ["English"] if ENGLISH_SUB_RE.search(title) else []
    return {"resolutions": resolutions, "subtitle_languages": languages}


def stable_release_id(source_id: str, guid: str, title: str) -> str:
    identity = guid.strip() or title.strip()
    digest = hashlib.sha256(f"{source_id}\0{identity}".encode("utf-8")).hexdigest()[:20]
    return f"rel-{digest}"


def _published_at(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_feed(xml_bytes: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    entries = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
    releases: list[dict[str, Any]] = []
    for entry in entries:
        title = _child_text(entry, "title")
        link = _entry_link(entry)
        if not title or not link:
            continue
        parsed_link = urllib.parse.urlparse(link)
        if parsed_link.scheme not in {"https", "http"} or not parsed_link.netloc:
            continue
        guid = _child_text(entry, "guid", "id") or link
        description = _child_text(entry, "description", "summary", "content", "encoded")
        published = _child_text(entry, "pubdate", "published", "updated", "date")
        hints = parse_release_hints(title + " " + description)
        releases.append({
            "id": stable_release_id(source["id"], guid, title),
            "title": plain_text(title, 220),
            "episode": parse_episode(title),
            "published_at": _published_at(published),
            "source_id": source["id"],
            "source_name": source["name"],
            "source_url": link,
            "summary": plain_text(description),
            "resolutions": hints["resolutions"],
            "subtitle_languages": hints["subtitle_languages"],
            "rights_status": source["rights_status"],
            "license": source.get("license"),
            "rights_evidence_url": source.get("rights_evidence_url"),
        })
    return releases


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.5",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        _safe_https_url(response.geturl(), "feed redirect URL")
        data = response.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError(f"feed exceeds {MAX_FEED_BYTES} bytes")
    return data


def build_index(sources: list[dict[str, Any]], fetched_at: datetime | None = None) -> dict[str, Any]:
    collected: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for source in sources:
        try:
            for release in parse_feed(fetch_feed(source["feed_url"]), source):
                collected[release["id"]] = release
        except Exception as exc:
            errors.append(f"{source['id']}: {type(exc).__name__}: {exc}")
    if errors:
        raise RuntimeError("One or more configured feeds failed; index was not written: " + " | ".join(errors))
    releases = list(collected.values())
    releases.sort(key=lambda item: (item["published_at"] or "", item["title"].casefold()), reverse=True)
    return {
        "schema_version": 1,
        "generated_at": (fetched_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_count": len(sources),
        "release_count": len(releases),
        "policy": "Metadata index only. No video or subtitle files are downloaded. Redistribution is enabled only for sources with explicit licence and rights-evidence records.",
        "releases": releases[:500],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default="anime-release-sources.json")
    parser.add_argument("--output", default="anime-release-index.json")
    args = parser.parse_args(argv)
    document = json.loads(Path(args.sources).read_text(encoding="utf-8"))
    sources = validate_sources(document)
    index = build_index(sources)
    Path(args.output).write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {index['release_count']} releases from {index['source_count']} configured feeds.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

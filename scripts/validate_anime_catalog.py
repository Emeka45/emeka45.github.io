#!/usr/bin/env python3
"""Validate the Anime & Donghua catalogue before publishing."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

MANIFEST = Path(__file__).resolve().parents[1] / "anime-downloads.json"
VALID_KINDS = {"anime", "donghua"}
VALID_SUBTITLE_STATES = {"verified", "provider-listed", "unknown", "unavailable"}


def is_https_url(value):
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def has_english_track(tracks):
    return any(
        isinstance(track, dict)
        and str(track.get("lang", "")).lower().startswith("en")
        and is_https_url(track.get("url", ""))
        for track in tracks
    )


def main():
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot parse {MANIFEST}: {exc}")
        return 1

    titles = data.get("titles")
    if not isinstance(titles, list) or not titles:
        print("ERROR: titles must be a non-empty array")
        return 1

    errors = []
    seen = set()
    for index, item in enumerate(titles):
        label = item.get("title", f"item {index + 1}") if isinstance(item, dict) else f"item {index + 1}"
        if not isinstance(item, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        for field in ("id", "title"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{label}: missing non-empty {field}")
        item_id = item.get("id")
        if item_id in seen:
            errors.append(f"{label}: duplicate id {item_id}")
        seen.add(item_id)
        if item.get("kind") not in VALID_KINDS:
            errors.append(f"{label}: kind must be anime or donghua")
        if item.get("subtitleStatus") not in VALID_SUBTITLE_STATES:
            errors.append(f"{label}: invalid or missing subtitleStatus")
        if not isinstance(item.get("subtitleLanguages"), list):
            errors.append(f"{label}: subtitleLanguages must be an array")
        if item.get("subtitleStatus") == "verified":
            declared = any(str(lang).lower().startswith("en") for lang in item.get("subtitleLanguages", []))
            evidence_ok = is_https_url(item.get("subtitleEvidence", "")) and bool(item.get("subtitleCheckedAt"))
            if not declared or not evidence_ok:
                errors.append(f"{label}: verified English subtitles require English language metadata, an HTTPS evidence URL and subtitleCheckedAt")
        episodes = item.get("episodes", [])
        for ep_index, ep in enumerate(episodes if isinstance(episodes, list) else []):
            if isinstance(ep, dict) and ep.get("subtitleStatus") == "verified" and not has_english_track(ep.get("subtitles", [])):
                errors.append(f"{label} episode {ep_index + 1}: verified subtitles require a real English HTTPS subtitle track")
        for field in ("sourceUrl", "posterUrl"):
            value = item.get(field)
            if value and not is_https_url(value):
                errors.append(f"{label}: {field} must be an HTTPS URL")
        if not isinstance(item.get("episodes", []), list):
            errors.append(f"{label}: episodes must be an array")
            continue
        for ep_index, ep in enumerate(item.get("episodes", [])):
            ep_label = f"{label} episode {ep_index + 1}"
            if not isinstance(ep, dict):
                errors.append(f"{ep_label}: episode must be an object")
                continue
            if ep.get("subtitleStatus") not in VALID_SUBTITLE_STATES:
                errors.append(f"{ep_label}: invalid or missing subtitleStatus")
            if not isinstance(ep.get("subtitles", []), list):
                errors.append(f"{ep_label}: subtitles must be an array")
            for track in ep.get("subtitles", []):
                if not isinstance(track, dict) or not is_https_url(track.get("url", "")):
                    errors.append(f"{ep_label}: subtitle track needs a valid HTTPS URL")
            for field in ("sourceUrl", "videoUrl", "watchUrl"):
                value = ep.get(field)
                if value and not is_https_url(value):
                    errors.append(f"{ep_label}: {field} must be an HTTPS URL")
            for download in ep.get("downloads", []):
                if not isinstance(download, dict) or not is_https_url(download.get("url", "")):
                    errors.append(f"{ep_label}: each download needs a valid HTTPS URL")
        for download in item.get("downloads", []):
            if not isinstance(download, dict) or not is_https_url(download.get("url", "")):
                errors.append(f"{label}: each download needs a valid HTTPS URL")

    if errors:
        print(f"Catalogue validation failed with {len(errors)} issue(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Catalogue validation passed: {len(titles)} unique titles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

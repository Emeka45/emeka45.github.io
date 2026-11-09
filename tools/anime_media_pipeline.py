#!/usr/bin/env python3
"""Encode only locally supplied media with explicit redistribution permission.

This tool does not download media. Place rights-cleared source files under the
configured incoming directory and describe them in a manifest before running.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

PROFILES = (360, 480, 720, 1080)
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}


def _evidence_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("rights_evidence_url must be a public HTTPS URL")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or "." not in host:
        raise ValueError("rights_evidence_url must use a public hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError("rights_evidence_url cannot point to a private or reserved IP")
    return value


def _inside(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must resolve inside the incoming directory") from exc
    if not candidate.is_file():
        raise ValueError(f"{label} file does not exist: {relative}")
    return candidate


def validate_manifest(document: dict[str, Any], incoming_dir: Path) -> list[dict[str, Any]]:
    if document.get("schema_version") != 1:
        raise ValueError("media manifest must use schema_version 1")
    assets = document.get("assets")
    if not isinstance(assets, list):
        raise ValueError("media manifest assets must be a list")
    incoming = incoming_dir.resolve()
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ValueError(f"asset {index + 1} must be an object")
        asset_id = str(asset.get("id", "")).strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", asset_id):
            raise ValueError(f"asset {index + 1} has an invalid id")
        if asset_id in seen:
            raise ValueError(f"duplicate asset id: {asset_id}")
        seen.add(asset_id)
        if asset.get("rights_status") != "redistribution_authorized":
            raise ValueError(f"asset {asset_id} requires rights_status=redistribution_authorized")
        if not str(asset.get("license", "")).strip():
            raise ValueError(f"asset {asset_id} requires a license")
        evidence = _evidence_url(str(asset.get("rights_evidence_url", "")))
        input_file = _inside(incoming, str(asset.get("input_file", "")), f"{asset_id} input")
        subtitle = None
        subtitle_language = str(asset.get("subtitle_language", "")).strip().lower()
        subtitle_name = str(asset.get("subtitle_file", "")).strip()
        if subtitle_language and not subtitle_name:
            raise ValueError(f"asset {asset_id} declares {subtitle_language} subtitles but has no subtitle_file")
        if subtitle_name:
            subtitle = _inside(incoming, subtitle_name, f"{asset_id} subtitle")
            if subtitle.suffix.lower() not in SUBTITLE_EXTENSIONS:
                raise ValueError(f"asset {asset_id} subtitle must be SRT, VTT, ASS, or SSA")
            if subtitle.resolve() == input_file.resolve():
                raise ValueError(f"asset {asset_id} subtitle must be a separate file")
        validated.append({
            "id": asset_id,
            "title": str(asset.get("title", asset_id)).strip()[:220],
            "input_file": input_file,
            "subtitle_file": subtitle,
            "subtitle_language": subtitle_language or None,
            "license": str(asset["license"]).strip()[:200],
            "rights_evidence_url": evidence,
        })
    return validated


def _encode_profile(input_file: Path, output_file: Path, height: int, ffmpeg_bin: str) -> None:
    command = [
        ffmpeg_bin, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(input_file),
        "-map", "0:v:0", "-map", "0:a?",
        "-vf", f"scale=-2:min(ih\\,{height})",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", str(output_file),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=7200, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or "ffmpeg returned a non-zero exit status")[-1200:]
        raise RuntimeError(f"ffmpeg failed for {height}p: {detail}")
    if not output_file.is_file() or output_file.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg did not create a valid {height}p output")


def process_manifest(
    manifest_path: str | Path,
    incoming_dir: str | Path,
    output_dir: str | Path,
    ffmpeg_bin: str = "ffmpeg",
) -> dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    incoming = Path(incoming_dir).resolve()
    output = Path(output_dir).resolve()
    if not incoming.is_dir():
        raise ValueError(f"incoming directory does not exist: {incoming}")
    output.mkdir(parents=True, exist_ok=True)
    assets = validate_manifest(manifest, incoming)
    results: list[dict[str, Any]] = []
    for asset in assets:
        destination = output / asset["id"]
        if destination.exists():
            raise FileExistsError(f"output already exists for {asset['id']}; move it aside before rebuilding")
        temporary = Path(tempfile.mkdtemp(prefix=f".{asset['id']}-", dir=output))
        try:
            for height in PROFILES:
                _encode_profile(asset["input_file"], temporary / f"{height}p.mp4", height, ffmpeg_bin)
            subtitle_name = None
            if asset["subtitle_file"]:
                subtitle_name = "english" + asset["subtitle_file"].suffix.lower() if asset["subtitle_language"] == "english" else "subtitles" + asset["subtitle_file"].suffix.lower()
                shutil.copy2(asset["subtitle_file"], temporary / subtitle_name)
            temporary.rename(destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        results.append({
            "id": asset["id"],
            "title": asset["title"],
            "profiles": list(PROFILES),
            "subtitle_language": asset["subtitle_language"],
            "subtitle_file": subtitle_name,
            "license": asset["license"],
            "rights_evidence_url": asset["rights_evidence_url"],
        })
    index = {"schema_version": 1, "asset_count": len(results), "assets": results}
    (output / "anime-media-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="anime-media-manifest.json")
    parser.add_argument("--incoming", default="media/incoming")
    parser.add_argument("--output", default="media/encoded")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args(argv)
    result = process_manifest(args.manifest, args.incoming, args.output, args.ffmpeg)
    print(f"Encoded {result['asset_count']} authorised assets into 360p/480p/720p/1080p profiles.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

# Anime media processing (rights-cleared files only)

The release monitor and this media pipeline are separate stages. The release monitor indexes public release metadata; the media pipeline encodes only files that a maintainer has already obtained with explicit permission to redistribute.

## Safety and rights gate

Every asset must include:
- `rights_status: redistribution_authorized`
- a specific `license` description
- a public HTTPS `rights_evidence_url` that points to the licence, creator permission, or other evidence
- a local source file placed under `media/incoming/`

A metadata-only listing, a streaming subscription, or a link to an episode page is **not** redistribution permission. The tool does not download from websites, bypass DRM, scrape streaming services, or fetch media enclosures. A maintainer must verify the rights evidence; the URL is a record, not an automated legal determination.

## Local setup

Install Python 3.10+ and FFmpeg on a machine you control. Keep source media outside Git where possible.

1. Put an authorised source file in `media/incoming/`.
2. If an English subtitle file is supplied, put the SRT/VTT/ASS/SSA file in the same directory.
3. Add an asset entry to `anime-media-manifest.json`, using paths relative to `media/incoming/`.
4. Run:

```sh
python -m unittest discover -s tests -v
python tools/anime_media_pipeline.py
```

The pipeline creates 360p, 480p, 720p, and 1080p MP4 outputs. Each profile is capped at its target height (it will not upscale smaller input); it uses H.264 video, AAC audio, and fast-start MP4 metadata. A supplied subtitle file is copied as a separate sidecar rather than burned into the video.

## Output and storage

Outputs are written to `media/encoded/<asset-id>/`, with `anime-media-index.json` in the encoded directory. Existing asset output directories are never overwritten; move or archive one before reprocessing. Failed encodes remove the temporary output directory so incomplete files are not published.

Do not commit large video files to GitHub Pages. The next deployment step is to connect a user-controlled object store (Cloudflare R2 is the intended option) and publish only rights-cleared files. No R2 bucket, API token, secret, or upload has been created by this change.

## Current status

The manifest is intentionally empty. No licensed source file or subtitle has been supplied or configured, so this implementation creates no anime downloads by itself. The release radar remains metadata-only until verified official feeds are configured.

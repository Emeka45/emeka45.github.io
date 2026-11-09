# Anime release monitor

This is the first backend stage for the Emeka45 Anime & Donghua Hub. It monitors configured RSS/Atom feeds and builds anime-release-index.json for the site to consume.

## Current behaviour

- Reads anime-release-sources.json.
- Supports RSS 2.0 and Atom feeds.
- Records episode identifiers, publication dates, source-page URLs, explicitly listed resolutions, and explicitly labelled English-subtitle hints.
- Generates stable release IDs so repeated feed runs do not duplicate the same release.
- Rejects non-HTTPS feed URLs and invalid source configuration.
- Keeps rights status explicit. A source marked redistribution_authorized must include a licence and a public rights-evidence URL.
- Never downloads videos, subtitle payloads, or media enclosures. It indexes metadata only.
- Fails the run rather than publishing a partial index if a configured feed cannot be read.

## Add a feed

Add a source object to anime-release-sources.json with an id, name, public HTTPS feed_url, and rights_status set to metadata_only. Only add official distributor, creator, or other approved feeds. A metadata feed does not grant permission to copy or host the media it describes.

For a source where redistribution rights have been verified, also provide a licence and a public rights_evidence_url. A maintainer must check that evidence. The monitor still does not download media; this status is a prerequisite for a later, separately implemented acquisition step.

## Run locally

Run python -m unittest discover -s tests -v, then python tools/anime_release_monitor.py.

## Automation

GitHub Actions runs the tests and refreshes the index every 12 hours, and can also be run manually from the Actions tab. It commits only when the generated index changes.

## Current source status

No feed has been configured yet. The workflow and parser are ready, but automatic discovery will begin only after approved feed URLs are added to anime-release-sources.json.

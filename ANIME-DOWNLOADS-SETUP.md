# Anime & Donghua download manifest

The Anime & Donghua page reads `anime-downloads.json` from the same website. Use this file to add direct episode streams and downloads **only when you own the media or have permission to distribute it**. The live catalogue supplies titles and metadata; it does not grant download rights.

## Shape

```json
{
  "version": 1,
  "titles": [
    {
      "anilistId": 12345,
      "title": "Exact catalogue title",
      "episodes": [
        {
          "number": 1,
          "title": "Episode 1",
          "streams": [
            { "label": "Watch 720p", "url": "https://your-authorized-host.example/episode-1-720.mp4" }
          ],
          "downloads": [
            { "label": "Download 720p MP4", "url": "https://your-authorized-host.example/episode-1-720.mp4" }
          ]
        }
      ]
    }
  ]
}
```

- Match a catalogue title by its AniList numeric ID (`anilistId`) or its exact title (`title`).
- Use a valid HTTPS URL to a media file or stream you are authorized to host/distribute.
- Direct downloadable files work best as MP4 or WebM. HLS (`.m3u8`) may stream in supported browsers but is not a single-file download.
- Cross-origin hosts may ignore the browser's `download` attribute or block playback with CORS. Hosting authorized files on your own origin or Cloudflare R2/custom domain is more reliable.
- Do not put passwords, API tokens, or other secrets in this public JSON file.
- An empty manifest is valid; the catalogue still loads. Until authorized media URLs are added, this file cannot make every episode downloadable by itself.

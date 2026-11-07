# Anime & Donghua download library

The Anime & Donghua page reads `anime-downloads.json` from this website repository. The page no longer depends on a third-party anime catalogue API. Add titles here only when the video is openly licensed for redistribution or you have explicit permission from the rights holder.

## Entry format

Each title should include a stable local `id`, a `kind` (`anime` or `donghua`), a `title`, an optional `description`, licence/source details, and a `downloads` array:

```json
{
  "id": "example-title",
  "kind": "anime",
  "title": "Example title",
  "description": "Short description",
  "license": "Licence and attribution details",
  "sourceUrl": "https://official-source.example/license",
  "episodes": [
    {
      "title": "Episode 1",
      "description": "Episode details",
      "videoUrl": "https://www.dailymotion.com/video/VIDEO_ID",
      "downloads": [
        {
          "label": "Download 360p MP4",
          "url": "https://authorized-host.example/episode-1-360p.mp4"
        }
      ]
    }
  ],
  "downloads": [
    {
      "label": "Download 360p WebM",
      "url": "https://authorized-host.example/video-360p.webm"
    }
  ]
}
```

## Dailymotion playback

- Add a Dailymotion episode URL to an episode's `videoUrl`, `watchUrl`, or `sourceUrl` field. The Anime & Donghua page opens it in the embedded Dailymotion player.
- The **Search Dailymotion** button opens Dailymotion search using the current catalogue search term (or a default Anime/Donghua search).
- Dailymotion playback and direct file downloads are separate controls. A Dailymotion page URL is not itself a downloadable MP4/WebM file; add a separate direct file URL in `downloads` when one is available.

## Rules

- Only include direct media links when you own the file, the licence allows redistribution, or the rights holder has authorized downloads.
- Prefer HTTPS and direct MP4/WebM files. HLS playlists can stream in some browsers but are not single-file downloads.
- The website presents download buttons, but most files currently remain hosted by their original sources. The HTML `download` attribute cannot force every cross-origin host or mobile browser to save a file.
- Do not copy or rehost commercial anime or donghua without permission. A catalogue entry or a source-page link does not grant download rights.
- Include accurate licence and attribution details; verify the source page before publishing a new title.
- `kind: "donghua"` entries appear under the Donghua tab. If there are no authorized entries, the page explains that no verified direct downloads are listed yet.


## Player and browsing features

The Anime & Donghua page supports:
- Separate Anime and Donghua catalogues.
- Search, status filters (watch online, downloads, official sources), and sorting.
- YouTube and Dailymotion episode embeds.
- Direct MP4/WebM episode preview in the built-in player, with optional subtitle tracks.
- Separate direct-file download links. A preview is not presented as a download, and a provider page is not presented as a direct file.

### Episode fields

```json
{
  "title": "Episode 1",
  "description": "Episode synopsis",
  "videoUrl": "https://www.youtube.com/watch?v=VIDEO_ID",
  "sourceUrl": "https://official-creator.example/series/",
  "subtitles": [
    { "label": "English", "lang": "en", "url": "https://example.org/subtitles/episode-1.vtt", "default": true }
  ],
  "downloads": [
    { "label": "240p WebM · low data", "url": "https://files.example.org/episode-1-240p.webm" },
    { "label": "480p MP4", "url": "https://files.example.org/episode-1-480p.mp4" }
  ]
}
```

For direct MP4/WebM URLs, the built-in player offers a preview button beside the download link. YouTube and Dailymotion URLs are embedded from their respective providers. Subtitle URLs must point to valid WebVTT files. Always verify each episode's license, music rights, attribution and source before publishing.

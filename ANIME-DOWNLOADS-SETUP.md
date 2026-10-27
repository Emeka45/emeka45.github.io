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
  "downloads": [
    {
      "label": "Download 360p WebM",
      "url": "https://authorized-host.example/video-360p.webm"
    }
  ]
}
```

## Rules

- Only include direct media links when you own the file, the licence allows redistribution, or the rights holder has authorized downloads.
- Prefer HTTPS and direct MP4/WebM files. HLS playlists can stream in some browsers but are not single-file downloads.
- The website presents download buttons, but most files currently remain hosted by their original sources. The HTML `download` attribute cannot force every cross-origin host or mobile browser to save a file.
- Do not copy or rehost commercial anime or donghua without permission. A catalogue entry or a source-page link does not grant download rights.
- Include accurate licence and attribution details; verify the source page before publishing a new title.
- `kind: "donghua"` entries appear under the Donghua tab. If there are no authorized entries, the page explains that no verified direct downloads are listed yet.

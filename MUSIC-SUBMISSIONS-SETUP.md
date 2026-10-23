# Music submissions — Cloudflare Pages + D1

## One-time Cloudflare setup
1. In Cloudflare dashboard, open Workers & Pages and select the Pages project serving emeka45.github.io.
2. Open Settings → Bindings and add a D1 database binding named exactly MUSIC_SUBMISSIONS. Create a database if needed.
3. In that D1 database Console, run the SQL in migrations/0001_music_submissions.sql.
4. Redeploy the Pages project so the Pages Function receives the binding.
5. Test music-submit.html. If storage is not configured, the endpoint will report that clearly and the form should offer a download/copy fallback.

## Review submissions
Run in the D1 Console:
```sql
SELECT id, created_at, submission_type, artist, contact_email, genre, release_title, official_audio_url, status FROM music_submissions ORDER BY created_at DESC LIMIT 100;
```
Mark reviewed:
```sql
UPDATE music_submissions SET status = 'reviewed' WHERE id = 'PASTE-SUBMISSION-ID';
```

## Safety and limits
The endpoint accepts submissions only; there is no public listing/read endpoint. Entries are not published automatically. D1 stores contact details and submitted links, so restrict dashboard access and adopt a retention policy. Basic validation and a honeypot are included; consider Cloudflare Turnstile and/or rate limiting before broad public promotion.

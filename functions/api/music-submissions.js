export async function onRequestPost({ request, env }) {
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
  if (!env.MUSIC_SUBMISSIONS) return json({ ok: false, code: "storage_not_configured", message: "Submission storage is not configured yet. Please download the submission file instead." }, 503);
  if (!(request.headers.get("content-type") || "").includes("application/json")) return json({ ok: false, message: "Expected JSON request." }, 415);
  let data;
  try { const raw = await request.text(); if (raw.length > 20000) return json({ ok: false, message: "Submission is too large." }, 413); data = JSON.parse(raw); }
  catch { return json({ ok: false, message: "Invalid submission data." }, 400); }
  if (typeof data.website === "string" && data.website.trim()) return json({ ok: true, received: true });
  const str = (key, max, required = false) => { const value = typeof data[key] === "string" ? data[key].trim() : ""; if (required && !value) throw new Error(key + " is required."); if (value.length > max) throw new Error(key + " is too long."); return value; };
  const validUrl = (value, key, required = false) => { if (!value) { if (required) throw new Error(key + " is required."); return ""; } let url; try { url = new URL(value); } catch { throw new Error(key + " must be a valid URL."); } if (!["https:", "http:"].includes(url.protocol)) throw new Error(key + " must use http or https."); return url.href; };
  let item;
  try {
    item = { submissionType: str("requestType", 60, true), artist: str("artist", 120, true), contactEmail: str("contactEmail", 200), location: str("location", 120), genre: str("genre", 100, true), releaseTitle: str("releaseTitle", 180, true), releaseType: str("releaseType", 60), releaseDate: str("releaseDate", 20), artworkUrl: validUrl(str("artworkUrl", 2000), "Artwork URL"), officialAudioUrl: validUrl(str("officialAudioUrl", 2000), "Official audio URL", true), officialVideoUrl: validUrl(str("officialVideoUrl", 2000), "Official video URL"), streamingUrl: validUrl(str("streamingUrl", 2000), "Streaming URL"), artistPageUrl: validUrl(str("artistPageUrl", 2000), "Artist page URL"), bio: str("bio", 1800), notes: str("notes", 1000), rightsConfirmed: data.rightsConfirmed === true, reviewRequested: data.reviewRequested === true };
    if (!item.rightsConfirmed) throw new Error("Rights confirmation is required.");
    if (item.contactEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(item.contactEmail)) throw new Error("Contact email is invalid.");
    if (item.releaseDate && !/^\d{4}-\d{2}-\d{2}$/.test(item.releaseDate)) throw new Error("Release date must use YYYY-MM-DD.");
  } catch (error) { return json({ ok: false, message: error.message || "Invalid submission." }, 400); }
  const id = crypto.randomUUID(), createdAt = new Date().toISOString();
  try {
    await env.MUSIC_SUBMISSIONS.prepare("INSERT INTO music_submissions (id, created_at, submission_type, artist, contact_email, location, genre, release_title, release_type, release_date, artwork_url, official_audio_url, official_video_url, streaming_url, artist_page_url, bio, notes, rights_confirmed, review_requested, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')").bind(id, createdAt, item.submissionType, item.artist, item.contactEmail, item.location, item.genre, item.releaseTitle, item.releaseType, item.releaseDate, item.artworkUrl, item.officialAudioUrl, item.officialVideoUrl, item.streamingUrl, item.artistPageUrl, item.bio, item.notes, item.rightsConfirmed ? 1 : 0, item.reviewRequested ? 1 : 0).run();
    return json({ ok: true, id, message: "Your submission has been received for review. It is not published automatically." }, 201);
  } catch { return json({ ok: false, code: "save_failed", message: "We could not save the submission. Please download a copy and try again later." }, 500); }
}
export async function onRequestGet() { return new Response(JSON.stringify({ ok: false, message: "Use the submission form to send a POST request." }), { status: 405, headers: { "Content-Type": "application/json; charset=utf-8", "Allow": "POST", "Cache-Control": "no-store" } }); }

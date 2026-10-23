const ALLOWED_ORIGINS = new Set([
  'https://emeka45.github.io',
  'https://www.emeka45.github.io'
]);

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'access-control-allow-origin': 'https://emeka45.github.io',
      'access-control-allow-methods': 'POST, OPTIONS',
      'access-control-allow-headers': 'content-type'
    }
  });
}

export async function onRequestOptions() {
  return json({ ok: true });
}

export async function onRequestPost(context) {
  const origin = context.request.headers.get('Origin');
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return json({ error: 'Origin not allowed.' }, 403);
  }

  const apiKey = context.env.GEMINI_API_KEY;
  if (!apiKey) {
    return json({ error: 'Music generation is not configured yet. Add GEMINI_API_KEY to the Cloudflare Pages secret bindings.' }, 503);
  }

  let body;
  try {
    body = await context.request.json();
  } catch {
    return json({ error: 'Invalid JSON request.' }, 400);
  }

  const title = String(body.title || 'Untitled').trim().slice(0, 80);
  const genre = String(body.genre || 'Pop').trim().slice(0, 80);
  const mood = String(body.mood || 'Warm and emotional').trim().slice(0, 100);
  const voice = String(body.voice || 'Vocals').trim().slice(0, 40);
  const duration = String(body.duration || 'about 2 minutes').trim().slice(0, 60);
  const lyrics = String(body.lyrics || '').trim().slice(0, 6000);
  const idea = String(body.idea || '').trim().slice(0, 1200);

  if (!idea && !lyrics) {
    return json({ error: 'Tell the studio what the song should be about, or provide lyrics.' }, 400);
  }

  const prompt = `Create an original song titled "${title}". Genre/style: ${genre}. Mood: ${mood}. ${voice}. Target length: ${duration}. Theme/idea: ${idea || 'Use the supplied lyrics as the complete lyrical direction.'}

${lyrics ? `Use these user-supplied lyrics and preserve their wording as much as practical:\n${lyrics}` : 'Write original lyrics that fit the theme and song structure.'}

Make the arrangement feel polished and musical, with a clear intro, verses, chorus, and bridge/outro where appropriate. Do not imitate or name a living artist. Do not quote or reproduce copyrighted lyrics.`;

  const upstream = await fetch('https://generativelanguage.googleapis.com/v1beta/interactions', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-goog-api-key': apiKey
    },
    body: JSON.stringify({
      model: 'lyria-3.5',
      input: prompt,
      response_format: { type: 'audio' }
    })
  });

  const data = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    return json({
      error: data?.error?.message || 'Gemini music generation failed.',
      providerStatus: upstream.status
    }, upstream.status >= 400 && upstream.status < 500 ? upstream.status : 502);
  }

  let audio = data?.output_audio?.data || null;
  let text = data?.output_text || '';

  if ((!audio || !text) && Array.isArray(data?.steps)) {
    for (const step of data.steps) {
      if (step?.type !== 'model_output' || !Array.isArray(step.content)) continue;
      for (const block of step.content) {
        if (block?.type === 'audio' && block.data) audio = block.data;
        if (block?.type === 'text' && block.text) text += (text ? '\n' : '') + block.text;
      }
    }
  }

  if (!audio) {
    return json({ error: 'Gemini returned no audio data.' }, 502);
  }

  return json({
    ok: true,
    title,
    artist: 'C. O. Eric AI Music Studio',
    lyrics: text,
    mimeType: 'audio/mpeg',
    audioBase64: audio
  });
}

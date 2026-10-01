const SOURCE = "https://raw.githubusercontent.com/mhollingshead/open-dictionary/main/api";
const CACHE_TTL = 86400;

function normalize(value) {
  return String(value || "").trim().toLowerCase().replace(/\\s+/g, " ");
}

function shardFor(word) {
  const first = word[0];
  if (!first || !/[a-z]/.test(first)) return null;
  const pair = word.length > 1 ? word.slice(0, 2) : first;
  return { first, pair };
}

async function loadShard(word, cache) {
  const shard = shardFor(word);
  if (!shard) return null;
  const url = `${SOURCE}/${shard.first}/${shard.pair}.json`;
  const key = new Request(url);
  const cached = await cache.match(key);
  if (cached) return cached.json();
  const response = await fetch(url, { cf: { cacheTtl: CACHE_TTL, cacheEverything: true } });
  if (!response.ok) return null;
  const data = await response.json();
  await cache.put(key, new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${CACHE_TTL}` }
  }));
  return data;
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "public, max-age=300"
  };
}

function response(data, status=200) {
  return Response.json(data, { status, headers: corsHeaders() });
}

function entryFromShard(shard, word) {
  const entry = shard?.[word];
  if (!entry) return null;
  return entry;
}

export async function onRequest(context) {
  if (context.request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders() });
  if (context.request.method !== "GET") return response({ error: "Method not allowed." }, 405);

  const url = new URL(context.request.url);
  const word = normalize(url.searchParams.get("word"));
  const prefix = normalize(url.searchParams.get("suggest"));
  const limit = Math.min(Math.max(Number(url.searchParams.get("limit") || 8), 1), 20);

  if (!word && !prefix) return response({
    service: "Universal Dictionary",
    endpoint: "/api/dictionary",
    usage: "?word=example or ?suggest=exam&limit=8",
    source: "Open Dictionary (Wiktionary-derived)"
  });

  const query = word || prefix;
  if (!query || !/^[a-z][a-z' -]*$/.test(query)) return response({ error: "Use an English word or prefix." }, 400);

  const shard = await loadShard(query.replace(/[^a-z].*$/, ""), caches.default);
  if (!shard) return response({ error: "Dictionary shard unavailable." }, 502);

  if (word) {
    const entry = entryFromShard(shard, word);
    if (!entry) return response({ error: `No entry found for "${word}".` }, 404);
    return response({
      word: entry.word || word,
      etymologies: entry.etymologies || [],
      source: "Open Dictionary (Wiktionary-derived)",
      service: "Universal Dictionary"
    });
  }

  const words = Object.keys(shard).filter(key => key.startsWith(prefix)).sort().slice(0, limit);
  return response({ query: prefix, suggestions: words, source: "Open Dictionary (Wiktionary-derived)" });
}

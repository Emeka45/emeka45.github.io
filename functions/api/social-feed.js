const TOPICS = [
  { category: "technology", query: "technology OR artificial intelligence OR apps" },
  { category: "entertainment", query: "anime OR donghua OR animation OR entertainment" },
  { category: "sports", query: "football OR sports" },
  { category: "science", query: "science discovery OR research OR space" },
  { category: "gospel", query: "gospel music OR Christianity" },
  { category: "Nigeria", query: "Nigeria news" },
  { category: "viral", query: "viral internet trends OR social media trends" }
];
function xmlField(block, tag) {
  const match = block.match(new RegExp("<" + tag + "(?:\\s[^>]*)?>([\\s\\S]*?)</" + tag + ">", "i"));
  return match ? match[1].replace(/^<!\[CDATA\[([\s\S]*)\]\]>$/, "$1").trim() : "";
}
function cleanText(s) {
  return String(s || "").replace(/<[^>]*>/g, " ").replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">").replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&apos;/g, "'").replace(/\s+/g, " ").trim().slice(0, 500);
}
export async function onRequestGet({ request }) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "public, max-age=600, s-maxage=600",
    "X-Content-Type-Options": "nosniff"
  };
  try {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    if (origin && new URL(origin).host !== url.host) {
      return new Response(JSON.stringify({ error: "Origin not allowed", items: [] }), { status: 403, headers });
    }
    const results = await Promise.all(TOPICS.map(async topic => {
      const feedURL = "https://news.google.com/rss/search?q=" +
        encodeURIComponent(topic.query) + "&hl=en-NG&gl=NG&ceid=NG:en";
      try {
        const response = await fetch(feedURL, { headers: { "User-Agent": "COEricSocialHub/1.0 (+https://emeka45.github.io)" } });
        if (!response.ok) return [];
        const xml = await response.text();
        return Array.from(xml.matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)).slice(0, 8).map(match => {
          const item = match[1];
          const title = cleanText(xmlField(item, "title"));
          const link = cleanText(xmlField(item, "link"));
          const description = cleanText(xmlField(item, "description"));
          const source = cleanText(xmlField(item, "source") || "Google News");
          if (!title || !/^https:\/\//i.test(link)) return null;
          return { title, summary: description || "Open the original public report for details.", category: topic.category, source, url: link };
        }).filter(Boolean);
      } catch { return []; }
    }));
    const items = results.flat().filter((item, i, all) => all.findIndex(other => other.url === item.url) === i).slice(0, 56);
    return new Response(JSON.stringify({ updatedAt: new Date().toISOString(), items }), { headers });
  } catch {
    return new Response(JSON.stringify({ error: "Public discovery feed temporarily unavailable", items: [] }), { status: 503, headers });
  }
}

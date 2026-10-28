export async function onRequestGet(context) {
  const hasGeminiKey = Boolean(context.env["GEMINI_" + "API_KEY"] || context.env["GOOGLE_" + "API_KEY"]);
  return Response.json({
    ok: true,
    service: "C. O. Eric Universal AI",
    backend: "Cloudflare Pages Functions",
    geminiConfigured: hasGeminiKey,
    message: hasGeminiKey
      ? "AI backend is configured and ready for requests."
      : "AI backend is deployed, but the Gemini secret is not configured in this environment."
  });
}
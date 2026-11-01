const SYSTEM_TEXT = "You are the C. O. Eric Universal AI assistant. Be helpful, accurate, concise and friendly. Use the available tools when they materially improve the answer. When web search is used, prefer current, verifiable information and distinguish sourced facts from your own explanation. Do not claim to be a human. Never reveal private keys, credentials or hidden implementation details.";

function cleanMessages(messages) {
  return (Array.isArray(messages) ? messages : [])
    .slice(-12)
    .filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.text === "string")
    .map(m => ({ role: m.role, text: m.text.slice(0, 6000) }));
}

function getGeminiTools(body) {
  const requested = Array.isArray(body?.plugins) ? body.plugins : ["web-search", "code-execution"];
  const selected = new Set(requested.map(String));
  const tools = [];
  const enabled = [];
  if (selected.has("web-search")) {
    tools.push({ googleSearch: {} });
    enabled.push("web-search");
  }
  if (selected.has("code-execution")) {
    tools.push({ codeExecution: {} });
    enabled.push("code-execution");
  }
  return { tools, enabled };
}

async function callGemini({ key, model, payload }) {
  return fetch("https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify(payload)
  });
}

export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    if (!body || typeof body !== "object") return Response.json({ error: "Invalid request." }, { status: 400 });

    const provider = ["coeric", "gemini", "openai", "anthropic", "deepseek"].includes(body.provider) ? body.provider : "coeric";
    const messages = cleanMessages(body.messages);
    if (!messages.length) return Response.json({ error: "Please enter a message." }, { status: 400 });

    if (provider === "openai" || provider === "anthropic" || provider === "deepseek") {
      return Response.json({ error: "This provider is currently locked because it uses a paid API. Use C. O. Eric Universal AI or Gemini for free mode." }, { status: 402 });
    }

    const key = context.env["GEMINI_" + "API_KEY"] || context.env["GOOGLE_" + "API_KEY"];
    if (!key) return Response.json({ error: "Gemini AI is not configured on the live Cloudflare backend. Add the encrypted GEMINI_API_KEY secret to the Production environment, then redeploy the Pages project." }, { status: 503 });

    let modelNames = [];
    try {
      const listResponse = await fetch("https://generativelanguage.googleapis.com/v1beta/models", { headers: { "x-goog-api-key": key } });
      const listData = await listResponse.json();
      if (listResponse.ok && Array.isArray(listData.models)) {
        modelNames = listData.models
          .filter(m => Array.isArray(m.supportedGenerationMethods) && m.supportedGenerationMethods.includes("generateContent"))
          .map(m => String(m.name || "").replace("models/", ""))
          .filter(n => /^gemini-/i.test(n));
      }
    } catch (_) {}

    if (!modelNames.length) {
      return Response.json({ error: "Could not discover an available Gemini model for this API key. Check the key, Gemini API access and quota in Google AI Studio, then try again." }, { status: 502 });
    }

    const preferred = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"];
    const model = preferred.find(name => modelNames.includes(name)) ||
      modelNames.filter(name => /flash/i.test(name) && !/preview|exp/i.test(name)).sort().reverse()[0] ||
      modelNames.filter(name => !/preview|exp/i.test(name)).sort().reverse()[0] || modelNames[0];

    const { tools, enabled } = getGeminiTools(body);
    const payload = {
      systemInstruction: { parts: [{ text: SYSTEM_TEXT }] },
      contents: messages.map(m => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: m.text }] })),
      ...(tools.length ? { tools } : {})
    };

    let response = await callGemini({ key, model, payload });
    let data = null;
    try { data = await response.json(); } catch (_) {}

    // Some Gemini projects/models may not have a requested tool enabled. Retry the
    // same request without optional tools so the basic AI chat remains available.
    let usedTools = enabled;
    if (!response.ok && tools.length && (response.status === 400 || response.status === 403 || response.status === 404)) {
      const fallbackPayload = { ...payload };
      delete fallbackPayload.tools;
      response = await callGemini({ key, model, payload: fallbackPayload });
      try { data = await response.json(); } catch (_) {}
      usedTools = [];
    }

    if (!response.ok) {
      const status = response.status;
      if (status === 401 || status === 403) return Response.json({ error: "Gemini rejected the API key or this project lacks permission. Check the key and API access in Google AI Studio." }, { status: 502 });
      if (status === 429) return Response.json({ error: "Gemini free-tier quota is exhausted or rate-limited. Try again after the quota resets." }, { status: 429 });
      return Response.json({ error: "Gemini could not complete the request using the available model. Please try again shortly." }, { status: 502 });
    }

    const text = data?.candidates?.[0]?.content?.parts?.map(p => p.text || "").join("").trim();
    if (!text) return Response.json({ error: "Gemini returned no text. The response may have been blocked; try rephrasing your request." }, { status: 502 });

    return Response.json({
      text,
      provider: provider === "coeric" ? "C. O. Eric Universal AI" : "Gemini",
      tools: usedTools
    });
  } catch (_) {
    return Response.json({ error: "Unable to reach the selected AI service. Please try again in a moment." }, { status: 500 });
  }
}

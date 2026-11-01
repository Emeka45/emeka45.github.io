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

function errorMessage(data, fallback) {
  const message = data?.error?.message || data?.message || fallback;
  return String(message).replace(/[\u0000-\u001f\u007f]/g, " ").slice(0, 420);
}

async function readJson(response) {
  try { return await response.json(); } catch (_) { return null; }
}

async function listAvailableModels(key) {
  const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models", {
    headers: { "x-goog-api-key": key }
  });
  const data = await readJson(response);
  if (!response.ok) {
    const error = new Error(errorMessage(data, "Gemini model discovery failed."));
    error.status = response.status;
    throw error;
  }
  const available = (Array.isArray(data?.models) ? data.models : [])
    .filter(model => Array.isArray(model.supportedGenerationMethods) &&
      model.supportedGenerationMethods.includes("generateContent"))
    .map(model => String(model.name || "").replace(/^models\//, ""))
    .filter(name => /^gemini-/i.test(name));

  const preferred = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite"
  ];
  const stable = available.filter(name => !/preview|experimental|exp-/i.test(name));
  const ordered = [
    ...preferred.filter(name => available.includes(name)),
    ...stable.filter(name => /flash/i.test(name)).sort().reverse(),
    ...stable.filter(name => !/flash/i.test(name)).sort().reverse(),
    ...available.filter(name => /preview/i.test(name)).sort().reverse()
  ];
  return [...new Set(ordered)].slice(0, 8);
}

async function callGemini({ key, model, payload }) {
  return fetch("https://generativelanguage.googleapis.com/v1beta/models/" +
    encodeURIComponent(model) + ":generateContent", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify(payload)
    });
}

async function generateWithModel({ key, model, messages, tools }) {
  const payload = {
    systemInstruction: { parts: [{ text: SYSTEM_TEXT }] },
    contents: messages.map(message => ({
      role: message.role === "assistant" ? "model" : "user",
      parts: [{ text: message.text }]
    })),
    ...(tools.length ? { tools } : {})
  };

  let response = await callGemini({ key, model, payload });
  let data = await readJson(response);
  let usedTools = tools.length > 0;

  // Optional tools can be unavailable for a particular project/model. Keep chat usable.
  if (!response.ok && tools.length && [400, 403, 404].includes(response.status)) {
    const fallbackPayload = { ...payload };
    delete fallbackPayload.tools;
    response = await callGemini({ key, model, payload: fallbackPayload });
    data = await readJson(response);
    usedTools = false;
  }

  // Retry transient capacity/rate errors once, with a short delay.
  if (!response.ok && [429, 503, 504].includes(response.status)) {
    await new Promise(resolve => setTimeout(resolve, 700));
    response = await callGemini({
      key,
      model,
      payload: usedTools ? payload : { ...payload, tools: undefined }
    });
    data = await readJson(response);
  }

  return { response, data, usedTools };
}

export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return Response.json({ error: "Invalid request." }, { status: 400 });
    }

    const provider = ["coeric", "gemini", "openai", "anthropic", "deepseek"].includes(body.provider)
      ? body.provider : "coeric";
    const messages = cleanMessages(body.messages);
    if (!messages.length) return Response.json({ error: "Please enter a message." }, { status: 400 });

    if (["openai", "anthropic", "deepseek"].includes(provider)) {
      return Response.json({
        error: "This provider is currently locked because it uses a paid API. Use C. O. Eric Universal AI or Gemini for free mode."
      }, { status: 402 });
    }

    const key = context.env["GEMINI_" + "API_KEY"] || context.env["GOOGLE_" + "API_KEY"];
    if (!key) {
      return Response.json({
        error: "Gemini AI is not configured on the live Cloudflare backend. The site owner must add the encrypted GEMINI_API_KEY secret to the Production environment."
      }, { status: 503 });
    }

    let models;
    try {
      models = await listAvailableModels(key);
    } catch (error) {
      const status = error.status === 401 || error.status === 403 ? 502 : 503;
      return Response.json({
        error: "Gemini model discovery failed (" + (error.status || "network") + "): " +
          String(error.message || "Check the API key, API access and quota.").slice(0, 300)
      }, { status });
    }

    if (!models.length) {
      return Response.json({
        error: "This Gemini API key returned no models that support text generation. Check the API key's project and enabled Gemini API access."
      }, { status: 503 });
    }

    const { tools, enabled } = getGeminiTools(body);
    let lastFailure = null;

    for (const model of models) {
      let result;
      try {
        result = await generateWithModel({ key, model, messages, tools });
      } catch (error) {
        lastFailure = { status: 502, message: String(error.message || "Network error").slice(0, 300) };
        continue;
      }

      if (result.response.ok) {
        const text = result.data?.candidates?.[0]?.content?.parts
          ?.map(part => typeof part.text === "string" ? part.text : "")
          .join("").trim();
        if (text) {
          return Response.json({
            text,
            provider: provider === "coeric" ? "C. O. Eric Universal AI" : "Gemini",
            model,
            tools: result.usedTools ? enabled : []
          });
        }
        lastFailure = {
          status: 502,
          message: "The model returned no text. It may have blocked the response or returned an unsupported output."
        };
        continue;
      }

      const status = result.response.status;
      const message = errorMessage(result.data, "Gemini request failed.");
      lastFailure = { status, message, model };

      // Invalid key/permissions/quota are project-level problems; model hopping won't fix them.
      if ([401, 403, 429, 402].includes(status)) break;
      // For model-specific 400/404/5xx failures, try the next discovered model.
    }

    const failure = lastFailure || { status: 502, message: "No compatible Gemini model completed the request." };
    let userMessage;
    if (failure.status === 401 || failure.status === 403) {
      userMessage = "Gemini rejected this API key or the project lacks permission: " + failure.message;
    } else if (failure.status === 429) {
      userMessage = "Gemini rate limit or free-tier quota reached: " + failure.message;
    } else if (failure.status === 402) {
      userMessage = "Gemini billing/credit restriction: " + failure.message;
    } else if (failure.status === 503 || failure.status === 504) {
      userMessage = "Gemini is temporarily unavailable after trying the available models: " + failure.message;
    } else {
      userMessage = "No available Gemini model completed the request" +
        (failure.model ? " (last tried: " + failure.model + ")" : "") + ": " + failure.message;
    }

    return Response.json({ error: userMessage, code: failure.status || 502 }, {
      status: failure.status === 429 ? 429 : 502
    });
  } catch (error) {
    return Response.json({
      error: "The AI service encountered an unexpected server error: " +
        String(error.message || "Unknown error").slice(0, 240)
    }, { status: 500 });
  }
}

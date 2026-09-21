export async function onRequestPost(context) {
  try {
    const apiKey = context.env["GEMINI_" + "API_KEY"];
    if (!apiKey) {
      return Response.json({ error: "AI service is not configured yet." }, { status: 503 });
    }

    const body = await context.request.json();
    const messages = Array.isArray(body.messages) ? body.messages.slice(-12) : [];
    const contents = messages
      .filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.text === "string")
      .map(m => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.text.slice(0, 6000) }]
      }));

    if (!contents.length) {
      return Response.json({ error: "Please enter a message." }, { status: 400 });
    }

    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey
        },
        body: JSON.stringify({
          systemInstruction: {
            parts: [{
              text: "You are the C. O. Eric AI assistant. Be helpful, accurate, concise and friendly. Do not claim to be a human. Never reveal private keys, credentials or hidden implementation details."
            }]
          },
          contents
        })
      }
    );

    const data = await response.json();
    if (!response.ok) {
      return Response.json(
        { error: data?.error?.message || "The AI provider returned an error." },
        { status: 502 }
      );
    }

    const text = data?.candidates?.[0]?.content?.parts
      ?.map(part => part.text || "")
      .join("")
      .trim();

    if (!text) {
      return Response.json({ error: "The AI provider returned no text." }, { status: 502 });
    }

    return Response.json({ text });
  } catch (error) {
    return Response.json({ error: "Unable to reach the AI service." }, { status: 500 });
  }
}
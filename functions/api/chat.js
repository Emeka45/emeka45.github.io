export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    const provider = ["coeric","gemini","openai","anthropic","deepseek"].includes(body.provider) ? body.provider : "coeric";
    const messages = Array.isArray(body.messages) ? body.messages.slice(-12) : [];
    const clean = messages.filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.text === "string").map(m => ({role:m.role,text:m.text.slice(0,6000)}));
    if (!clean.length) return Response.json({error:"Please enter a message."},{status:400});
    const systemText = "You are the C. O. Eric AI assistant. Be helpful, accurate, concise and friendly. Do not claim to be a human. Never reveal private keys, credentials or hidden implementation details.";

    if (provider === "coeric" || provider === "gemini") {
      const key = context.env["GEMINI_"+"API_KEY"];
      if (!key) return Response.json({error:"Gemini AI is not configured yet."},{status:503});
      const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",{method:"POST",headers:{"Content-Type":"application/json","x-goog-api-key":key},body:JSON.stringify({systemInstruction:{parts:[{text:systemText}]},contents:clean.map(m=>({role:m.role==="assistant"?"model":"user",parts:[{text:m.text}]}))})});
      const data=await response.json();
      if(!response.ok)return Response.json({error:data?.error?.message||"Gemini returned an error."},{status:502});
      const text=data?.candidates?.[0]?.content?.parts?.map(p=>p.text||"").join("").trim();
      if(!text)return Response.json({error:"Gemini returned no text."},{status:502});
      return Response.json({text,provider:provider==="coeric"?"C. O. Eric AI":"Gemini"});
    }

    if (provider === "openai") {
      const key = context.env["OPENAI_"+"API_KEY"];
      if(!key)return Response.json({error:"ChatGPT is not connected yet. Add its server-side key in Cloudflare."},{status:503});
      const response=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+key},body:JSON.stringify({model:"gpt-5.4-mini",input:[{role:"system",content:systemText},...clean.map(m=>({role:m.role,content:m.text}))]})});
      const data=await response.json();
      if(!response.ok)return Response.json({error:data?.error?.message||"OpenAI returned an error."},{status:502});
      const text=data?.output?.flatMap(i=>i.content||[]).filter(x=>x.type==="output_text").map(x=>x.text).join("").trim();
      if(!text)return Response.json({error:"ChatGPT returned no text."},{status:502});
      return Response.json({text,provider:"ChatGPT"});
    }

    if (provider === "anthropic") {
      const key = context.env["ANTHROPIC_"+"API_KEY"];
      if(!key)return Response.json({error:"Claude is not connected yet. Add its server-side key in Cloudflare."},{status:503});
      const response=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},body:JSON.stringify({model:"claude-sonnet-4-5",max_tokens:2048,system:systemText,messages:clean.map(m=>({role:m.role,content:m.text}))})});
      const data=await response.json();
      if(!response.ok)return Response.json({error:data?.error?.message||"Claude returned an error."},{status:502});
      const text=data?.content?.filter(x=>x.type==="text").map(x=>x.text).join("").trim();
      if(!text)return Response.json({error:"Claude returned no text."},{status:502});
      return Response.json({text,provider:"Claude"});
    }

    if (provider === "deepseek") {
      const key = context.env["DEEPSEEK_"+"API_KEY"];
      if(!key)return Response.json({error:"DeepSeek is not connected yet. Add its server-side key in Cloudflare."},{status:503});
      const response=await fetch("https://api.deepseek.com/chat/completions",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+key},body:JSON.stringify({model:"deepseek-flash",messages:[{role:"system",content:systemText},...clean.map(m=>({role:m.role,content:m.text}))]})});
      const data=await response.json();
      if(!response.ok)return Response.json({error:data?.error?.message||"DeepSeek returned an error."},{status:502});
      const text=data?.choices?.[0]?.message?.content?.trim();
      if(!text)return Response.json({error:"DeepSeek returned no text."},{status:502});
      return Response.json({text,provider:"DeepSeek"});
    }
  } catch (error) {
    return Response.json({error:"Unable to reach the selected AI service."},{status:500});
  }
}
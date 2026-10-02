import { createMcpHandler } from "agents/mcp/server";
import { McpServer } from "@modelcontextprotocol/server";

interface Env {
  CLOUDFLARE_API_TOKEN?: string;
  CLOUDFLARE_ACCOUNT_ID?: string;
  MCP_ACCESS_TOKEN?: string;
}

async function cloudflareGet(env: Env, path: string) {
  if (!env.CLOUDFLARE_API_TOKEN || !env.CLOUDFLARE_ACCOUNT_ID) {
    throw new Error("Cloudflare credentials are not configured.");
  }
  const response = await fetch(`https://api.cloudflare.com/client/v4${path}`, {
    headers: {
      Authorization: `Bearer ${env.CLOUDFLARE_API_TOKEN}`,
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(`Cloudflare API returned HTTP ${response.status}.`);
  return data;
}

function createServer(env: Env) {
  const server = new McpServer({
    name: "Emeka45 Cloudflare Bridge",
    version: "1.0.0",
  });

  server.registerTool("cloudflare_connection_status", {
    description: "Verify that the private Cloudflare credentials required by this bridge are configured. Never returns credential values.",
    inputSchema: {},
  }, async () => ({
    content: [{
      type: "text",
      text: JSON.stringify({
        connected: Boolean(env.CLOUDFLARE_API_TOKEN && env.CLOUDFLARE_ACCOUNT_ID),
        accountIdConfigured: Boolean(env.CLOUDFLARE_ACCOUNT_ID),
        apiTokenConfigured: Boolean(env.CLOUDFLARE_API_TOKEN),
      }, null, 2),
    }],
  }));

  server.registerTool("cloudflare_account", {
    description: "Read basic information about the configured Cloudflare account.",
    inputSchema: {},
  }, async () => {
    try {
      const data = await cloudflareGet(env, `/accounts/${env.CLOUDFLARE_ACCOUNT_ID}`);
      return { content: [{ type: "text", text: JSON.stringify(data.result, null, 2) }] };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : "Cloudflare request failed." }] };
    }
  });

  server.registerTool("cloudflare_pages_projects", {
    description: "List Cloudflare Pages projects visible to the configured API token.",
    inputSchema: {},
  }, async () => {
    try {
      const data = await cloudflareGet(env, `/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/pages/projects`);
      return { content: [{ type: "text", text: JSON.stringify(data.result ?? data, null, 2) }] };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : "Cloudflare Pages request failed." }] };
    }
  });

  return server;
}

const handler = (request: Request, env: Env, ctx: ExecutionContext) =>
  createMcpHandler(() => createServer(env), { route: "/mcp" })(request, env, ctx);

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({ ok: true, service: "Emeka45 Cloudflare Bridge", mcp: "/mcp" });
    }

    if (url.pathname !== "/mcp") return new Response("Not found", { status: 404 });

    if (env.MCP_ACCESS_TOKEN) {
      const authorization = request.headers.get("Authorization");
      if (authorization !== `Bearer ${env.MCP_ACCESS_TOKEN}`) {
        return new Response("Unauthorized", {
          status: 401,
          headers: { "WWW-Authenticate": "Bearer" },
        });
      }
    }

    return handler(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;

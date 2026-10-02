import { createMcpHandler } from "agents/mcp/server";
import { McpServer } from "@modelcontextprotocol/server";

interface Env {
  CLOUDFLARE_API_TOKEN?: string;
  CLOUDFLARE_ACCOUNT_ID?: string;
  MCP_ACCESS_TOKEN?: string;
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

    if (url.pathname !== "/mcp") {
      return new Response("Not found", { status: 404 });
    }

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

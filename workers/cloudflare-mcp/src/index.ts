import { OAuthProvider, type OAuthHelpers } from "@cloudflare/workers-oauth-provider";
import { createMcpHandler } from "agents/mcp/server";
import { McpServer } from "@modelcontextprotocol/server";

interface Env {
  OAUTH_KV: KVNamespace;
  OAUTH_PROVIDER: OAuthHelpers;
  CLOUDFLARE_API_TOKEN?: string;
  CLOUDFLARE_ACCOUNT_ID?: string;
  GITHUB_CLIENT_ID?: string;
  GITHUB_CLIENT_SECRET?: string;
  ALLOWED_GITHUB_USERNAME?: string;
}

interface GitHubUser {
  login: string;
  name?: string | null;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function page(title: string, body: string, extraHeaders?: HeadersInit): Response {
  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    :root{color-scheme:dark}
    body{margin:0;background:#0b1020;color:#eef2ff;font:16px system-ui,sans-serif;display:grid;min-height:100vh;place-items:center}
    main{width:min(92vw,560px);padding:28px;border:1px solid #26314f;border-radius:20px;background:#121a30;box-shadow:0 20px 60px #0006}
    h1{margin-top:0;font-size:24px}
    p,li{line-height:1.55;color:#cbd5e1}
    button{width:100%;padding:13px 16px;border:0;border-radius:12px;background:#fff;color:#111827;font-weight:700;font-size:16px}
    .muted{font-size:13px;color:#94a3b8}
    .scope{background:#0b1020;border-radius:12px;padding:12px}
    a{color:#93c5fd}
  </style>
</head>
<body><main>${body}</main></body></html>`;
  const headers = new Headers(extraHeaders);
  headers.set("Content-Type", "text/html; charset=utf-8");
  headers.set("Cache-Control", "no-store");
  return new Response(html, { status: 200, headers });
}

async function cloudflareGet(env: Env, path: string): Promise<unknown> {
  if (!env.CLOUDFLARE_API_TOKEN || !env.CLOUDFLARE_ACCOUNT_ID) {
    throw new Error("Cloudflare credentials are not configured.");
  }

  const response = await fetch(`https://api.cloudflare.com/client/v4${path}`, {
    headers: {
      Authorization: `Bearer ${env.CLOUDFLARE_API_TOKEN}`,
      "Content-Type": "application/json",
    },
  });

  const data = await response.json() as { result?: unknown };
  if (!response.ok) {
    throw new Error(`Cloudflare API returned HTTP ${response.status}.`);
  }
  return data.result ?? data;
}

function createServer(env: Env) {
  const server = new McpServer({
    name: "Emeka45 Cloudflare Bridge",
    version: "1.1.0",
  });

  server.registerTool(
    "cloudflare_connection_status",
    {
      description: "Check whether this bridge has its private Cloudflare configuration. Never returns credential values.",
      inputSchema: {},
    },
    async () => ({
      content: [{
        type: "text",
        text: JSON.stringify({
          connected: Boolean(env.CLOUDFLARE_API_TOKEN && env.CLOUDFLARE_ACCOUNT_ID),
          accountIdConfigured: Boolean(env.CLOUDFLARE_ACCOUNT_ID),
          apiTokenConfigured: Boolean(env.CLOUDFLARE_API_TOKEN),
        }, null, 2),
      }],
    }),
  );

  server.registerTool(
    "cloudflare_account",
    {
      description: "Read basic information about the configured Cloudflare account.",
      inputSchema: {},
    },
    async () => {
      try {
        return {
          content: [{ type: "text", text: JSON.stringify(
            await cloudflareGet(env, `/accounts/${env.CLOUDFLARE_ACCOUNT_ID}`),
            null,
            2,
          ) }],
        };
      } catch (error) {
        return {
          isError: true,
          content: [{
            type: "text",
            text: error instanceof Error ? error.message : "Cloudflare request failed.",
          }],
        };
      }
    },
  );

  server.registerTool(
    "cloudflare_pages_projects",
    {
      description: "List Cloudflare Pages projects visible to this bridge's Cloudflare API token.",
      inputSchema: {},
    },
    async () => {
      try {
        return {
          content: [{ type: "text", text: JSON.stringify(
            await cloudflareGet(env, `/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/pages/projects`),
            null,
            2,
          ) }],
        };
      } catch (error) {
        return {
          isError: true,
          content: [{
            type: "text",
            text: error instanceof Error ? error.message : "Cloudflare Pages request failed.",
          }],
        };
      }
    },
  );

  return server;
}

const mcpHandler = {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    return createMcpHandler(() => createServer(env), { route: "/mcp" })(request, env, ctx);
  },
};

async function exchangeGitHubCode(
  request: Request,
  code: string,
  env: Env,
): Promise<GitHubUser> {
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) {
    throw new Error("GitHub OAuth credentials are not configured.");
  }

  const redirectUri = new URL("/callback", request.url).href;
  const tokenResponse = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      client_id: env.GITHUB_CLIENT_ID,
      client_secret: env.GITHUB_CLIENT_SECRET,
      code,
      redirect_uri: redirectUri,
    }),
  });

  const token = await tokenResponse.json() as { access_token?: string; error?: string };
  if (!tokenResponse.ok || !token.access_token) {
    throw new Error(token.error || "GitHub token exchange failed.");
  }

  const userResponse = await fetch("https://api.github.com/user", {
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token.access_token}`,
      "User-Agent": "Emeka45-Cloudflare-MCP-Bridge",
    },
  });

  if (!userResponse.ok) {
    throw new Error(`GitHub user lookup failed with HTTP ${userResponse.status}.`);
  }

  return await userResponse.json() as GitHubUser;
}

const defaultHandler: ExportedHandler<Env> = {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({
        ok: true,
        service: "Emeka45 Cloudflare Bridge",
        mcp: "/mcp",
        oauth: true,
      });
    }

    if (url.pathname === "/authorize" && request.method === "POST") {
      try {
        const form = await request.formData();
        const handle = form.get("handle");
        if (typeof handle !== "string" || !handle) {
          return new Response("Missing authorization handle.", { status: 400 });
        }

        const approved = await env.OAUTH_PROVIDER.approveConsent(request, handle);
        const upstream = await env.OAUTH_PROVIDER.beginUpstream(
          approved.request,
          { headers: approved.headers },
        );

        if (!env.GITHUB_CLIENT_ID) {
          return new Response("GitHub OAuth client is not configured.", { status: 503 });
        }

        const githubUrl = new URL("https://github.com/login/oauth/authorize");
        githubUrl.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
        githubUrl.searchParams.set("redirect_uri", new URL("/callback", request.url).href);
        githubUrl.searchParams.set("scope", "read:user");
        githubUrl.searchParams.set("state", upstream.state);

        const headers = new Headers(upstream.headers);
        headers.set("Location", githubUrl.href);
        return new Response(null, { status: 302, headers });
      } catch (error) {
        return new Response(
          error instanceof Error ? error.message : "Authorization approval failed.",
          { status: 400 },
        );
      }
    }

    if (url.pathname === "/authorize" && request.method === "GET") {
      try {
        const authRequest = await env.OAUTH_PROVIDER.parseAuthRequest(request);
        const description = await env.OAUTH_PROVIDER.describeConsent(authRequest);
        const transaction = await env.OAUTH_PROVIDER.beginConsent(authRequest);

        const requestedScopes = description.scopes.length
          ? description.scopes.map((scope) => `<li>${escapeHtml(scope)}</li>`).join("")
          : "<li>Cloudflare bridge access</li>";

        return page(
          "Authorize Emeka45 Cloudflare Bridge",
          `<h1>Connect ChatGPT to Cloudflare</h1>
          <p><strong>${escapeHtml(description.clientName)}</strong> is requesting access to this MCP server.</p>
          <div class="scope"><ul>${requestedScopes}</ul></div>
          <p class="muted">You will authenticate with GitHub before the bridge issues ChatGPT an access token. Your Cloudflare API token never leaves this Worker.</p>
          <form method="post" action="/authorize">
            <input type="hidden" name="handle" value="${escapeHtml(transaction.handle)}">
            <button type="submit">Continue with GitHub</button>
          </form>
          <p class="muted">Redirect destination: ${escapeHtml(description.redirectUriHostname)}</p>`,
          transaction.headers,
        );
      } catch (error) {
        return new Response(
          error instanceof Error ? error.message : "Invalid authorization request.",
          { status: 400 },
        );
      }
    }

    if (url.pathname === "/callback") {
      try {
        const { request: authRequest } = await env.OAUTH_PROVIDER.finishUpstream(request);
        const code = url.searchParams.get("code");
        if (!code) {
          return new Response("GitHub did not return an authorization code.", { status: 400 });
        }

        const user = await exchangeGitHubCode(request, code, env);
        if (!env.ALLOWED_GITHUB_USERNAME) {
          return new Response("Bridge access is not configured for an allowed GitHub account.", { status: 503 });
        }

        if (user.login.toLowerCase() !== env.ALLOWED_GITHUB_USERNAME.toLowerCase()) {
          return new Response("This GitHub account is not authorized to use this private bridge.", { status: 403 });
        }

        const { redirectTo } = await env.OAUTH_PROVIDER.completeAuthorization({
          request: authRequest,
          userId: user.login,
          scope: authRequest.scope,
          metadata: { label: `GitHub: ${user.login}` },
          props: { githubLogin: user.login },
        });

        return Response.redirect(redirectTo, 302);
      } catch (error) {
        return new Response(
          error instanceof Error ? error.message : "OAuth callback failed.",
          { status: 400 },
        );
      }
    }

    return new Response("Not found", { status: 404 });
  },
};

function createProvider(request: Request) {
  const resource = new URL("/mcp", request.url).href;
  const issuer = new URL("/", request.url).origin;

  return new OAuthProvider<Env>({
    apiRoute: "/mcp",
    apiHandler: mcpHandler,
    defaultHandler,
    authorizeEndpoint: "/authorize",
    tokenEndpoint: "/oauth/token",
    clientRegistrationEndpoint: "/oauth/register",
    scopesSupported: ["cloudflare:read"],
    requiredScopes: ["cloudflare:read"],
    resourceMetadata: {
      resource,
      authorization_servers: [issuer],
      scopes_supported: ["cloudflare:read"],
      resource_name: "Emeka45 Cloudflare Bridge",
    },
    clientIdMetadataDocumentEnabled: true,
  });
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    return createProvider(request).fetch(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;

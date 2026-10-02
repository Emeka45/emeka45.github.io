# Emeka45 Cloudflare Bridge

This Worker exposes a small, read-only MCP interface that lets a compatible AI client inspect the connected Cloudflare account.

## Tools

- cloudflare_connection_status — confirms required private bindings exist without returning their values.
- cloudflare_account — reads basic account information.
- cloudflare_pages_projects — lists Pages projects visible to the configured API token.

The first release deliberately exposes no write operations.

## Deploy

From this directory:

```bash
npm install
npx wrangler login
npx wrangler secret put CLOUDFLARE_API_TOKEN
npx wrangler secret put CLOUDFLARE_ACCOUNT_ID
npx wrangler secret put MCP_ACCESS_TOKEN
npm run deploy
```

Use a Cloudflare API token with only the permissions required by these read-only operations. Never commit secrets.

The deployed endpoints are:

- /health — service health check
- /mcp — Streamable HTTP MCP endpoint

Cloudflare currently recommends the stateless `createMcpHandler` approach for new MCP servers and Streamable HTTP on `/mcp`.

## ChatGPT connection

After deployment, add the Worker MCP endpoint in ChatGPT's connector/app development flow. If the client asks for bearer authentication, provide the value stored in `MCP_ACCESS_TOKEN`.

OAuth 2.1 can be added as the next stage after the read-only bridge is deployed and verified.

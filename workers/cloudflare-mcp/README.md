# Emeka45 Cloudflare MCP Bridge

This Worker exposes a small, read-only MCP bridge for the Emeka45 Cloudflare account and protects `/mcp` with OAuth 2.1 + PKCE.

## Architecture

ChatGPT (MCP client) → `/mcp` → Cloudflare OAuth Provider → GitHub sign-in → Cloudflare API.

The Worker keeps the Cloudflare API token server-side. It never returns the token to ChatGPT or the browser.

The OAuth provider publishes MCP protected-resource metadata dynamically from the request hostname, so the code does not hard-code a workers.dev account subdomain.

## Current tools

- `cloudflare_connection_status`
- `cloudflare_account`
- `cloudflare_pages_projects`

The bridge is intentionally read-only at this stage.

## Cloudflare secrets

Set these on the deployed Worker. Do **not** commit them:

```bash
npx wrangler secret put CLOUDFLARE_API_TOKEN
npx wrangler secret put CLOUDFLARE_ACCOUNT_ID
npx wrangler secret put GITHUB_CLIENT_ID
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put ALLOWED_GITHUB_USERNAME
```

The Cloudflare token should use only the permissions required by the tools you expose. For the current tools, start with account-scoped **Account Settings Read** and **Cloudflare Pages Read** rather than a broad all-account token.

## GitHub OAuth App

Create a GitHub OAuth App for this Worker after the Worker URL is known.

- Homepage: `https://<worker-host>/`
- Authorization callback: `https://<worker-host>/callback`

The GitHub login is only the upstream identity check. The Worker then issues its own MCP access token.

## KV

OAuth state, clients, grants and tokens use the `OAUTH_KV` binding. Wrangler supports automatic KV provisioning when the binding is declared without an ID; the resulting resource is managed by Cloudflare during deployment.

## Local validation

```bash
npm install
npm run typecheck
npx wrangler deploy --dry-run
```

## Deployment

```bash
npm run deploy
```

Then check:

`https://<worker-host>/health`

Do not open `/mcp` directly in a browser; it is an MCP protocol endpoint and expects an MCP client.

## Next connection step

Once the Worker is deployed and the GitHub OAuth callback is configured, add the deployed `/mcp` endpoint to ChatGPT as a remote MCP connector. ChatGPT should discover the protected-resource metadata, start Authorization Code + PKCE, open the Worker authorization page, and return to the MCP callback after GitHub authentication.

For a production release, add a custom domain and keep the Cloudflare API token narrowly scoped.
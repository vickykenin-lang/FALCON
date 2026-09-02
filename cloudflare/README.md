# Falcon Cloudflare zero-cost gateway

This adapter replaces the always-on Telegram polling process with an event-driven path:

Telegram webhook -> Cloudflare Worker -> Cloudflare Queue -> GitHub Actions -> existing Falcon Python Brain -> Telegram reply.

Falcon's Brain, governance, execution contracts, DeepSeek primary provider, Gemini fallback, and GitHub adapters remain in the existing Python system. The Cloudflare Worker is only a transport/runtime adapter and does not duplicate Falcon intelligence.

## Why this path

- No continuously running VM is required.
- Telegram delivers messages by webhook instead of long polling.
- Cloudflare Queue provides delivery/retry between the webhook and GitHub Actions.
- The existing GitHub Actions secrets for DeepSeek, Gemini, Telegram, and GitHub execution remain the model/runtime credentials.
- Cloudflare receives only two additional runtime secrets: the GitHub workflow-dispatch token and Telegram webhook validation secret.

## Cloudflare resources

Create one Worker from the `cloudflare/` directory and one Queue named `falcon-tasks`. `wrangler.jsonc` already binds the producer and consumer as `FALCON_TASKS`.

Worker variables/secrets:

- Variable: `FALCON_TELEGRAM_ALLOWED_USER_ID=1311732972`
- Secret: `FALCON_GITHUB_TOKEN` — Founder-owned GitHub token able to dispatch Actions in `vickykenin-lang/FALCON`
- Secret: `FALCON_TELEGRAM_WEBHOOK_SECRET` — Founder-created random webhook validation secret

Do not commit either secret.

## GitHub secret required for webhook setup

Add the same Founder-created webhook validation value as GitHub Actions secret:

- `FALCON_TELEGRAM_WEBHOOK_SECRET`

The Telegram bot token already remains in `FALCON_TELEGRAM_BOT_TOKEN` on GitHub.

## Deploy

From the `cloudflare/` directory with Wrangler authenticated to the Founder Cloudflare account:

1. Create Queue `falcon-tasks` if it does not exist.
2. Add the two Worker secrets listed above.
3. Deploy the Worker using `wrangler deploy`.
4. Verify `GET /health` returns `HEALTHY`.
5. Run the GitHub workflow `Configure Falcon Cloudflare Webhook` and supply the deployed Worker base URL.
6. Send `/health` to the Falcon Telegram bot, then send a plain-language mission.

## Free-tier guardrail

This design is intended for Cloudflare Workers Free + Queues Free usage. It deliberately avoids an always-on process. If Cloudflare Free limits are exceeded, operations should fail/stop rather than silently upgrade the architecture to a paid service. Founder approval is required before adopting any paid Cloudflare plan.

## Current limitation

GitHub Actions runners are ephemeral, so Falcon's local file-backed runtime memory is not yet durable across Cloudflare-dispatched missions. Live intelligence and governed mission execution work, but production memory persistence must be moved behind a replaceable durable-memory adapter before this Cloudflare path is considered full Part 4 certification.

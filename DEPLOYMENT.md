# Falcon persistent runtime

Falcon's production Telegram path is a long-running worker. The repository is host-agnostic: use the Docker image on any container platform that supports an always-on process, restart policy, secret injection, and a persistent volume.

## Required runtime secrets

- `FALCON_TELEGRAM_BOT_TOKEN`
- `FALCON_TELEGRAM_ALLOWED_USER_ID`
- At least one live intelligence key:
  - `FALCON_DEEPSEEK_API_KEY` (primary/recommended)
  - `FALCON_GEMINI_API_KEY` (automatic fallback when both are configured)

Optional:
- `FALCON_GITHUB_TOKEN` for private repositories or GitHub writes

## Recommended production configuration

- `FALCON_INTELLIGENCE_MODE=auto`
- `FALCON_DEEPSEEK_MODEL=deepseek-v4-pro`
- `FALCON_GEMINI_MODEL=gemini-3.7-flash`
- `FALCON_INTELLIGENCE_TIMEOUT=60`
- `FALCON_STATE_DIR=/data/falcon`
- `FALCON_GITHUB_WRITE_ENABLED=true` only when Founder intentionally enables write capability

`auto` selects DeepSeek first when configured and transparently falls back to Gemini if DeepSeek is unavailable or returns a plan that fails Falcon's plan contract validation. If only one key is present, Falcon uses that provider. If no live key is configured, Falcon fails closed rather than silently using a fake model.

## Container runtime

The Docker image starts the Telegram worker and stores checkpoints/memory under `/data/falcon`. Mount a persistent volume there. `compose.yaml` provides a host-neutral reference deployment with `restart: unless-stopped` and a named persistent volume.

Credentials must be supplied by the hosting platform's secret manager or process environment and must never be committed to this repository.

## Host acceptance requirements

Before choosing a production host, verify all of these against the actual plan/account: always-on background process support, container support, persistent volume support, secret manager/environment injection, automatic restart policy, outbound HTTPS to Telegram/DeepSeek/Gemini/GitHub, and acceptable monthly cost/quotas.

## Production acceptance

A deployment is not certified until all of the following are observed live:

1. Container remains running across idle periods.
2. Telegram `/health` receives a Falcon response.
3. A real DeepSeek-backed mission produces a valid Falcon plan.
4. A controlled DeepSeek failure causes Gemini fallback when Gemini is configured.
5. One governed execution produces evidence.
6. Runtime survives a host/container restart and reads its persistent state afterward.

No hosting vendor is part of Falcon's architecture or required by this repository.

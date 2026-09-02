# Falcon persistent runtime

Falcon's production Telegram path is a long-running worker. The repository is host-agnostic: deploy the Docker image on any container platform that supports an always-on process, restart policy, secret injection, and a persistent volume.

## Required runtime secrets

- `FALCON_TELEGRAM_BOT_TOKEN`
- `FALCON_TELEGRAM_ALLOWED_USER_ID`
- `FALCON_DEEPSEEK_API_KEY` (primary live intelligence)
- `FALCON_GEMINI_API_KEY` (automatic fallback)

Optional:
- `FALCON_GITHUB_TOKEN` for private repositories or GitHub writes

## Verified production intelligence configuration

- `FALCON_INTELLIGENCE_MODE=auto`
- `FALCON_DEEPSEEK_MODEL=deepseek-v4-pro`
- `FALCON_GEMINI_MODEL=gemini-3.5-flash-lite`
- `FALCON_INTELLIGENCE_TIMEOUT=60`
- `FALCON_GEMINI_MAX_ATTEMPTS=2`
- `FALCON_GEMINI_RETRY_DELAY=1`
- `FALCON_GEMINI_MAX_OUTPUT_TOKENS=4096`
- `FALCON_STATE_DIR=/data/falcon`
- `FALCON_GITHUB_WRITE_ENABLED=true` only when Founder intentionally enables write capability

`auto` selects DeepSeek first and transparently falls back to Gemini if DeepSeek is unavailable or returns a plan that fails Falcon's plan-contract validation. If no live key is configured, Falcon fails closed rather than silently using a fake model.

## Container runtime

The Docker image starts the Telegram worker and stores checkpoints/memory under `/data/falcon`. Mount a persistent volume at that exact path. `compose.yaml` provides a host-neutral reference with `restart: unless-stopped` and a named persistent volume.

The image healthcheck runs Falcon's `health` command. The CLI path is repository-tested and the Docker image is built in CI.

Credentials must be supplied by the selected hosting platform's secret manager or process environment and must never be committed to this repository. GitHub Actions secrets used for CI/live provider acceptance do not automatically transfer to a production host.

## Host acceptance requirements

Do not select or certify a host until its actual plan/account is verified for:

1. Always-on background worker support.
2. Container/Docker support.
3. Persistent writable storage for `/data/falcon`.
4. Secret/environment-variable injection.
5. Automatic restart/recovery behavior.
6. Outbound HTTPS access to Telegram, DeepSeek, Gemini, and GitHub.
7. Acceptable quota and recurring cost for the Founder.

## Production acceptance

A deployment is not certified until all of the following are observed live:

1. Container remains running across normal idle periods.
2. Telegram `/health` receives a Falcon response from the deployed runtime.
3. A real DeepSeek-backed mission produces a valid Falcon plan and governed execution evidence.
4. A controlled DeepSeek failure causes the configured Gemini fallback to succeed.
5. Runtime is restarted and Falcon continues with its persistent `/data/falcon` state available afterward.
6. If GitHub write/private access is enabled, a controlled governed GitHub action succeeds and is verified independently.

No hosting vendor is part of Falcon's architecture or required by this repository.

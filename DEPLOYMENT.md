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

Credentials must be supplied by the hosting platform's secret manager or process environment and must never be committed to this repository.

## Railway deployment profile

Railway is a compatible persistent-host option for this worker, but it is not part of Falcon's architecture.

1. Create a persistent service and connect `vickykenin-lang/FALCON` as its GitHub source. Railway should detect the root `Dockerfile` automatically.
2. Attach a volume mounted at `/data/falcon`.
3. Add the required runtime secrets and configuration variables listed above in the service Variables tab.
4. Because Railway volumes are mounted as root while Falcon's Docker image normally runs as the non-root `falcon` user, set `RAILWAY_RUN_UID=0` for the Railway deployment so `/data/falcon` is writable. This is a Railway-specific runtime compatibility setting, not a Falcon architecture dependency.
5. On a paid Railway plan, set Restart Policy to `Always` for the persistent Telegram worker. On plans where `Always` is unavailable, the platform's restart limits are weaker and should not be treated as production certification.
6. Do not override the Docker start command unless necessary; the Dockerfile already starts `python falcon.py --state-dir "$FALCON_STATE_DIR" telegram`.

GitHub Actions secrets used for CI/live provider acceptance do not automatically transfer to Railway or another host. Add host secrets independently through that platform's secret manager.

## Production acceptance

A deployment is not certified until all of the following are observed live:

1. Container remains running across normal idle periods.
2. Telegram `/health` receives a Falcon response from the deployed runtime.
3. A real DeepSeek-backed mission produces a valid Falcon plan and governed execution evidence.
4. A controlled DeepSeek failure causes the configured Gemini fallback to succeed.
5. Runtime is restarted and Falcon continues with its persistent `/data/falcon` state available afterward.
6. If GitHub write/private access is enabled, a controlled governed GitHub action succeeds and is verified independently.

No hosting vendor is part of Falcon's architecture or required by this repository.

# Falcon persistent runtime

Falcon's production Telegram path is a long-running worker. The repository includes a Dockerfile so the runtime can be deployed on any container host that supports an always-on worker and a persistent volume.

## Required runtime secrets

- `FALCON_TELEGRAM_BOT_TOKEN`
- `FALCON_TELEGRAM_ALLOWED_USER_ID`
- `FALCON_OPENAI_API_KEY` when `FALCON_INTELLIGENCE_MODE=openai`

## Recommended production configuration

- `FALCON_INTELLIGENCE_MODE=openai`
- `FALCON_OPENAI_MODEL=gpt-5.6-sol`
- `FALCON_INTELLIGENCE_TIMEOUT=60`
- `FALCON_STATE_DIR=/data/falcon`
- `FALCON_GITHUB_TOKEN` when authenticated/private/write GitHub access is required
- `FALCON_GITHUB_WRITE_ENABLED=true` only when Founder intentionally enables write capability

The container command is:

```sh
python falcon.py --state-dir "${FALCON_STATE_DIR:-/data/falcon}" telegram
```

Mount a persistent volume at `/data/falcon`. Credentials must be configured in the hosting provider's secret manager and must never be committed to this repository.

## Production acceptance

A deployment is not certified until all of the following are observed live: container remains running across normal idle periods, Telegram `/health` receives a Falcon response, one model-backed mission produces a structured plan, one governed execution produces evidence, and the runtime successfully resumes after a host restart with its persistent state volume attached.

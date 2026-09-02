FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FALCON_STATE_DIR=/data/falcon

WORKDIR /app

RUN useradd --create-home --uid 10001 falcon \
    && mkdir -p /data/falcon \
    && chown -R falcon:falcon /data/falcon /app

COPY --chown=falcon:falcon . /app

USER falcon

VOLUME ["/data/falcon"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python falcon.py --state-dir "${FALCON_STATE_DIR}" health >/dev/null || exit 1

CMD ["sh", "-c", "python falcon.py --state-dir \"${FALCON_STATE_DIR:-/data/falcon}\" telegram"]

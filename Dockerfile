# Revelio + WitnessTrace in one container.
# nginx (:8080) serves the React build and proxies /api and /wt-api to the Revelio
# gateway (127.0.0.1:8021), which forwards to WitnessTrace (127.0.0.1:8022).
# Both APIs stay on loopback inside the container; only 8080 is exposed.

ARG NODE_IMAGE=node:22-bookworm-slim
ARG PYTHON_IMAGE=python:3.14-slim

# ---- Frontend build ----------------------------------------------------------
FROM ${NODE_IMAGE} AS web
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---- Codex CLI (used by WitnessTrace for AI generation) ----------------------
FROM ${NODE_IMAGE} AS codex
ARG INSTALL_CODEX=1
ARG CODEX_VERSION=latest
RUN mkdir -p /opt/codex && if [ "$INSTALL_CODEX" = "1" ]; then \
      npm install --prefix /opt/codex --no-audit --no-fund "@openai/codex@${CODEX_VERSION}"; \
    fi

# ---- Runtime -----------------------------------------------------------------
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends nginx tini ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

WORKDIR /app
# One environment serves both APIs (see docs/integration/STARTUP_GUIDE.md).
COPY witness-backend/requirements-runtime-lock.txt /tmp/requirements.txt
COPY backend/requirements-speech.txt /tmp/requirements-speech.txt
RUN pip install -r /tmp/requirements.txt -r /tmp/requirements-speech.txt httpx==0.28.1 \
 && rm /tmp/requirements*.txt

# Local speech-to-text model for dictation, baked in so it works offline.
ARG WHISPER_MODEL=base.en
ENV REVELIO_WHISPER_MODEL=${WHISPER_MODEL} \
    REVELIO_WHISPER_DIR=/opt/whisper \
    REVELIO_WHISPER_OFFLINE=1
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/opt/whisper')" \
 && chmod -R a+rX /opt/whisper

# Node + Codex CLI. Empty when built with INSTALL_CODEX=0.
COPY --from=codex /usr/local/bin/node /usr/local/bin/node
COPY --from=codex /opt/codex /opt/codex
RUN if [ -x /opt/codex/node_modules/.bin/codex ]; then ln -s /opt/codex/node_modules/.bin/codex /usr/local/bin/codex; \
    else rm -f /usr/local/bin/node; fi

COPY backend/app ./backend/app
COPY witness-backend/*.py ./witness-backend/
COPY witness-backend/static ./witness-backend/static
COPY --from=web /src/dist ./dist
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/revelio-entrypoint

ENV REVELIO_RUNTIME_DIR=/data \
    REVELIO_DATA_DIR=/data/accounts \
    WITNESSTRACE_DATA_DIR=/data/data \
    WITNESSTRACE_OUTPUTS_DIR=/data/outputs \
    WITNESSTRACE_WORK_DIR=/data/work \
    WITNESSTRACE_GATEWAY_TARGET=http://127.0.0.1:8022 \
    REVELIO_HOSTED_PROVIDER= \
    CODEX_HOME=/home/app/.codex \
    HOME=/home/app

RUN mkdir -p /data /home/app/.codex && chown -R app:app /data /home/app
VOLUME ["/data"]
USER app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4)" || exit 1

ENTRYPOINT ["tini", "--", "revelio-entrypoint"]

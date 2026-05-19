# syntax=docker/dockerfile:1.24

ARG HERMES_REF=v2026.4.30

# ---------- Source fetch ----------
# renovate: datasource=docker depName=alpine/git
FROM alpine/git:2.52.0 AS src
ARG HERMES_REF
RUN git clone --depth=1 --branch ${HERMES_REF} \
    https://github.com/NousResearch/hermes-agent /src

# ---------- Pinned tool images (copy-only) ----------
# renovate: datasource=docker depName=node
FROM node:24.15.0-trixie-slim AS node
# renovate: datasource=docker depName=ghcr.io/astral-sh/uv
FROM ghcr.io/astral-sh/uv:0.11.15 AS uv

# ---------- Build stage ----------
# renovate: datasource=docker depName=python
FROM python:3.14.5-slim-trixie AS build

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/hermes/.playwright \
    npm_config_install_links=false \
    PATH="/opt/hermes/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential gcc python3-dev libffi-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /opt/hermes
COPY --from=src /src /opt/hermes

RUN npm install --prefer-offline --no-audit \
 && (cd web && npm install --prefer-offline --no-audit) \
 && (cd ui-tui && npm install --prefer-offline --no-audit) \
 && npm cache clean --force

RUN cd web && npm run build && cd ../ui-tui && npm run build

RUN uv venv && uv pip install --no-cache-dir -e ".[all]"

RUN npx playwright install --with-deps chromium --only-shell

# ---------- Runtime stage ----------
# renovate: datasource=docker depName=python
FROM python:3.14.5-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/hermes/.playwright \
    HERMES_WEB_DIST=/opt/hermes/hermes_cli/web_dist \
    HERMES_HOME=/opt/data \
    PATH="/opt/hermes/.venv/bin:/opt/data/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates tini ffmpeg ripgrep git openssh-client procps \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 10000 -m -d /opt/data hermes

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY --from=build --chown=10000:10000 /opt/hermes /opt/hermes

WORKDIR /opt/hermes
USER 10000
VOLUME ["/opt/data"]

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "hermes"]
CMD ["gateway", "run"]

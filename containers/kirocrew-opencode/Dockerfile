FROM docker.io/library/node:24-slim AS nodejs
FROM ghcr.io/kirodotdev/kirocrew:0.2.0

# renovate: datasource=npm depName=opencode-ai
ARG OPENCODE_VERSION=1.18.29

USER root

COPY --from=nodejs /usr/local/bin/node /usr/local/bin/node
COPY --from=nodejs /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm

RUN set -eux; \
    ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm; \
    ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx; \
    npm install -g "opencode-ai@${OPENCODE_VERSION}"; \
    npm cache clean --force; \
    rm -rf /usr/local/lib/node_modules/opencode-ai/node_modules/*-musl; \
    rm -rf /root/.npm /tmp/*; \
    node --version; \
    npx --version; \
    opencode --version

WORKDIR /opt/kirocrew-shim
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . faiss-cpu \
    && kirocrew-shim --version \
    && python3 -c "import faiss; print('faiss', faiss.__version__)" \
    && ln -sf /usr/local/bin/kirocrew-shim /usr/local/bin/kiro-cli

# Unpinned on purpose: apt resolves whatever gh is current at build time.
# Last so the layer cache misses whenever anything above changes -- otherwise
# `cache-from: type=gha` would serve a stale gh forever.
RUN set -eux; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /etc/apt/keyrings/githubcli-archive-keyring.gpg; \
    chmod 0644 /etc/apt/keyrings/githubcli-archive-keyring.gpg; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends gh; \
    rm -rf /var/lib/apt/lists/*; \
    gh --version

WORKDIR /home/kirocrew
USER kirocrew

# Must be absolute: ACP spawns the agent with cwd=<session work_dir>.
ENV KIROCREW_KIRO_BIN=/usr/local/bin/kirocrew-shim \
    OPENCODE_MODEL=ollama-cloud/gpt-oss:120b

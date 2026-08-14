# KiroCrew driving `opencode acp`
FROM ghcr.io/kirodotdev/kirocrew:0.2.0

# renovate: datasource=npm depName=opencode-ai
ARG OPENCODE_VERSION=1.18.18

USER root

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends nodejs npm; \
    npm install -g "opencode-ai@${OPENCODE_VERSION}"; \
    npm cache clean --force; \
    rm -rf /usr/local/lib/node_modules/opencode-ai/node_modules/*-musl; \
    apt-get purge -y --auto-remove nodejs npm; \
    rm -rf /var/lib/apt/lists/* /root/.npm /tmp/*; \
    opencode --version

WORKDIR /opt/kirocrew-shim
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --break-system-packages . \
    && kirocrew-shim --version

WORKDIR /home/kirocrew
USER kirocrew

# KIROCREW_KIRO_BIN must be ABSOLUTE: relative paths resolve against the
# gateway cwd, but ACP spawns the agent with cwd=<session work_dir>
# (kiro_prerequisite.py:504). It is checked before any PATH search
# (kiro_cli.py:73) so the bundled kiro-cli 2.16.2 is never reached.
ENV HOME=/home/kirocrew \
    KIROCREW_KIRO_BIN=/usr/local/bin/kirocrew-shim \
    OPENCODE_MODEL=ollama-cloud/gpt-oss:120b

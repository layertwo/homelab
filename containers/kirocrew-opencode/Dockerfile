# KiroCrew driving `opencode acp` against Ollama Cloud.
#
# Upstream KiroCrew is used UNMODIFIED -- no source patch. The shim is a
# translating ACP proxy on the stdio pipe (see
# docs/superpowers/specs/2026-08-10-kirocrew-ollama-design.md).
#
# Base image facts, read from the published 0.2.0 config rather than assumed:
#   debian trixie (apt-get, not apk) | python 3.12.13 already present
#   user kirocrew uid 1000 | WORKDIR /home/kirocrew | EXPOSE 5476
#   ENTRYPOINT ["kirocrew-entrypoint"] CMD ["gateway"] | KIROCREW_BIND=0.0.0.0
# Both ENTRYPOINT and CMD are inherited deliberately: the entrypoint does
# first-run sandbox probing and credential scrubbing we want to keep.
#
# Verified by building and running this image (see README "Verification"):
# /api/health returns 200, the full ACP handshake succeeds through the shim, and
# the entrypoint seeds agent.sandbox=auto because `unshare` works. Note the base
# image ships NO systemd-run, so KiroCrew logs a SECURITY warning that cgroup v2
# pids.max/memory.max ceilings are unenforced; RLIMIT_NOFILE still applies and
# the pod's own memory limit bounds the container as a whole.
FROM ghcr.io/kirodotdev/kirocrew:0.2.0

# Pinned to the version the ACP handshake + live turns were verified against.
ARG OPENCODE_VERSION=1.18.16

USER root

# nodejs+npm are BUILD-ONLY: the installed `opencode` is a native ELF binary
# (bin/opencode.exe, ~175MB), not a JS entrypoint, so nothing invokes node at
# runtime. Both are purged again below, verified by running `opencode --version`
# after the purge.
#
# The musl build is also dropped: this is glibc Debian, so it could never
# execute here. It is a distinct inode (~192MB) -- unlike bin/opencode.exe,
# which is a HARDLINK to the arm64 package's binary and therefore costs nothing
# extra. Deleting it would break the /usr/local/bin/opencode symlink chain.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends nodejs npm; \
    npm install -g "opencode-ai@${OPENCODE_VERSION}"; \
    npm cache clean --force; \
    rm -rf /usr/local/lib/node_modules/opencode-ai/node_modules/*-musl; \
    apt-get purge -y --auto-remove nodejs npm; \
    rm -rf /var/lib/apt/lists/* /root/.npm /tmp/*; \
    opencode --version

# The shim is a normal Python package (src/kirocrew_shim) installed into the
# base image's Python 3.12; its console script lands at
# /usr/local/bin/kirocrew-shim. It declares no dependencies, so this cannot
# perturb the gateway's own installed packages.
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
ENV KIROCREW_KIRO_BIN=/usr/local/bin/kirocrew-shim \
    OPENCODE_MODEL=ollama-cloud/gpt-oss:120b

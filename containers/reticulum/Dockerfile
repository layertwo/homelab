FROM python:3.14.7-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/

# UV_PYTHON_DOWNLOADS=0: use this image's interpreter, never a managed download.
# UV_COMPILE_BYTECODE=1: the runtime root filesystem is read-only, so compile now.
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

# --locked fails the build if uv.lock drifts from pyproject.toml. The two --version
# calls prove both entrypoints import (including the cryptography wheel).
RUN uv sync --locked \
    && rnsd --version \
    && lxmd --version

ENTRYPOINT ["rnsd", "--config", "/config"]

FROM python:3.14.5-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

EXPOSE 8080

# Improved Gunicorn configuration
ENTRYPOINT ["gunicorn", \
    "--bind", "0.0.0.0:8080", \
    "--workers", "4", \
    "--worker-class", "sync", \
    "--timeout", "30", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "100", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "oidc_saml_bridge.app:create_app()"]

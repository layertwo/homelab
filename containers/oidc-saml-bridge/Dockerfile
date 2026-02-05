FROM python:3.14.3-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

EXPOSE 8080

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8080", "oidc_saml_bridge.app:create_app()"]

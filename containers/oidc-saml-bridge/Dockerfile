FROM python:3.14.3-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

EXPOSE 8080

ENTRYPOINT ["oidc-saml-bridge"]

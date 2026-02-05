FROM python:3.14.3-slim
ARG UI_VERSION=v1.7.2

RUN apt update && apt upgrade && \
    apt install build-essential curl ffmpeg libpq-dev unzip -y --no-install-recommends && \
    apt clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/lib/opentakserver /app

# Download OpenTAKServer-UI
WORKDIR /var/lib/opentakserver
RUN mkdir -p ui && cd ui && \
    curl -L https://github.com/brian7704/OpenTAKServer-UI/releases/download/${UI_VERSION}/OpenTAKServer-UI-${UI_VERSION}.zip -o opentakserver-ui.zip && \
    unzip opentakserver-ui.zip && \
    mv opentakserver/* . && \
    rm -rf opentakserver opentakserver-ui.zip

WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt 

WORKDIR /var/lib/opentakserver
EXPOSE 8081 8088 8089
COPY entrypoint.sh /app

CMD ["/app/entrypoint.sh"]
# Flask will stop gracefully on SIGINT (Ctrl-C).
# Docker compose tries to stop processes using SIGTERM by default, then sends SIGKILL after a delay if the process doesn't stop.
STOPSIGNAL SIGINT

HEALTHCHECK --interval=1m CMD curl --fail http://localhost:8081/api/health || exit 1
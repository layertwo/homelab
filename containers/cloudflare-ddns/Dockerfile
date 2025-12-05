FROM python:3.14.1-slim

WORKDIR /app
COPY . /app
RUN pip install -e .

ENTRYPOINT ["do-dns-update"]

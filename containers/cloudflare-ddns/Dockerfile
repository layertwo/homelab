FROM python:3.13.2-slim

WORKDIR /app
COPY . /app
RUN pip install -e .

ENTRYPOINT ["do-dns-update"]

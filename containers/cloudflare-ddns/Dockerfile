FROM python:3.13.0-slim
COPY ./requirements.txt requirements.txt
RUN python -m pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./cloudflare_ddns.py /
ENTRYPOINT ["python3", "cloudflare_ddns.py"]

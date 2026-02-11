FROM python:3.12-slim

# Git for auto-push
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

# Git safe directory (mounted volume)
RUN git config --global --add safe.directory /app

EXPOSE 4343

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]

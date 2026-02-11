FROM python:3.12-slim

# Git + SSH for auto-push to GitHub
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

# Save default data & uploads so entrypoint can seed empty volumes
RUN cp -r /app/data /defaults-data && \
    mkdir -p /defaults-uploads && \
    cp -r /app/static/uploads /defaults-uploads/uploads

# SSH config: accept new host keys automatically (for git push to GitHub)
RUN mkdir -p /root/.ssh && \
    echo "Host github.com\n  StrictHostKeyChecking accept-new" > /root/.ssh/config && \
    chmod 600 /root/.ssh/config

# Git safe directory (mounted volume)
RUN git config --global --add safe.directory /app

EXPOSE 4343

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]

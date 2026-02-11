#!/bin/sh
set -e

# ── Seed empty volumes with default data (first run) ──────────
if [ ! -f /app/data/content.json ]; then
    echo "[init] Копирую данные по умолчанию в /app/data/ ..."
    cp -r /defaults-data/* /app/data/
fi

if [ ! -d /app/static/uploads/pages ]; then
    echo "[init] Создаю структуру /app/static/uploads/ ..."
    cp -r /defaults-uploads/uploads/* /app/static/uploads/
fi
# ──────────────────────────────────────────────────────────────

# Configure git identity if not already set
if [ -n "$GIT_USER_NAME" ]; then
    git config --global user.name "$GIT_USER_NAME"
fi
if [ -n "$GIT_USER_EMAIL" ]; then
    git config --global user.email "$GIT_USER_EMAIL"
fi

# Override git remote URL if provided (for SSH push from Portainer)
if [ -n "$GIT_REMOTE_URL" ]; then
    if git -C /app rev-parse --git-dir >/dev/null 2>&1; then
        # .git есть и это настоящий репозиторий
        current_remote=$(git -C /app remote get-url origin 2>/dev/null || echo "")
        if [ "$current_remote" != "$GIT_REMOTE_URL" ]; then
            echo "[init] Git remote origin → $GIT_REMOTE_URL"
            git -C /app remote set-url origin "$GIT_REMOTE_URL" 2>/dev/null || true
        fi
    else
        # .git отсутствует или повреждён — создаём новый
        echo "[init] Инициализация git-репозитория..."
        git init -b main /app 2>/dev/null || true
        git -C /app remote add origin "$GIT_REMOTE_URL" 2>/dev/null || \
            git -C /app remote set-url origin "$GIT_REMOTE_URL" 2>/dev/null || true
        echo "[init] Git remote origin → $GIT_REMOTE_URL"
    fi
fi

# Auto-setup upstream for push
git config --global push.autoSetupRemote true 2>/dev/null || true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Сайт:    http://0.0.0.0:4343"
echo "  Админка: http://0.0.0.0:4343/admin/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exec gunicorn \
    --bind 0.0.0.0:4343 \
    --workers 2 \
    --access-logfile - \
    --error-logfile - \
    app:app

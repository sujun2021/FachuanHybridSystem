#!/bin/sh
set -e

# 设置工作目录（支持两种挂载方式）
if [ -f "/app/apiSystem/manage.py" ]; then
    WORK_DIR="/app/apiSystem"
    cd /app/apiSystem
elif [ -f "/app/manage.py" ]; then
    WORK_DIR="/app"
    cd /app
else
    echo "Error: manage.py not found!"
    exit 1
fi

# 设置 uv 虚拟环境路径
VENV_BIN="/app/.venv/bin"
export PATH="$VENV_BIN:$PATH"

# 读取 .env 文件中的配置（支持生产/开发模式切换）
if [ -f "${WORK_DIR}/.env" ]; then
    echo "Loading environment from ${WORK_DIR}/.env..."
    set -a
    . "${WORK_DIR}/.env"
    set +a
elif [ -f "/app/apiSystem/.env" ]; then
    echo "Loading environment from /app/apiSystem/.env..."
    set -a
    . "/app/apiSystem/.env"
    set +a
fi

# PostgreSQL 连接检测
if [ "${DB_ENGINE:-postgresql}" = "postgres" ] || [ "${DB_ENGINE:-postgresql}" = "postgresql" ] || [ "${DB_ENGINE:-postgresql}" = "django.db.backends.postgresql" ]; then
  echo "Waiting for PostgreSQL..."
  uv run python - <<'PY'
import os
import time

import psycopg

host = os.environ.get("DB_HOST", "postgres")
port = int(os.environ.get("DB_PORT", "5432"))
name = os.environ.get("DB_NAME", "fachuan_dev")
user = os.environ.get("DB_USER", "postgres")
password = os.environ.get("DB_PASSWORD", "postgres")

deadline = time.time() + 60
while True:
    try:
        with psycopg.connect(host=host, port=port, dbname=name, user=user, password=password, connect_timeout=5):
            break
    except Exception:
        if time.time() >= deadline:
            raise
        time.sleep(2)
PY
fi

# Redis 连通性检测（当 REDIS_URL 配置了才检测）
if [ -n "${REDIS_URL:-}" ]; then
  echo "Waiting for Redis..."
  uv run python - <<'PY'
import os
import time
from urllib.parse import urlparse

redis_url = os.environ.get("REDIS_URL", "")
parsed = urlparse(redis_url)
host = parsed.hostname or "redis"
port = parsed.port or 6379

deadline = time.time() + 60
while True:
    try:
        import socket
        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(b"PING\r\n")
        resp = sock.recv(1024)
        sock.close()
        if b"PONG" in resp or b"+PONG" in resp:
            break
    except Exception:
        if time.time() >= deadline:
            raise
        time.sleep(2)
PY
fi

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Installing Gunicorn..."
uv pip install gunicorn   # <--- ✨ 就是加这一行！

echo "Starting server..."

# 判断运行模式
# 生产模式: DJANGO_DEBUG=False 或 RUN_MODE=production
# 开发模式: DJANGO_DEBUG=True 或 RUN_MODE=development（默认）
if [ "${DJANGO_DEBUG:-True}" = "False" ] || [ "${RUN_MODE:-development}" = "production" ]; then
    echo "Running in PRODUCTION mode (Gunicorn)..."
    echo "  DJANGO_DEBUG=${DJANGO_DEBUG}"
    echo "  RUN_MODE=${RUN_MODE:-development}"
    
    # 生产模式：使用 Gunicorn
# 先确保 gunicorn 安装在虚拟环境中
echo "Ensuring Gunicorn is installed..."
/app/.venv/bin/pip install gunicorn

    if [ -f "${WORK_DIR}/gunicorn_config.py" ]; then
    echo "Using gunicorn config: ${WORK_DIR}/gunicorn_config.py"
    exec sh -c "cd ${WORK_DIR} && /app/.venv/bin/gunicorn --config '${WORK_DIR}/gunicorn_config.py' apiSystem.wsgi:application"
    elif [ -f "/app/gunicorn_config.py" ]; then
    echo "Using gunicorn config: /app/gunicorn_config.py"
    exec sh -c "cd ${WORK_DIR} && /app/.venv/bin/gunicorn --config /app/gunicorn_config.py apiSystem.wsgi:application"
    else
    echo "No gunicorn config found, using default settings..."
    exec sh -c "cd ${WORK_DIR} && /app/.venv/bin/gunicorn --workers=4 --bind=0.0.0.0:8002 --timeout=120 --threads=4 apiSystem.wsgi:application"
    fi  
else
    echo "Running in DEVELOPMENT mode (Django dev server)..."
    echo "  DJANGO_DEBUG=${DJANGO_DEBUG}"
    echo "  RUN_MODE=${RUN_MODE:-development}"
    
    # 开发模式：使用 Django 内置服务器
    exec uv run python manage.py runserver --insecure 0.0.0.0:8002
fi
#!/bin/sh
set -e

echo "======================================"
echo "Starting Fachuan Backend Container..."
echo "======================================"

#
# 1. 自动识别 Django 项目目录
#

if [ -f "/app/apiSystem/manage.py" ]; then
    WORK_DIR="/app/apiSystem"
elif [ -f "/app/manage.py" ]; then
    WORK_DIR="/app"
else
    echo "ERROR: manage.py not found"
    exit 1
fi

cd "$WORK_DIR"

echo "WORK_DIR=$WORK_DIR"

#
# 2. Python 虚拟环境
#

export PATH="/app/.venv/bin:$PATH"

python --version || true
pip --version || true

#
# 3. 加载 .env
#

if [ -f "${WORK_DIR}/.env" ]; then
    echo "Loading .env..."
    set -a
    . "${WORK_DIR}/.env"
    set +a
fi

#
# 4. PostgreSQL 等待
#

if [ -n "${DB_HOST:-}" ]; then

echo "Waiting PostgreSQL..."

python <<PY
import os
import psycopg
import time

host=os.getenv("DB_HOST")
port=int(os.getenv("DB_PORT","5432"))
db=os.getenv("DB_NAME")
user=os.getenv("DB_USER")
pwd=os.getenv("DB_PASSWORD")

deadline=time.time()+120

while True:
    try:
        psycopg.connect(
            host=host,
            port=port,
            dbname=db,
            user=user,
            password=pwd,
            connect_timeout=5
        )
        print("Postgres Ready")
        break

    except Exception as e:

        if time.time()>deadline:
            raise e

        print("Waiting postgres...",e)
        time.sleep(2)

PY

fi

#
# 5. Redis 等待
#

if [ -n "${REDIS_URL:-}" ]; then

echo "Waiting Redis..."

python <<PY

import socket
import os
import time
from urllib.parse import urlparse

url=urlparse(os.getenv("REDIS_URL"))

host=url.hostname
port=url.port or 6379

deadline=time.time()+60

while True:

    try:

        s=socket.create_connection(
            (host,port),
            timeout=5
        )

        s.close()

        print("Redis Ready")

        break

    except Exception:

        if time.time()>deadline:
            raise

        time.sleep(2)

PY

fi

#
# 6. 数据库迁移
#

echo "Running migrate..."

python manage.py migrate --noinput

#
# 7. 收集静态文件
#

echo "Collect static..."

python manage.py collectstatic --noinput

#
# 8. 检查 gunicorn
#

if [ ! -f /app/.venv/bin/gunicorn ]; then

echo "Installing gunicorn..."

pip install gunicorn

fi

#
# 9. 启动
#

echo "======================================"
echo "Starting Gunicorn..."
echo "======================================"

echo "DJANGO_DEBUG=${DJANGO_DEBUG:-False}"
echo "RUN_MODE=${RUN_MODE:-production}"

if [ -f "${WORK_DIR}/gunicorn_config.py" ]; then

CONFIG="${WORK_DIR}/gunicorn_config.py"

elif [ -f "/app/backend/gunicorn_config.py" ]; then

CONFIG="/app/backend/gunicorn_config.py"

else

CONFIG=""

fi

if [ -n "$CONFIG" ]; then

echo "Using Config=$CONFIG"

exec /app/.venv/bin/gunicorn \
    apiSystem.wsgi:application \
    --config "$CONFIG"

else

echo "No gunicorn config"

exec /app/.venv/bin/gunicorn \
    apiSystem.wsgi:application \
    --bind 0.0.0.0:8002 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

fi
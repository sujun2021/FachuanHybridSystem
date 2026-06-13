"""Gunicorn 生产环境配置。

当 .env 中 DJANGO_DEBUG=False 时自动启用（docker-entrypoint.sh 判断后调用）。

通过环境变量控制：
- GUNICORN_WORKERS: worker 进程数（默认 1，适配单核 VPS）
- GUNICORN_THREADS: 每个 worker 的线程数（默认 2）
- GUNICORN_PORT: 监听端口（默认 8002）
"""

import os

# 绑定地址
bind = f"0.0.0.0:{os.getenv('GUNICORN_PORT', '8002')}"

# 单核 VPS 专用
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 超时（诉讼文书下载可能较慢）
timeout = 300
graceful_timeout = 30

# 进程命名（方便 ps 查看）
proc_name = "fachuan-gunicorn"

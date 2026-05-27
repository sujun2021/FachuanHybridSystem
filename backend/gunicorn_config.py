import os
import multiprocessing

# ============================================================
# Gunicorn 生产环境配置
# ============================================================

# 绑定地址和端口
bind = "0.0.0.0:8002"

# Worker 数量
# 推荐值: CPU核心数 * 2 + 1
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker 类型 (推荐使用 gthread 或 gevent)
worker_class = "gthread"

# 每个 Worker 的线程数
threads = int(os.environ.get("GUNICORN_THREADS", 4))

# 请求超时时间（秒）
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))

# 优雅重启超时时间
graceful_timeout = 30

# 最大请求数（超过后重启 Worker，防止内存泄漏）
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))

# 最大请求数的抖动范围
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 200))

# 预加载应用（减少内存占用，推荐生产环境使用）
preload_app = True

# 访问日志配置
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")  # "-" 表示标准输出
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")    # "-" 表示标准输出
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# 进程名称前缀
proc_name = "fachuan-web"

# 监听队列大小
backlog = int(os.environ.get("GUNICORN_BACKLOG", 2048))

# 环境变量传递
raw_env = [
    "DJANGO_SETTINGS_MODULE=apiSystem.settings",
]

# 启用发送文件（用于静态文件服务，配合 whitenoise）
sendfile = True

# 限制请求体大小（字节）
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
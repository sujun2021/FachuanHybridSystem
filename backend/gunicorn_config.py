import os

bind = "0.0.0.0:8002"

workers = int(
    os.getenv(
        "GUNICORN_WORKERS",
        "2"
    )
)

worker_class = "gthread"

threads = int(
    os.getenv(
        "GUNICORN_THREADS",
        "4"
    )
)

timeout = 120

graceful_timeout = 30

max_requests = 1000
max_requests_jitter = 100

#
# 先关掉 preload
#

preload_app = False

#
# 日志
#

accesslog="-"
errorlog="-"

loglevel="info"

proc_name="fachuan-web"

backlog=2048

raw_env=[
"DJANGO_SETTINGS_MODULE=apiSystem.settings"
]

limit_request_line=4094
limit_request_fields=100
limit_request_field_size=8190
import multiprocessing

import psutil

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

wsgi_app = "config.asgi"

# ---- LOGGING ----

loglevel = "info"

accesslog = "-"
access_log_format = '%(t)s %(h)s - "%(r)s" %(s)s %(L)s'

errorlog = "-"

# ---- TIMEOUTS ----

timeout = 30
graceful_timeout = timeout + 10

# ---- WORKERS ----

worker_class = "uvicorn.workers.UvicornWorker"
workers = multiprocessing.cpu_count() + 1

# ---- MEMORY ----

# Get total available memory in MiB
memory = int(psutil.virtual_memory().total * 0.7 // (2**20))

# ---- MAX REQUESTS ----

# Calculate max_requests (prevent memory leaks)
max_requests = max(200, memory * 50 // 1024)

# Set max_requests_jitter to 5% of max_requests
max_requests_jitter = max_requests // 20

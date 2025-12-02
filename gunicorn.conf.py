import multiprocessing

import psutil

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

wsgi_app = "config.wsgi"

accesslog = "-"

access_log_format = '%(t)s %(h)s - "%(m)s %(U)s" %(s)s %(L)s'

worker_class = "gthread"

# Calculate the number of workers (CPU + 1)
workers = multiprocessing.cpu_count() + 1

# Get total available memory in MiB
memory = psutil.virtual_memory().total // (2**20)

# Estimate max threads per worker (based on memory)
memory_per_worker = min(memory // workers, 192)

# Threads should be at least 2
threads = max(2, memory_per_worker // 128)

# Calculate max_requests (prevent memory leaks)
max_requests = max(200, memory * 50 // 1024)

# Set max_requests_jitter to 5% of max_requests
max_requests_jitter = max_requests // 20

# Scale timeout based on threading: more threads = less per-thread CPU time
timeout = max(30, 35 + (threads * 2))

# Graceful timeout: allow extra time for clean shutdown
graceful_timeout = timeout + 10

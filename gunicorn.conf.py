import multiprocessing

import psutil

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

wsgi_app = "config.wsgi"

# Basic settings

accesslog = "-"

# Calculate the number of workers (CPU * 2 + 1)
workers = (multiprocessing.cpu_count() * 2) + 1

# Get total available memory in GiB
memory = psutil.virtual_memory().total >> 30

# Estimate max threads per worker (based on memory)
memory_per_worker = memory / workers  # Available memory per worker (in GiB)

threads = max(2, int(memory_per_worker * 2))  # Allocate ~2 threads per GiB per worker

# Calculate max_requests (prevent memory leaks)
max_requests = max(300, int(memory * 50))  # 50 requests per GiB, minimum 300

# Set max_requests_jitter to 5% of max_requests
max_requests_jitter = max_requests // 20

# Base timeout: slightly above the database statement timeout (30s in PostgreSQL settings)
base_timeout = 35

# Scale timeout based on threading: more threads = less per-thread CPU time
timeout = max(30, base_timeout + (threads * 2))

# Graceful timeout: allow extra time for clean shutdown
graceful_timeout = timeout + 10  # Give workers 10 extra seconds to finish tasks

base_keepalive_timeout = (
    20  # 20 seconds, slightly shorter than the connection pool timeout
)

# Adjust keep-alive based on number of threads and CPU count (to scale with worker load)
keepalive_timeout = max(
    15, base_keepalive_timeout + (threads * 2)
)  # Ensure a reasonable value

# Add a max limit to avoid excessively long keep-alive times
keepalive_timeout = min(30, keepalive_timeout)  # Max keep-alive timeout capped at 30s

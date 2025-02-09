import multiprocessing

import psutil

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

wsgi_app = "config.wsgi"


# Basic settings

accesslog = "-"
timeout = 35
graceful_timeout = 40
threads = 2
keepalive = 5

# Calculate the number of workers (CPU * 2 + 1)
workers = (multiprocessing.cpu_count() * 2) + 1

# Get total available memory in GiB
memory = psutil.virtual_memory().total // (2**30)

# Set max_requests based on memory
max_requests = memory * 50

# Set max_requests_jitter to 5% of max_requests
max_requests_jitter = max_requests // 20

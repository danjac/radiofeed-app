import math
import multiprocessing

import psutil

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

wsgi_app = "listenwave.wsgi"

accesslog = "-"

# number of workers should be CPU*2 + 1
workers = multiprocessing.cpu_count() * 2 + 1

# total available memory in GB
memory = math.floor(psutil.virtual_memory().total / (pow(1000, 3)))

# set max_requests to arbitrary value of memory * 100
# e.g. 4GB = 400 max requests
max_requests = memory * 100

# set max_requests to 1/20 of max_requests
# e.g. max requests 800 = (800 / 20) 40 max_requests_jitter
max_requests_jitter = math.floor(max_requests / 20)

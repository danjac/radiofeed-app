import logging
import math
import multiprocessing

import psutil
from loguru import logger


class PropagateHandler(logging.Handler):
    """Propagate logs to Gunicorn."""

    def emit(self, record: logging.LogRecord) -> None:
        """Handle logging event."""
        logging.getLogger("gunicorn.error").handle(record)


logger.remove()
logger.add(PropagateHandler(), format="{message}")
logger.warning("Logging with Gunicorn")

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

wsgi_app = "radiofeed.wsgi"

accesslog = "-"

# number of workers should be CPU*2 + 1
workers = (multiprocessing.cpu_count() * 2) + 1

# total available memory in GB
memory = math.floor(psutil.virtual_memory().total / (pow(1000, 3)))

# set max_requests to arbitrary value of memory * 50
# e.g. 4GB = 200 max requests
max_requests = memory * 50

# set max_requests_jitter to 5% of max_requests
# e.g. max_requests 200 = (200 / 20) 10 max_requests_jitter
max_requests_jitter = math.floor(max_requests / 20)

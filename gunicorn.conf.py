from __future__ import annotations

import multiprocessing

# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

workers = multiprocessing.cpu_count() * 2 + 1

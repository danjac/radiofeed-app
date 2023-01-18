from __future__ import annotations

import multiprocessing

bind = "127.0.0.1:8000"

workers = multiprocessing.cpu_count() * 2 + 1

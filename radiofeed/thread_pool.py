import functools
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from django.db import close_old_connections, connections


def execute_thread_pool(fn: Callable, iterable: Iterable, **kwargs) -> list[Future]:
    """Execute a function in a thread pool and return the list of futures."""
    results = []
    threadsafe_fn = db_thread_safe(fn)
    with ThreadPoolExecutor(**kwargs) as executor:
        futures = [executor.submit(threadsafe_fn, item) for item in iterable]
        for future in as_completed(futures):
            results.append(future.result())
    return results


def db_thread_safe(fn: Callable) -> Callable:
    """Decorator to make a function threadsafe by managing database connections."""

    @functools.wraps(fn)
    def _inner(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            connections.close_all()

    return _inner

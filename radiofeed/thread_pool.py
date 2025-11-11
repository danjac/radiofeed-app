import functools
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

from django.db import close_old_connections, connections

T = TypeVar("T")
R = TypeVar("R")


def execute_thread_pool(
    fn: Callable[[T], R],
    iterable: Iterable[T],
    **kwargs,
) -> list[R]:
    """Execute a function in a thread pool and return the list of futures."""
    threadsafe_fn = db_thread_safe(fn)

    with ThreadPoolExecutor(**kwargs) as executor:
        return [
            future.result()
            for future in as_completed(
                executor.submit(threadsafe_fn, item) for item in iterable
            )
        ]


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

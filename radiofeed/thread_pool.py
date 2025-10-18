import functools
import logging
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from django.db import close_old_connections, connections

_logger = logging.getLogger(__name__)


def execute_thread_pool(
    fn: Callable,
    iterable: Iterable,
    *,
    raise_exception: bool = False,
    **kwargs,
) -> list[Future]:
    """Execute a function in a thread pool and return the list of futures."""
    results = []

    threadsafe_fn = db_thread_safe(fn)

    with ThreadPoolExecutor(**kwargs) as executor:
        futures = {executor.submit(threadsafe_fn, item): item for item in iterable}

        for future in as_completed(futures):
            try:
                result = future.result()
                _logger.debug("Task %s completed: %s", futures[future], result)
                results.append(result)
            except Exception as exc:
                _logger.exception(exc)
                if raise_exception:
                    raise

    _logger.debug("Tasks completed: %d", len(results))

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

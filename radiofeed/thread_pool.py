import functools
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from django.db import close_old_connections, connections


def execute_thread_pool(fn: Callable, iterable: Iterable) -> list[Future]:
    """Execute a function in a thread pool and return the list of futures."""
    results = []
    with DjangoThreadPoolExecutor() as executor:
        futures = [executor.submit(fn, item) for item in iterable]
        for future in as_completed(futures):
            results.append(future.result())
    return results


class DjangoThreadPoolExecutor(ThreadPoolExecutor):
    """
    ThreadPoolExecutor that automatically cleans up Django DB connections
    before and after running each task.
    """

    def submit(self, fn, *args, **kwargs) -> Future:
        """Handle DB connections around the task execution."""

        @functools.wraps(fn)
        def _handle(*args, **kwargs):
            close_old_connections()
            try:
                return fn(*args, **kwargs)
            finally:
                connections.close_all()

        return super().submit(_handle, *args, **kwargs)

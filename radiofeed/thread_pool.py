import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from django.db import close_old_connections

logger = logging.getLogger(__name__)


class DjangoThreadPoolExecutor(ThreadPoolExecutor):
    """A ThreadPoolExecutor that ensures Django's database connections are closed."""

    def submit(self, fn, *args, **kwargs):
        """Submit a callable to be executed with Django-safe threading."""

        def _fn(*args, **kwargs):
            close_old_connections()
            return fn(*args, **kwargs)

        return super().submit(_fn, *args, **kwargs)


def execute_thread_pool(
    fn: Callable[[Any], Any], items: Iterable[Any], **executor_kwargs
) -> list[Any]:
    """
    Run `fn(item)` for each item in `items` using Django-safe threads.
    Any kwargs are passed to DjangoThreadPoolExecutor (e.g., max_workers).
    Returns a list of results in the order they complete.
    """
    results = []
    with DjangoThreadPoolExecutor(**executor_kwargs) as executor:
        futures = {executor.submit(fn, item): item for item in items}
        for future in as_completed(futures):
            try:
                result = future.result()
                logger.debug("Result for %s: %s", futures[future], result)
                results.append(future.result())
            except Exception as exc:
                logger.exception(exc)
    logger.debug("%d tasks completed.", len(results))
    return results

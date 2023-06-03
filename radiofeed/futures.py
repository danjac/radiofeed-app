import itertools
from collections.abc import Callable, Iterable
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor as BaseThreadPoolExecutor

from django.db import connections


class ThreadPoolExecutor(BaseThreadPoolExecutor):
    """ThreadPoolExecutor with safemap() and safesubmit() methods."""

    def _close_db_connections(self, future: Future) -> None:
        connections.close_all()

    def safesubmit(self, fn: Callable, *args, **kwargs) -> Future:
        """Runs submit() on function, closing the DB connections when done."""
        future = self.submit(fn, *args, **kwargs)
        future.add_done_callback(self._close_db_connections)
        return future

    def safemap(self, fn: Callable, *iterables: Iterable) -> list[Future]:
        """Runs safesubmit() on each item of iterators, returning list of futures."""
        return [
            self.safesubmit(fn, item)
            for item in itertools.chain.from_iterable(iterables)
        ]

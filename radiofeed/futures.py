from collections.abc import Callable, Iterable
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor as BaseThreadPoolExecutor

from django.db import connections


class ThreadPoolExecutor(BaseThreadPoolExecutor):
    """ThreadPoolExecutor with safemap method."""

    def _close_db_connections(self, future: Future) -> None:
        connections.close_all()

    def safemap(self, iterable: Iterable, fn: Callable, *args, **kwargs):
        """Runs ThreadPoolExecutor.map on each item in iterable, closing the DB connections when done."""

        for item in iterable:
            future = self.submit(fn, item, *args, **kwargs)
            future.add_done_callback(self._close_db_connections)

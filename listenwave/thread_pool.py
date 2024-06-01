import itertools
from collections.abc import Callable, Iterable
from concurrent import futures

from django.db import connections


class DatabaseSafeThreadPoolExecutor(futures.ThreadPoolExecutor):
    """ThreadPoolExecutor subclass which handles closing DB connections for each thread."""

    def db_safe_submit(self, fn: Callable, *args, **kwargs) -> futures.Future:
        """Runs submit() on function, closing the DB connections when done."""
        future = self.submit(fn, *args, **kwargs)
        future.add_done_callback(self._close_db_connections)
        return future

    def db_safe_map(
        self, fn: Callable, *iterables: Iterable, **kwargs
    ) -> list[futures.Future]:
        """Runs db_safe_submit() on each item of iterators, returning list of futures."""
        return [
            self.db_safe_submit(fn, item, **kwargs)
            for item in itertools.chain.from_iterable(iterables)
        ]

    def _close_db_connections(self, future: futures.Future) -> None:
        connections.close_all()

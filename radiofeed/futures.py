from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor

from django.db import connections


def safemap(iterable: Iterable, fn: Callable, *args, **kwargs):
    """Runs ThreadPoolExecutor.map on each item in iterable, closing the DB connections when done."""

    def _done(future: Future) -> None:
        connections.close_all()

    with ThreadPoolExecutor() as executor:
        for item in iterable:
            future = executor.submit(fn, item, *args, **kwargs)
            future.add_done_callback(_done)

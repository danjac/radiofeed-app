import functools
import itertools
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from django.db import close_old_connections
from django.db.models import QuerySet

T = TypeVar("T")  # type of the worker argument
R = TypeVar("R")  # return type of the worker


def db_threadsafe(fn: Callable[[T], R]) -> Callable[[T], R]:
    """
    Decorator to make a worker thread-safe for Django DB connections.
    Ensures `close_old_connections()` is called at thread start and after the function.
    """

    @functools.wraps(fn)
    def _fn(arg: T) -> R:
        close_old_connections()  # thread start
        try:
            return fn(arg)
        finally:
            close_old_connections()  # cleanup

    return _fn


def map_thread_pool(
    fn: Callable[[T], R],
    iterable: Iterable[T],
    batch_size: int = 500,
) -> Iterator[R]:
    """
    Map a single-argument function over an iterable using a thread pool.
    Exceptions in the worker are propagated immediately via future.result().
    The worker is made thread-safe for Django DB connections.
    """
    fn = db_threadsafe(fn)

    # if QuerySet, evaluate as iterator() to avoid caching all results in memory
    if isinstance(iterable, QuerySet):
        iterable = iterable.iterator()

    with ThreadPoolExecutor() as executor:
        for batch in itertools.batched(iterable, batch_size, strict=False):
            yield from executor.map(fn, batch)

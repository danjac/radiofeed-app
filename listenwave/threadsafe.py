import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from django.db import close_old_connections

P = ParamSpec("P")  # parameters of the wrapped function
R = TypeVar("R")  # return type of the wrapped function


def db_threadsafe(fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to make a worker thread-safe for Django DB connections.

    Ensures `close_old_connections()` is called at thread start and after the function.
    """

    @functools.wraps(fn)
    def _fn(*args: P.args, **kwargs: P.kwargs) -> R:
        close_old_connections()  # thread start
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()  # cleanup

    return _fn

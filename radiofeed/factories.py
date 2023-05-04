import itertools
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class _NotSet:
    def __bool__(self) -> bool:
        return False


NotSet: Any = _NotSet()


class Sequence:
    """Returns an incremented sequence string."""

    def __init__(self, format_str: str, varname: str = "n"):
        self._counter = (
            format_str.format(**{varname: counter}) for counter in itertools.count()
        )

    def __call__(self) -> str:
        """Returns next string in sequence"""
        return next(self._counter)


def create_batch(factory: Callable[..., T], count: int, /, **kwargs) -> list[T]:
    """Create batch of models."""
    return [factory(**kwargs) for _ in range(count)]


def resolve(value: T | None, default_value: T | Callable[..., T | None]) -> T | None:
    """Returns default value if value is NotSet."""
    if value is NotSet:
        return default_value() if callable(default_value) else default_value
    return value

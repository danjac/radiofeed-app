from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class _NotSet:
    def __bool__(self) -> bool:
        return False


NotSet: Any = _NotSet()


def create_batch(factory: Callable[..., T], count: int, /, **kwargs) -> list[T]:
    """Create batch of models."""
    return [factory(**kwargs) for _ in range(count)]


def resolve(value: T | None, default_value: T | Callable[..., T | None]) -> T | None:
    """Returns default value if value is NotSet."""
    if value is NotSet:
        return default_value() if callable(default_value) else default_value
    return value

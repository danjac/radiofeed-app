from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


class _NotSet:
    def __bool__(self) -> bool:
        return False


NotSet: Any = _NotSet()


def create_batch(factory: Callable[..., T], count: int, /, **kwargs) -> list[T]:
    """Create batch of models."""
    return [factory(**kwargs) for i in range(0, count)]


def resolve(value: Any, default_value: Any) -> Any:
    """Returns default value if value is NotSet."""
    if value is NotSet:
        return default_value() if callable(default_value) else default_value
    return value

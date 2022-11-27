from __future__ import annotations

from typing import Callable, TypeVar
from unittest.mock import sentinel

T = TypeVar("T")


NotSet = sentinel.NotSet


def create_batch(factory: Callable[..., T], count: int, /, **kwargs) -> list[T]:
    """Create batch of models."""
    return [factory(**kwargs) for i in range(0, count)]

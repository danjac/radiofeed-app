from __future__ import annotations

import functools
import uuid

from typing import Any, Callable, TypeVar

from django.utils import timezone
from faker import Faker

T = TypeVar("T")

_faker = Faker()


class _NotSet:
    def __bool__(self) -> bool:
        return False


NotSet: Any = _NotSet()


def create_batch(factory: Callable[..., T], count: int, /, **kwargs) -> list[T]:
    """Create batch of models."""
    return [factory(**kwargs) for i in range(0, count)]


def default(value: Any, default_value: Any) -> Any:
    """Returns default value if value is NotSet."""
    if value is NotSet:
        return default_value() if callable(default_value) else default_value
    return value


# common defaults
#


default_name = functools.partial(default, default_value=_faker.name)
default_text = functools.partial(default, default_value=_faker.text)
default_now = functools.partial(default, default_value=timezone.now)
default_guid = functools.partial(default, default_value=lambda: uuid.uuid4().hex)

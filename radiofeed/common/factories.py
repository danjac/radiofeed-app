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


def notset(value: Any, default_value: Any) -> Any:
    """Returns default value if value is NotSet."""
    if value is NotSet:
        return default_value() if callable(default_value) else default_value
    return value


def create_batch(factory: Callable[..., T], count: int, /, **kwargs) -> list[T]:
    """Create batch of models."""
    return [factory(**kwargs) for i in range(0, count)]


notset_username = functools.partial(notset, default_value=_faker.unique.user_name)
notset_email = functools.partial(notset, default_value=_faker.unique.email)
notset_url = functools.partial(notset, default_value=_faker.unique.url)
notset_password = functools.partial(notset, default_value=_faker.password)
notset_name = functools.partial(notset, default_value=_faker.name)
notset_text = functools.partial(notset, default_value=_faker.text)
notset_datetime = functools.partial(notset, default_value=timezone.now)
notset_guid = functools.partial(notset, default_value=lambda: uuid.uuid4().hex)

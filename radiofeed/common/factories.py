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


def notset(value: Any, default_value: Any) -> Any:
    """Returns default value if value is NotSet."""
    if value is NotSet:
        return default_value() if callable(default_value) else default_value
    return value


# common notset defaults

guid_notset = functools.partial(notset, default_value=lambda: uuid.uuid4().hex)
name_notset = functools.partial(notset, default_value=_faker.name)
datetime_notset = functools.partial(notset, default_value=timezone.now)
email_notset = functools.partial(notset, default_value=_faker.unique.email)
password_notset = functools.partial(notset, default_value=_faker.password)
text_notset = functools.partial(notset, default_value=_faker.text)
url_notset = functools.partial(notset, default_value=_faker.unique.url)
username_notset = functools.partial(notset, default_value=_faker.unique.user_name)

from __future__ import annotations

import functools

from typing import Any, Callable, Iterable, TypeVar, Union

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.encoding import force_str

from audiotrails.podcasts.date_parser import parse_date

Validator = Union[Callable, list[Callable]]

Value = TypeVar("Value")


def conv(
    *values: Iterable[Value],
    convertor: Callable,
    validator: Validator | None = None,
    default: Value | Callable = None,
) -> Any:
    """Returns first (converted) non-falsy value. Otherwise returns default value"""
    try:
        return next(
            filter(None, map(lambda value: _conv(value, convertor, validator), values))
        )
    except StopIteration:
        return default() if callable(default) else default


def _conv(
    value: Value, convertor: Callable, validator: Validator | None = None
) -> Value:
    try:
        return _validate(convertor(value), validator) if value else None
    except (ValidationError, TypeError, ValueError):
        return None


def _validate(value: Value, validator: Validator | None) -> Value:
    if None in (value, validator):
        return value

    validators = [validator] if callable(validator) else validator

    for _validator in validators:
        _validator(value)

    return value


conv_str = functools.partial(conv, convertor=force_str, default="")
conv_bool = functools.partial(conv, convertor=bool, default=False)
conv_list = functools.partial(conv, convertor=list, default=list)
conv_int = functools.partial(conv, convertor=int)
conv_date = functools.partial(conv, convertor=parse_date)

conv_url = functools.partial(
    conv,
    convertor=force_str,
    default="",
    validator=URLValidator(schemes=["http", "https"]),
)

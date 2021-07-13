from __future__ import annotations

import functools

from typing import Any, Callable, Iterable, TypeVar, Union

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.encoding import force_str

from audiotrails.podcasts.date_parser import parse_date

Validator = Union[Callable, list[Callable]]

Value = TypeVar("Value")


def coerce(
    *values: Iterable[Value],
    fn: Callable,
    validator: Validator | None = None,
    default: Value | Callable = None,
    **extra_kwargs,
) -> Any:
    """Returns first (coerced) non-falsy value. Otherwise returns default"""
    try:
        return next(
            filter(
                None,
                map(
                    lambda value: _coerce(value, fn, validator, **extra_kwargs), values
                ),
            )
        )
    except StopIteration:
        return default() if callable(default) else default


def _coerce(
    value: Value, fn: Callable, validator: Validator | None = None, **extra_kwargs
) -> Value:
    try:
        return _validate(fn(value, **extra_kwargs), validator) if value else None
    except (ValidationError, TypeError, ValueError):
        return None


def _validate(value: Value, validator: Validator | None) -> Value:
    if None in (value, validator):
        return value

    validators = [validator] if callable(validator) else validator

    for _validator in validators:
        _validator(value)

    return value


def _coerce_str(value: str, limit: int | None = None) -> str:
    value = force_str(value)
    if limit:
        value = value[:limit]
    return value


coerce_str = functools.partial(coerce, fn=_coerce_str, default="")
coerce_bool = functools.partial(coerce, fn=bool, default=False)
coerce_list = functools.partial(coerce, fn=list, default=list)
coerce_int = functools.partial(coerce, fn=int)
coerce_date = functools.partial(coerce, fn=parse_date)
coerce_url = functools.partial(
    coerce,
    fn=force_str,
    default="",
    validator=URLValidator(schemes=["http", "https"]),
)

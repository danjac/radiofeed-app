import dataclasses
from collections.abc import Callable

from django.http import HttpResponse

from simplecasts.http.request import HttpRequest


@dataclasses.dataclass(frozen=True, kw_only=False)
class BaseMiddleware:
    """Base middleware class."""

    get_response: Callable[[HttpRequest], HttpResponse]

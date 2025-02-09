import functools
from collections.abc import Callable

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from radiofeed.http import HttpResponseTooManyRequests


def throttle(rate_limit: int) -> Callable:
    """Decorator to throttle requests based on rate limit.

    If the rate limit is exceeded, return a 429 status code.

    If user is authenticated, use user's primary key as part of the cache key, otherwise use IP address.
    """

    def _decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            parts: list[str] = ["throttle", request.path]

            if request.user.is_authenticated:
                parts.append(str(request.user.pk))
            else:
                parts.append(request.META["REMOTE_ADDR"])

            key = ":".join(parts)

            if cache.get(key):
                return HttpResponseTooManyRequests()
            cache.set(key, value=True, timeout=rate_limit)
            return view(request, *args, **kwargs)

        return _wrapper

    return _decorator

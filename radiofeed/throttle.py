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
            key = "|".join(
                [
                    "throttle",
                    request.path,
                    _get_ident(request),
                ]
            )

            if cache.get(key):
                return HttpResponseTooManyRequests()

            cache.set(key, value=True, timeout=rate_limit)
            return view(request, *args, **kwargs)

        return _wrapper

    return _decorator


def _get_ident(request: HttpRequest) -> str:
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"

    if xff := request.headers.get("x-forwarded-for"):
        return f"ip:{xff.split(',')[0]}"

    return f"ip:{request.META['REMOTE_ADDR']}"

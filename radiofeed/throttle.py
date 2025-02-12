import functools
from collections.abc import Callable

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from radiofeed.http import HttpResponseTooManyRequests


def throttle(*, limit: int, duration: int) -> Callable:
    """Decorator to throttle requests.

    A cache key is checked with a timeout of `duration` seconds. If the key exists, the request is throttled.

    For example, to limit requests to 10 per minute:

        @throttle(10, 60)

    If user is authenticated, use user's primary key as part of the cache key, otherwise uses IP address.
    """

    def _decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            key = "|".join(
                [
                    "throttle",
                    request.path,
                    get_ident(request),
                ]
            )

            count = cache.get(key, 0)

            if count > limit:
                return HttpResponseTooManyRequests()

            cache.set(key, count + 1, timeout=duration)
            return view(request, *args, **kwargs)

        return _wrapper

    return _decorator


def get_ident(request: HttpRequest) -> str:
    """Returns throttle identifier based on user or IP address."""
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"

    if xff := request.headers.get("x-forwarded-for"):
        return f"ip:{xff.split(',')[0]}"

    return f"ip:{request.META['REMOTE_ADDR']}"

from __future__ import annotations

import functools

from typing import Any, Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject
from django.views.decorators.http import require_http_methods
from django_htmx.http import HttpResponseClientRedirect

from radiofeed.common.http import HttpResponseUnauthorized
from radiofeed.common.types import GetResponse

require_form_methods = require_http_methods(["GET", "POST"])


def middleware(
    middleware_fn: Callable[[HttpRequest, GetResponse], HttpResponse]
) -> GetResponse:
    """Create a middleware callable."""

    @functools.wraps(middleware_fn)
    def _wrapper(get_response: GetResponse) -> GetResponse:
        def _middleware(request: HttpRequest) -> HttpResponse:
            return middleware_fn(request, get_response)

        return _middleware

    return _wrapper


def lazy_object_middleware(attrname: str) -> GetResponse:
    """Creates middleware that sets request property with a SimpleLazyObject."""

    def _decorator(fn: Callable[[HttpRequest], Any]) -> GetResponse:
        @functools.wraps(fn)
        def _middleware(
            request: HttpRequest, get_response: GetResponse
        ) -> HttpResponse:
            setattr(request, attrname, SimpleLazyObject(lambda: fn(request)))
            return get_response(request)

        return middleware(_middleware)

    return _decorator


def require_auth(view: Callable) -> Callable:
    """Login required decorator also handling HTMX and AJAX views."""

    @functools.wraps(view)
    def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        if request.htmx:
            return HttpResponseClientRedirect(
                redirect_to_login(settings.LOGIN_REDIRECT_URL).url
            )

        # plain non-HTMX AJAX: return a 401
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponseUnauthorized()

        return redirect_to_login(request.get_full_path())

    return _wrapper

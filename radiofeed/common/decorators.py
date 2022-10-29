from __future__ import annotations

import functools

from typing import Callable
from urllib.parse import urlparse, urlunparse

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import resolve_url
from django.views.decorators.http import require_http_methods
from django_htmx.http import HttpResponseClientRedirect

from radiofeed.common.http import HttpResponseUnauthorized

require_form_methods = require_http_methods(["GET", "POST"])


def middleware(
    middleware_fn: Callable[[HttpRequest, Callable], HttpResponse]
) -> Callable:
    """Create a middleware callable."""

    @functools.wraps(middleware_fn)
    def _wrapper(get_response: Callable):
        def _middleware(request: HttpRequest) -> HttpResponse:
            return middleware_fn(request, get_response)

        return _middleware

    return _wrapper


def require_auth(view: Callable) -> Callable:
    """Login required decorator also handling HTMX and AJAX views.

    Use this decorator instead of @require_auth with views returning HTMX fragment and JSON responses.

    Returns redirect to login page if HTMX request, otherwise returns HTTP UNAUTHORIZED.
    """

    @functools.wraps(view)
    def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        #
        # plain non-HTMX AJAX: return a 401
        if (
            not request.htmx
            and request.headers.get("x-requested-with") == "XMLHttpRequest"
        ):
            return HttpResponseUnauthorized()

        if request.htmx:
            login_redirect_url = (
                resolve_url(
                    urlunparse(["", "", *list(urlparse(request.htmx.current_url))[2:]])
                )
                if request.htmx.current_url
                else request.get_full_path()
            )

            return HttpResponseClientRedirect(redirect_to_login(login_redirect_url).url)

        return redirect_to_login(request.get_full_path())

    return _wrapper

from __future__ import annotations

import functools

from typing import Callable
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
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

        response = redirect_to_login(
            _get_login_redirect_url(request), redirect_field_name=REDIRECT_FIELD_NAME
        )

        if request.htmx:
            return HttpResponseClientRedirect(response.url)

        return response

    return _wrapper


def _get_login_redirect_url(request: HttpRequest) -> str:
    if not request.htmx or request.htmx.target == "content":
        return request.get_full_path()

    if request.htmx.current_url:
        return resolve_url(
            urlunparse(["", "", *list(urlparse(request.htmx.current_url))[2:]])
        )
    return settings.LOGIN_REDIRECT_URL

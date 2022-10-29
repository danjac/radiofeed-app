from __future__ import annotations

import functools

from typing import Callable
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, QueryDict
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

        # HTMX: redirect to the current url
        if request.htmx:
            return _htmx_login_redirect(request)

        # plain non-HTMX AJAX: return a 401
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponseUnauthorized()

        # default behaviour
        return redirect_to_login(
            request.get_full_path(), redirect_field_name=REDIRECT_FIELD_NAME
        )

    return _wrapper


def _htmx_login_redirect(request: HttpRequest) -> HttpResponse:

    if request.htmx.boosted:
        redirect_to = request.get_full_path()

    elif request.htmx.current_url:
        # strip domain from current url
        redirect_to = resolve_url(
            urlunparse(["", ""] + list(urlparse(request.htmx.current_url))[2:])
        )
    else:
        redirect_to = settings.LOGIN_REDIRECT_URL

    resolved_url = resolve_url(settings.LOGIN_URL)
    login_url_parts = list(urlparse(resolved_url))

    qs = QueryDict(login_url_parts[4], mutable=True)
    qs[REDIRECT_FIELD_NAME] = redirect_to
    login_url_parts[4] = qs.urlencode(safe="/")

    return HttpResponseClientRedirect(urlunparse(login_url_parts))

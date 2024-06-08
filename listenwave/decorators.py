import functools

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import resolve_url
from django.views.decorators.http import require_http_methods

from listenwave.http import HttpResponseUnauthorized
from listenwave.types import HttpRequestResponse

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816


def ajax_login_required(view: HttpRequestResponse) -> HttpRequestResponse:
    """AJAX login required decorator. Returns an HTTP 401 Unauthorized
    if the user is not logged in."""

    @functools.wraps(view)
    def _view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        return HttpResponseUnauthorized()

    return _view


def htmx_login_required(
    view: HttpRequestResponse,
    redirect_field_name: str = REDIRECT_FIELD_NAME,
    login_url: str | None = None,
) -> HttpRequestResponse:
    """HTMX login required decorator for handling partials.

    Redirects to the HX-Current-URL header if available.

    HtmxRedirectMiddleware will ensure we send the correct HTMX redirect header.
    """

    @functools.wraps(view)
    def _view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        # Use HX-Current URL header if available
        # Note that the django-htmx checks this is "safe" i.e. belongs to current scheme
        path = request.htmx.current_url_abs_path or settings.LOGIN_REDIRECT_URL
        resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
        return redirect_to_login(path, resolved_login_url, redirect_field_name)

    return _view

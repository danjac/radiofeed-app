import functools
import http
from collections.abc import Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django_htmx.http import HttpResponseClientRedirect

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa


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
            return HttpResponse(status=http.HTTPStatus.UNAUTHORIZED)

        return redirect_to_login(request.get_full_path())

    return _wrapper

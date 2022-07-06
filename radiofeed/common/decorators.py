import functools

from typing import Callable

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django_htmx.http import HttpResponseClientRedirect

from radiofeed.common.http import HttpResponseUnauthorized


def ajax_login_required(view: Callable) -> Callable:
    """Login required decorator for HTMX and AJAX views.

    Use this decorator instead of @login_required with views returning HTMX fragment and JSON responses.

    Returns redirect to login page if HTMX request, otherwise returns HTTP UNAUTHORIZED.

    Args:
        view: Django view callable
    """

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        if request.htmx:
            return HttpResponseClientRedirect(
                redirect_to_login(
                    settings.LOGIN_REDIRECT_URL,
                    redirect_field_name=REDIRECT_FIELD_NAME,
                ).url
            )
        return HttpResponseUnauthorized()

    return wrapper

import functools

from typing import Callable

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django_htmx.http import HttpResponseClientRedirect


def ajax_login_required(view: Callable) -> Callable:
    """Use this decorator instead of @login_required
    when handling HTMX includes and JSON requests.

    If an HTMX request returns a client redirect to login page
    if user is not logged in, otherwise raises a 403.

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
        raise PermissionDenied

    return wrapper

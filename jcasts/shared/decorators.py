import functools

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden


def ajax_login_required(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        if request.htmx:
            response = HttpResponseForbidden()
            response["HX-Redirect"] = redirect_to_login(
                settings.LOGIN_REDIRECT_URL, redirect_field_name=REDIRECT_FIELD_NAME
            ).url
            response["HX-Refresh"] = "true"
            return response

        raise PermissionDenied

    return wrapper

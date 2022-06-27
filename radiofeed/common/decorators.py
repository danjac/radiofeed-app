import functools

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django_htmx.http import HttpResponseClientRedirect

from radiofeed.common.http import HttpResponseUnauthorized


def ajax_login_required(view):
    """Use this decorator instead of @login_required
    when handling HTMX fragment and JSON requests. For standard
    requests and full page HTMX responses use Django @login_required.

    If an HTMX request returns a client redirect to login page
    if user is not logged in, otherwise raises a 401.
    """

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
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

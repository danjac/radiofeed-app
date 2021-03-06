import datetime
import functools

from typing import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.utils import timezone


def with_new_user_cta(view: Callable) -> Callable:
    """Checks if new user CTA should be shown, sets cookie to hide afterwards"""

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        request.show_new_user_cta = (
            request.user.is_anonymous and "new-user-cta" not in request.COOKIES
        )
        response = view(request, *args, **kwargs)
        response.set_cookie(
            "new-user-cta",
            value="true",
            expires=timezone.now() + datetime.timedelta(days=30),
            samesite="Lax",
        )

        return response

    return wrapper


def ajax_login_required(view: Callable) -> Callable:
    """Returns a 403 Forbidden if user is not authenticated."""

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_anonymous:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper

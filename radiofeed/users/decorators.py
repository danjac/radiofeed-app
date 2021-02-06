import functools
from typing import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def ajax_login_required(view: Callable) -> Callable:
    """Returns a 403 Forbidden if user is not authenticated."""

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_anonymous:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper

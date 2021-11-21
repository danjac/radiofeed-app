from __future__ import annotations

import functools

from typing import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from jcasts.shared.htmx import hx_redirect_to_login


def ajax_login_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        if request.htmx:
            return hx_redirect_to_login()
        raise PermissionDenied

    return wrapper

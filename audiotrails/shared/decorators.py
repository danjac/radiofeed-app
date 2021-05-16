import functools
import json

from typing import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest


def accepts_json(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.content_type == "application/json":
            try:
                request.json = json.loads(request.body)
                return view(request, *args, **kwargs)
            except json.JSONDecodeError:
                return HttpResponseBadRequest("Invalid JSON payload")

        return HttpResponseBadRequest("Content-Type not application/json")

    return wrapper


def ajax_login_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        raise PermissionDenied

    return wrapper

import functools
import json

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest


def accepts_json(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.content_type == "application/json":
            try:
                request.json = json.loads(request.body)
                return view(request, *args, **kwargs)
            except json.JSONDecodeError:
                error_msg = "Invalid JSON payload"

        else:
            error_msg = "Content-Type not application/json"
        return HttpResponseBadRequest(error_msg)

    return wrapper


def ajax_login_required(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        raise PermissionDenied

    return wrapper

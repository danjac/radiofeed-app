import functools

from django.core.exceptions import PermissionDenied


def ajax_login_required(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        raise PermissionDenied

    return wrapper

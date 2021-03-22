import functools

from django.core.exceptions import PermissionDenied


def ajax_login_required(view):
    """Returns a 403 Forbidden if user is not authenticated."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_anonymous:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper

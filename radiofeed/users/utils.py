# Django
from django.core.exceptions import PermissionDenied


def user_display(user):
    """Returns default rendering of a user. Used with the
    django_allauth user_display template tag."""
    return user.name or user.username


def has_perm_or_403(user, permission, obj=None):
    """Checks if user has permission, raises PermissionDenied otherwise.

    Use in place of the auth @permission_required decorator
    when you want to do permission checks inside the view."""
    if not user.has_perm(permission, obj):
        raise PermissionDenied

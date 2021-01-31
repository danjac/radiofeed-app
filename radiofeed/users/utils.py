from django.conf import settings


def user_display(user: settings.AUTH_USER_MODEL) -> str:
    """Returns default rendering of a user. Used with the
    django_allauth user_display template tag."""
    return user.username

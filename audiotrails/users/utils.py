from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def user_display(user):
    """Returns default rendering of a user. Used with the
    django_allauth user_display template tag."""
    return user.username


def get_redirect_url(
    request,
    redirect_url_param="redirect_url",
    default_url=settings.HOME_URL,
):
    redirect_url = request.POST.get(redirect_url_param)
    if redirect_url and url_has_allowed_host_and_scheme(
        redirect_url, {request.get_host()}, request.is_secure()
    ):
        return redirect_url
    return default_url

from django import template
from django.conf import settings

from simplecasts.http.request import RequestContext

register = template.Library()


@register.inclusion_tag("cookie_banner.html", takes_context=True)
def cookie_banner(context: RequestContext) -> dict:
    """Renders GDPR cookie banner"""
    cookies_accepted = settings.GDPR_COOKIE_NAME in context.request.COOKIES
    return context.flatten() | {"cookies_accepted": cookies_accepted}

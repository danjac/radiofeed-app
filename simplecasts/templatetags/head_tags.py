import functools
import json

from django import template
from django.conf import settings
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from simplecasts.http.request import RequestContext
from simplecasts.services.pwa import get_theme_color

register = template.Library()


@register.simple_tag(takes_context=True)
def title_tag(context: RequestContext, *elements: str, divider: str = " | ") -> str:
    """Renders <title> content including the site name.

    Example:
        {% title_tag "About Us" "Company" %}
    Results in:
        <title>Simplecasts | About Us | Company</title>
    """
    content = divider.join((context.request.site.name, *elements))
    return format_html("<title>{}</title>", content)


@register.simple_tag
@functools.cache
def meta_tags() -> str:
    """Renders META tags from settings."""
    meta_tags = [
        *[
            {
                "name": key,
                "content": value,
            }
            for key, value in settings.META_TAGS.items()
        ],
        {
            "name": "theme-color",
            "content": get_theme_color(),
        },
        {
            "name": "copyright",
            "content": f"© {settings.META_TAGS['author']} {timezone.now().year}",
        },
        {
            "name": "htmx-config",
            "content": json.dumps(settings.HTMX_CONFIG),
        },
    ]
    return format_html_join(
        "\n",
        "<meta {}>",
        (
            (
                format_html_join(
                    " ",
                    '{}="{}"',
                    ((key, value) for key, value in meta.items()),
                ),
            )
            for meta in meta_tags
        ),
    )

import functools
import json
from datetime import timedelta

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.forms.utils import flatatt
from django.shortcuts import resolve_url
from django.template.context import Context
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString
from django.utils.timesince import timesince

from simplecasts import covers, sanitizer
from simplecasts.pwa import get_theme_color
from simplecasts.request import RequestContext

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


@register.simple_tag
@functools.cache
def get_cover_image_attrs(
    variant: covers.CoverVariant,
    cover_url: str,
    title: str,
) -> dict:
    """Returns cover image attributes."""
    return covers.get_cover_image_attrs(variant, cover_url, title)


@register.simple_tag
@functools.cache
def cover_image(
    variant: covers.CoverVariant,
    cover_url: str,
    title: str,
) -> str:
    """Renders a cover image."""
    attrs = get_cover_image_attrs(variant, cover_url, title)
    return format_html("<img {}>", flatatt(_clean_attrs(attrs)))


@register.simple_tag
def absolute_uri(site: Site, path: str, *args, **kwargs) -> str:
    """Returns absolute URI for the given path."""
    scheme = "https" if settings.USE_HTTPS else "http"
    url = resolve_url(path, *args, **kwargs)
    return f"{scheme}://{site.domain}{url}"


@register.inclusion_tag("markdown.html")
def markdown(text: str) -> dict:
    """Render content as Markdown."""
    return {"markdown": sanitizer.markdown(text)}


@register.inclusion_tag("cookie_banner.html", takes_context=True)
def cookie_banner(context: RequestContext) -> dict:
    """Renders GDPR cookie banner"""
    cookies_accepted = settings.GDPR_COOKIE_NAME in context.request.COOKIES
    return context.flatten() | {"cookies_accepted": cookies_accepted}


@register.simple_block_tag(takes_context=True)
def fragment(
    context: Context,
    content: str,
    template_name: str,
    *,
    only: bool = False,
    **extra_context,
) -> SafeString:
    """Renders include in block.

    Example:

    Calling template:

    {% fragment "header.html" %}
    title goes here
    {% endfragment %}

    header.html:

    <h1>{{ content }}</h1>

    Renders:

    <h1>title goes here</h1>

    If `only` is passed it will not include outer context.
    """

    context = context.new() if only else context

    if context.template is None:
        raise template.TemplateSyntaxError(
            "Can only be used inside a template context."
        )

    tmpl = context.template.engine.get_template(template_name)

    with context.push(content=content, **extra_context):
        return tmpl.render(context)


@register.filter
def format_duration(total_seconds: int, min_value: int = 60) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    return (
        timesince(timezone.now() - timedelta(seconds=total_seconds))
        if total_seconds >= min_value
        else ""
    )


def _clean_attrs(attrs: dict) -> dict:
    return {k.replace("_", "-"): v for k, v in attrs.items() if v not in (None, False)}

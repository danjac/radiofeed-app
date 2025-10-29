import functools
import json
from typing import Final

from django import forms, template
from django.conf import settings
from django.contrib.sites.models import Site
from django.shortcuts import resolve_url
from django.template.context import Context, RequestContext
from django.template.defaultfilters import pluralize
from django.utils.html import format_html_join

from radiofeed.cover_image import CoverImageVariant, get_cover_image_attrs
from radiofeed.html import render_markdown
from radiofeed.pwa import get_theme_color

_TIME_PARTS: Final = [
    ("hour", 60 * 60),
    ("minute", 60),
]

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)


@register.simple_tag
@functools.cache
def meta_tags() -> str:
    """Renders META tags from settings."""
    meta_tags = [
        *settings.META_TAGS,
        {
            "name": "htmx-config",
            "content": json.dumps(settings.HTMX_CONFIG),
        },
        {
            "name": "theme-color",
            "content": get_theme_color(),
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
def absolute_uri(site: Site, path: str, *args, **kwargs) -> str:
    """Returns absolute URI for the given path."""
    scheme = "https" if settings.USE_HTTPS else "http"
    url = resolve_url(path, *args, **kwargs)
    return f"{scheme}://{site.domain}{url}"


@register.simple_tag
def render_field(field: forms.Field, **attrs) -> str:
    """Returns rendered widget."""
    attrs = {
        k.replace(
            "_",
            "-",
        ): v
        for k, v in attrs.items()
        if v not in (None, False)
    }
    return field.as_widget(attrs=attrs)


@register.inclusion_tag("markdown.html")
def markdown(content: str | None) -> dict:
    """Render content as Markdown."""
    markdown = render_markdown(content) if content else ""
    return {"markdown": markdown}


@register.inclusion_tag("cover_image.html")
def cover_image(variant: CoverImageVariant, cover_url: str, title: str) -> dict:
    """Renders a cover image."""
    return {"attrs": get_cover_image_attrs(variant, cover_url, title)}


@register.inclusion_tag("cookie_banner.html", takes_context=True)
def cookie_banner(context: RequestContext):
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
) -> str:
    """Renders include in block.

    Example:

    {% fragment "header.html" %}
    title goes here
    {% endfragment %}

    header.html:
    <h1>{{ content }}</h1>

    If `only` is passed it will not include outer context.
    """

    if not context.template:
        raise template.TemplateSyntaxError(
            "Can only be used inside a template context."
        )

    tmpl = context.template.engine.get_template(template_name)

    context = context.new() if only else context

    with context.push(content=content, **extra_context):
        return tmpl.render(context)


@register.filter
def widget(field: forms.Field) -> forms.Widget:
    """Returns widget for field."""
    return field.field.widget


@register.filter
def widget_type(field: forms.Field) -> str:
    """Returns the widget class name for the bound field."""
    return widget(field).__class__.__name__.lower()


@register.filter
def format_duration(total_seconds: int) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    parts: list[str] = []
    for label, seconds in _TIME_PARTS:
        value = total_seconds // seconds
        total_seconds -= value * seconds
        if value:
            parts.append(f"{value} {label}{pluralize(value)}")
    return " ".join(parts)

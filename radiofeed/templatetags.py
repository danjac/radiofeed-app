import functools
import json
from typing import Final

from django import forms, template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import resolve_url
from django.template.context import Context, RequestContext
from django.template.defaultfilters import pluralize

from radiofeed import pwa
from radiofeed.cover_image import CoverImageVariant, get_cover_image_attrs
from radiofeed.html import render_markdown

_TIME_PARTS: Final = [
    ("hour", 60 * 60),
    ("minute", 60),
]

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)


_jsonify = functools.partial(json.dumps, cls=DjangoJSONEncoder)


@register.simple_tag
def get_meta_config() -> dict:
    """Returns META config settings."""
    return settings.META_CONFIG


@register.simple_tag
def get_htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return _jsonify(settings.HTMX_CONFIG)


@register.simple_tag
def get_theme_color() -> str:
    """Returns theme color in meta tag."""
    return pwa.get_theme_color()


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
    return {"cookies_accepted": cookies_accepted}


@register.simple_block_tag(takes_context=True)
def blockinclude(
    context: Context,
    content: str,
    template_name: str,
    *,
    only: bool = False,
    **extra_context,
) -> str:
    """Renders include in block.

    Example:

    {% blockinclude "header.html" %}
    title goes here
    {% endblockinclude %}

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
def widget_type(field: forms.Field) -> str:
    """Returns the widget class name for the bound field."""
    return field.field.widget.__class__.__name__.lower()


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

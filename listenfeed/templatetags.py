import functools
import json
import re

from django import forms, template
from django.conf import settings
from django.contrib.sites.models import Site
from django.forms.utils import flatatt
from django.shortcuts import resolve_url
from django.template.context import Context, RequestContext
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.timesince import timesince

from listenfeed.cover_image import CoverImageVariant, get_cover_image_attrs
from listenfeed.markdown import markdown
from listenfeed.pwa import get_theme_color

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)


@register.simple_tag(takes_context=True)
def title(context: RequestContext, *elements: str, divider: str = "|") -> str:
    """Renders <title> content including the site name.

    Example:
        {% title "About Us" "Company" %}
    Results in:
        Listenfeed | About Us | Company
    """
    return f" {divider} ".join((context.request.site.name, *elements))


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
            "name": "copyright",
            "content": f"© {settings.META_TAGS['author']} {timezone.now().year}",
        },
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
@functools.cache
def cover_image(variant: CoverImageVariant, cover_url: str, title: str) -> str:
    """Renders a cover image."""
    attrs = get_cover_image_attrs(variant, cover_url, title)
    return format_html("<img {}>", flatatt(_clean_attrs(attrs)))


@register.simple_tag
def absolute_uri(site: Site, path: str, *args, **kwargs) -> str:
    """Returns absolute URI for the given path."""
    scheme = "https" if settings.USE_HTTPS else "http"
    url = resolve_url(path, *args, **kwargs)
    return f"{scheme}://{site.domain}{url}"


@register.simple_tag
def render_field(field: forms.Field, **attrs) -> str:
    """Returns rendered widget."""
    return field.as_widget(attrs=_clean_attrs(attrs))


@register.inclusion_tag("markdown.html", name="markdown")
def markdown_(text: str) -> dict:
    """Render content as Markdown."""
    return {"markdown": markdown(text)}


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
def format_duration(total_seconds: int, min_value: int = 60) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    return (
        timesince(timezone.now() - timezone.timedelta(seconds=total_seconds))
        if total_seconds >= min_value
        else ""
    )


@register.filter
def websearch_clean(text: str) -> str:
    """Cleans a search query for websearch usage by removing special characters."""
    text = _re_websearch_syntax().sub(" ", text)
    text = _re_websearch_keywords().sub(" ", text)
    text = _re_whitespace().sub(" ", text)
    return text.strip()


def _clean_attrs(attrs: dict) -> dict:
    return {k.replace("_", "-"): v for k, v in attrs.items() if v not in (None, False)}


@functools.cache
def _re_websearch_syntax() -> re.Pattern:
    return re.compile(r'[+\-~"\'()<>]')


@functools.cache
def _re_websearch_keywords() -> re.Pattern:
    return re.compile(r"\b(AND|OR|NOT)\b", re.IGNORECASE)


@functools.cache
def _re_whitespace() -> re.Pattern:
    return re.compile(r"\s+")

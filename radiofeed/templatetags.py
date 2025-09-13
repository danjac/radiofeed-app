import functools
import itertools
import json
from typing import Final

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.utils import flatatt
from django.shortcuts import resolve_url
from django.template.context import Context
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
def htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return _jsonify(settings.HTMX_CONFIG)


@register.simple_tag
def theme_color() -> str:
    """Returns theme color in meta tag."""
    return pwa.get_theme_color()


@register.simple_tag
def absolute_uri(site: Site, path: str, *args, **kwargs) -> str:
    """Returns absolute URI for the given path."""
    scheme = "https" if settings.USE_HTTPS else "http"
    url = resolve_url(path, *args, **kwargs)
    return f"{scheme}://{site.domain}{url}"


@register.simple_tag
def attrs(**values) -> dict:
    """Returns attributes as dictionary."""
    return values


@register.simple_tag
def htmlattrs(*attrs: dict | None, **defaults) -> str:
    """Renders attributes as HTML attributes.

    Use with `attrs` to pass attributes to an include template.

    Example:

        {% attrs id="test" class="text-lg" required=True as attrs %}
        {% include "header.html" with attrs=attrs %}

    In include template:
        <h1 {% htmlattrs attrs id="xyz" class="text-red-100" %}>Header</h1>

    This would be rendered as:
        <h1 class="text-red-100 text-lg" id="test" required>Header</h1>

    Default values are overriden, except for `class`, which is appended.

    Note that snake case attribute names are converted to kebab case e.g. `hx_get` -> `hx-get`
    """
    merged = {}
    classes = []
    # Merge dictionaries, replacing "_" in name with "-"
    for dct in [defaults, *attrs]:
        if dct:
            clone = dct.copy()
            # Extract classes
            if classnames := clone.pop("class", None):
                classes.append(classnames)
            merged |= {name.replace("_", "-"): value for name, value in clone.items()}

    if classes:
        # Combine all the extracted class names
        merged["class"] = _merge_classes(*classes)

    return flatatt(merged)


@register.simple_block_tag(takes_context=True)
def blockinclude(
    context: Context,
    content: str,
    template_name: str,
    **extra_context,
) -> str:
    """Renders a block include.
    This is useful for rendering a block of HTML with a specific template.
    The included template should have a `content` variable that will be replaced.

    For example:

        header.html:

        <header>
            <h1>{{ title }}</h1>
            {{ content }}
        </header>

        Usage in a template:

        {% blockinclude "header.html" title="Home page" %}
            <p>This is the content of the blockinclude.</p>
        {% endblockinclude %}

        Renders as:

        <header>
            <h1>Home page</h1>
            <p>This is the content of the blockinclude.</p>
        </header>

    If `only` is passed then will only include the variables provided.
    """
    if context.template is None:
        raise template.TemplateSyntaxError(
            "blockinclude tag can only be used in a template context"
        )

    tmpl = context.template.engine.get_template(template_name)

    with context.push(content=content, **extra_context):
        return tmpl.render(context)


@register.inclusion_tag("cookie_banner.html", takes_context=True)
def cookie_banner(context: Context) -> dict:
    """Returns True if user has accepted cookies."""
    cookies_accepted = False
    if request := context.get("request", None):
        cookies_accepted = settings.GDPR_COOKIE_NAME in request.COOKIES
    return {
        "cookies_accepted": cookies_accepted,
        "request": request,
    }


@register.inclusion_tag("cover_image.html")
def cover_image(
    variant: CoverImageVariant,
    cover_url: str | None,
    title: str,
    **attrs,
) -> dict:
    """Renders a cover image."""
    return {
        "default_attrs": get_cover_image_attrs(
            variant,
            cover_url,
            title,
        ),
        "extra_attrs": attrs,
    }


@register.inclusion_tag("markdown.html")
def markdown(content: str | None) -> dict:
    """Render content as Markdown."""
    content = render_markdown(content) if content else ""
    return {"content": content}


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


def _merge_classes(*classnames: str) -> str:
    """Merges CSS classes into single string of unique names, preserving original order."""
    return " ".join(
        dict.fromkeys(
            itertools.chain.from_iterable([group.split() for group in classnames])
        ).keys()
    )

import dataclasses
import functools
import json
from collections.abc import Iterator
from typing import Any, Final

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.shortcuts import resolve_url
from django.template.context import RequestContext
from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from radiofeed import pwa
from radiofeed.cover_image import get_cover_image_attrs, get_cover_image_class
from radiofeed.html import render_markdown

_TIME_PARTS: Final = [
    ("hour", 60 * 60),
    ("minute", 60),
]

register = template.Library()

get_cover_image_attrs = register.simple_tag(get_cover_image_attrs)
get_cover_image_class = register.simple_tag(get_cover_image_class)


@dataclasses.dataclass(frozen=True)
class DropdownItem:
    """Dropdown navigation item."""

    label: str
    url: str
    icon: str = ""
    key: Any = None


@dataclasses.dataclass
class DropdownContext:
    """Info on dropdown."""

    selected: Any = None
    current: DropdownItem | None = None
    items: list[DropdownItem] = dataclasses.field(default_factory=list)

    def __bool__(self) -> bool:
        """Check if dropdown has any items."""
        return bool(self.items)

    def __len__(self) -> int:
        """Return number of items."""
        return len(self.items)

    def __iter__(self) -> Iterator[DropdownItem]:
        """Iterate over items."""
        return iter(self.items)

    def add(self, **kwargs) -> DropdownItem:
        """Add dropdown item."""
        item = DropdownItem(**kwargs)
        if item.key == self.selected:
            self.current = item
        else:
            self.items.append(item)
        return item


@register.simple_tag
def htmx_config() -> str:
    """Returns HTMX config in meta tag."""
    return format_html(
        '<meta name="htmx-config" content="{config}">',
        config=json.dumps(settings.HTMX_CONFIG, cls=DjangoJSONEncoder),
    )


@register.simple_tag
def theme_color() -> str:
    """Returns the PWA configuration theme color meta tag."""
    return format_html(
        '<meta name="theme-color" content="{color}">',
        color=pwa.get_theme_color(),
    )


@register.simple_tag
@functools.cache
def get_site() -> Site:
    """Returns the current Site instance. Use when `request.site` is unavailable, e.g. in emails run from cronjobs."""

    return Site.objects.get_current()


@register.simple_tag
def absolute_uri(url: Model | str | None = None, *url_args, **url_kwargs) -> str:
    """Returns the absolute URL to site domain."""

    site = get_site()
    path = resolve_url(url, *url_args, **url_kwargs) if url else ""
    scheme = "https" if settings.SECURE_SSL_REDIRECT else "http"

    return f"{scheme}://{site.domain}{path}"


@register.simple_tag(takes_context=True)
def get_accept_cookies(context: RequestContext) -> bool:
    """Returns True if user has accepted cookies."""
    return settings.GDPR_COOKIE_NAME in context.request.COOKIES


@register.filter
def markdown(content: str | None) -> str:
    """Render content as Markdown."""
    return render_markdown(content or "")


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

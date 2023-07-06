import math
import urllib.parse
from collections.abc import Iterator
from typing import TypedDict

from django import template
from django.core.signing import Signer
from django.http import HttpRequest, HttpResponse
from django.shortcuts import resolve_url
from django.template.base import Parser, Token
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe
from render_block import render_block_to_string

from radiofeed import cleaners

register = template.Library()


class ActiveLink(TypedDict):
    """Provides details on whether a link is currently active, along with its
    URL and CSS."""

    url: str
    css: str
    active: bool


def render_template_partials(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str | None = None,
    use_blocks: list | str | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Renders template blocks instead of whole template for an HTMX request.

    If `use_blocks` is a `list`, will render each named template block in list.

    If `use_blocks` is a `str`, will render the specified template block.

    The list of blocks will be passed to the template context as `use_blocks`.

    If `target` is provided, will render template blocks if HX-Target matches `target`.

    If not an HTMX request or the target does not match will render the entire template.
    """

    if (
        request.htmx
        and use_blocks
        and (target is None or target == request.htmx.target)
    ):
        if isinstance(use_blocks, str):
            use_blocks = [use_blocks]

        context = (context or {}) | {
            "use_blocks": use_blocks,
        }
        return HttpResponse(
            [
                render_block_to_string(
                    template_name,
                    block,
                    context,
                    request=request,
                )
                for block in use_blocks
            ],
            **response_kwargs,
        )
    return TemplateResponse(request, template_name, context, **response_kwargs)


@register.simple_tag(takes_context=True)
def active_link(
    context: RequestContext,
    url_name: str,
    css: str = "link",
    active_css: str = "active",
    *args,
    **kwargs,
) -> ActiveLink:
    """Returns url with active link info."""
    url = resolve_url(url_name, *args, **kwargs)

    return (
        ActiveLink(active=True, css=f"{css} {active_css}", url=url)
        if context.request.path == url
        else ActiveLink(active=False, css=css, url=url)
    )


@register.inclusion_tag("_markdown.html")
def markdown(value: str | None) -> dict:
    """Renders cleaned HTML/Markdown content."""
    return {"content": mark_safe(cleaners.clean_html(value or ""))}  # noqa


@register.inclusion_tag("_cookie_notice.html", takes_context=True)
def cookie_notice(context: RequestContext) -> dict:
    """Renders GDPR cookie notice. Notice should be hidden once user has clicked
    "Accept Cookies" button."""
    return {"accept_cookies": "accept-cookies" in context.request.COOKIES}


@register.simple_tag
def cover_image_url(cover_url: str | None, size: int) -> str:
    """Returns signed cover image URL."""
    return (
        reverse(
            "cover_image",
            kwargs={
                "size": size,
            },
        )
        + "?"
        + urllib.parse.urlencode({"url": Signer().sign(cover_url)})
        if cover_url
        else ""
    )


@register.inclusion_tag("_cover_image.html")
def cover_image(
    cover_url: str | None,
    size: int,
    title: str,
    url: str = "",
    css_class: str = "",
) -> dict:
    """Renders a cover image with proxy URL."""
    placeholder = static(f"img/placeholder-{size}.webp")

    return {
        "cover_url": cover_image_url(cover_url, size),
        "placeholder": placeholder,
        "title": title,
        "size": size,
        "url": url,
        "css_class": css_class,
    }


@register.filter
def format_duration(total_seconds: int | None) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1h 30min."""
    if total_seconds is None or total_seconds < 60:
        return ""

    rv: list[str] = []

    if total_hours := math.floor(total_seconds / 3600):
        rv.append(f"{total_hours}h")

    if total_minutes := round((total_seconds % 3600) / 60):
        rv.append(f"{total_minutes}min")

    return " ".join(rv)


class PaginationNode(template.Node):
    """Custom pagination node."""

    template_name = "_pagination.html"

    def __init__(self, nodelist: template.NodeList):
        self.nodelist = nodelist

    def render(self, context: RequestContext) -> str:
        """Render template tag contents"""
        page_obj = context["page_obj"]

        def _paginated_list_contents() -> Iterator[str]:
            for obj in page_obj:
                context.update({"object": obj})
                yield self.nodelist.render(context)

        next_page_url = (
            context.request.pagination.url(page_obj.next_page_number)
            if page_obj.has_next()
            else None
        )

        previous_page_url = (
            context.request.pagination.url(page_obj.previous_page_number)
            if page_obj.has_previous()
            else None
        )

        context.update(
            {
                "paginated_list_contents": _paginated_list_contents(),
                "next_page_url": next_page_url,
                "previous_page_url": previous_page_url,
            }
        )
        return render_to_string(
            self.template_name,
            context.flatten(),
            request=context.request,
        )


@register.tag
def pagination(parser: Parser, token: Token) -> PaginationNode:
    """Does a pagination."""
    nodelist = parser.parse(("endpagination",))
    parser.delete_first_token()
    return PaginationNode(nodelist)

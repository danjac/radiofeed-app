from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from django.core.paginator import InvalidPage, Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

_PARAM: Final = "page"
_TARGET: Final = "pagination"
_PAGE_SIZE: Final = 30


def pagination_url(request: HttpRequest, page_number: int) -> str:
    """Inserts the page query string parameter with the provided page number into the template.

    Preserves the original request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like: "/search?q=test&p=3"

    Returns:
        updated URL path with new page
    """
    qs = request.GET.copy()
    qs[_PARAM] = page_number
    return f"{request.path}?{qs.urlencode()}"


def render_pagination_response(
    request: HttpRequest,
    object_list: Iterable,
    template_name: str,
    pagination_template_name: str,
    extra_context: dict | None = None,
) -> HttpResponse:
    """Renders paginated response.

    Raises:
        Http404: invalid page number
    """
    try:
        page = Paginator(object_list, _PAGE_SIZE).page(request.GET.get(_PARAM, 1))

    except InvalidPage:
        raise Http404()

    template_name = (
        pagination_template_name
        if request.htmx and request.htmx.target == _TARGET
        else template_name
    )

    return render(
        request,
        template_name,
        {
            "page_obj": page,
            "pagination_target": _TARGET,
            "pagination_template": pagination_template_name,
            **(extra_context or {}),
        },
    )

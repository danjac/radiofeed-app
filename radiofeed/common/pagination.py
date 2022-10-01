from __future__ import annotations

from typing import Final, Iterable

from django.core.paginator import InvalidPage, Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

_DEFAULT_PAGINATION_PARAM: Final = "p"


def pagination_url(
    request: HttpRequest, page_number: int, param: str = _DEFAULT_PAGINATION_PARAM
) -> str:
    """Inserts the page query string parameter with the provided page number into the template.

    Preserves the original request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like: "/search?q=test&p=3"

    Returns:
        updated URL path with new page
    """
    params = request.GET.copy()
    params[param] = page_number
    return f"{request.path}?{params.urlencode()}"


def render_pagination_response(
    request: HttpRequest,
    object_list: Iterable,
    template_name: str,
    pagination_template_name: str,
    extra_context: dict | None = None,
    target: str = "object-list",
    param: str = _DEFAULT_PAGINATION_PARAM,
    page_size: int = 30,
    **pagination_kwargs,
) -> HttpResponse:
    """Renders paginated response.

    Raises:
        Http404: invalid page
    """
    try:
        page_obj = Paginator(
            object_list,
            page_size,
            **pagination_kwargs,
        ).page(request.GET.get(param, 1))
    except InvalidPage:
        raise Http404()

    return render(
        request,
        pagination_template_name
        if request.htmx and request.htmx.target == target
        else template_name,
        {
            "page_obj": page_obj,
            "pagination_target": target,
            "pagination_template": pagination_template_name,
            **(extra_context or {}),
        },
    )

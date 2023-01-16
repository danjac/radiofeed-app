from __future__ import annotations

from collections.abc import Iterable

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def render_pagination_response(
    request: HttpRequest,
    object_list: Iterable,
    template_name: str,
    pagination_template_name: str,
    extra_context: dict | None = None,
    page_size: int = 30,
    pagination_target: str = "pagination",
) -> HttpResponse:
    """Renders optimized paginated response.

    Conditionally renders to selected pagination template if matching HTMX target.

    Requires `CurrentPageMiddleware`.
    """
    template_name = (
        pagination_template_name
        if request.htmx and request.htmx.target == pagination_target
        else template_name
    )

    return render(
        request,
        template_name,
        {
            "page_obj": Paginator(object_list, page_size).get_page(
                request.page.current
            ),
            "pagination_target": pagination_target,
            "pagination_template": pagination_template_name,
            **(extra_context or {}),
        },
    )

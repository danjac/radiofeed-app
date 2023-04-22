from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from render_block import render_block_to_string


def render_pagination_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    page_size: int = 30,
    pagination_block: str = "pagination",
    pagination_target: str = "pagination",
) -> HttpResponse:
    """Renders optimized paginated response.

    Conditionally renders to selected pagination template if matching HTMX target.

    Requires `radiofeed.middleware.PaginationMiddleware` in MIDDLEWARE.
    """

    context = {
        "page_obj": Paginator(object_list, page_size).get_page(
            request.pagination.current
        ),
        "pagination_target": pagination_target,
        **(extra_context or {}),
    }

    if request.htmx and request.htmx.target == pagination_target:
        return HttpResponse(
            render_block_to_string(
                template_name,
                pagination_block,
                context,
                request=request,
            )
        )

    return render(request, template_name, context)

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from radiofeed.fragments import render_fragments_if_target


def render_paginated_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    page_size: int = 30,
    pagination_target: str = "pagination",
    use_blocks: list[str] | None = None,
) -> HttpResponse:
    """Renders optimized paginated response.

    Conditionally renders to selected pagination template if matching HTMX target.

    Adds `django.core.paginator.Page` instance to context as `page_obj`.

    Requires `radiofeed.middleware.PaginationMiddleware` in MIDDLEWARE.
    """
    context = {
        "page_obj": Paginator(object_list, page_size).get_page(
            request.pagination.current
        ),
        "pagination_target": pagination_target,
    } | (extra_context or {})

    return render_fragments_if_target(
        request,
        template_name,
        pagination_target,
        context,
        use_blocks=use_blocks or ["pagination"],
    )

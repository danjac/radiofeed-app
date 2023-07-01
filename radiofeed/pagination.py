from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from radiofeed.fragments import render_template_fragments


def render_paginated_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    context: dict | None = None,
    *,
    page_size: int = 30,
    pagination_target: str = "pagination",
    use_blocks: list[str] | None = None,
    **kwargs,
) -> HttpResponse:
    """Renders a paginated queryset.

    Adds Page instance `page_obj` to template context. If `pagination_target` matches HX-Target request header,
    will render the pagination block instead of the entire template.
    """
    context = (context or {}) | {
        "page_obj": Paginator(object_list, page_size).get_page(
            request.pagination.current
        ),
        "pagination_target": pagination_target,
    }
    use_blocks = use_blocks or ["pagination"]
    return render_template_fragments(
        request,
        template_name,
        context,
        target=pagination_target,
        use_blocks=use_blocks,
        **kwargs,
    )

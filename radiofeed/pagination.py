from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from radiofeed.partials import render_template_partials


def render_paginated_list(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    context: dict | None = None,
    *,
    page_size: int = 30,
    target: str = "pagination",
    use_blocks: list | str = "pagination",
    **response_kwargs,
) -> HttpResponse:
    """Renders a paginated queryset.

    Adds Page instance `page_obj` to template context. If `target` matches HX-Target request header,
    will render the pagination block instead of the entire template.
    """
    return render_template_partials(
        request,
        template_name,
        {
            "page_obj": Paginator(object_list, page_size).get_page(
                request.pagination.current
            ),
            "pagination_target": target,
        }
        | (context or {}),
        target=target,
        use_blocks=use_blocks,
        **response_kwargs,
    )

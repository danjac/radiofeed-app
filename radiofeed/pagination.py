from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest

from radiofeed.htmx import render_htmx_response


def render_pagination_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    context: dict | None = None,
    *,
    page_size: int = 30,
    partial: str = "pagination",
    target: str = "pagination",
    **kwargs,
):
    """Renders paginated object list.

    Will render partial if HTMX request matching target.
    """

    return render_htmx_response(
        request,
        template_name,
        {
            "page_obj": Paginator(object_list, page_size).get_page(
                request.pagination.current
            ),
            "pagination_target": target,
            **(context or {}),
        },
        partial=partial,
        target=target,
        **kwargs,
    )

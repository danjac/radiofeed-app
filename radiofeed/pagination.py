from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from radiofeed.htmx import render_htmx


def render_pagination(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    context: dict | None = None,
    *,
    page_size: int = 30,
    partial: str = "pagination",
    target: str = "pagination",
    **kwargs,
) -> HttpResponse:
    """Renders paginated object list.

    Will render partial if HTMX request matching target.
    """

    return render_htmx(
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

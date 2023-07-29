from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from radiofeed.htmx import render_template_blocks


def render_pagination_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    *,
    page_size: int = 30,
    use_blocks: list[str] | str = "pagination",
    target: str = "pagination",
    **response_kwargs,
) -> HttpResponse:
    """Renders template with paginated queryset."""

    return render_template_blocks(
        request,
        template_name,
        {
            "page_obj": Paginator(object_list, page_size).get_page(
                request.pagination.current
            ),
            "pagination_target": target,
            **(extra_context or {}),
        },
        use_blocks=use_blocks,
        target=target,
        **response_kwargs,
    )

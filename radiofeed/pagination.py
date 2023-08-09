from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_pagination(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    *,
    page_size: int = 30,
    target: str = "pagination",
) -> TemplateResponse:
    """Renders paginated object list."""

    return TemplateResponse(
        request,
        template_name,
        {
            "page_obj": Paginator(object_list, page_size).get_page(
                request.pagination.current
            ),
            "pagination_target": target,
            **(extra_context or {}),
        },
    )

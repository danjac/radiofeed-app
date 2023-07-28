from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_pagination_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    *,
    page_size: int = 30,
    pagination_target: str = "pagination",
    **response_kwargs,
) -> TemplateResponse:
    """Renders template with paginated queryset."""
    page_obj = Paginator(object_list, page_size).get_page(request.pagination.current)

    context = {
        "page_obj": page_obj,
        "pagination_target": pagination_target,
        **(extra_context or {}),
    }
    return TemplateResponse(request, template_name, context, **response_kwargs)

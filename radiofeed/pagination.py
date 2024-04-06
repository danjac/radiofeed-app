from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest

from radiofeed.htmx import HtmxTemplateResponse


class PaginationResponse(HtmxTemplateResponse):
    """Renders paginated object list."""

    def __init__(
        self,
        request: HttpRequest,
        object_list: QuerySet,
        template_name: str,
        context: dict | None = None,
        *,
        page_size: int = 30,
        partial: str = "pagination",
        target: str = "pagination",
    ) -> None:
        super().__init__(
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
        )

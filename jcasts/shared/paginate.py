from __future__ import annotations

from django.conf import settings
from django.core.paginator import InvalidPage, Page, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest


def paginate(
    request: HttpRequest,
    object_list: list | QuerySet,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    param: str = "page",
    allow_empty: bool = True,
    orphans: int = 0,
) -> Page:

    paginator = Paginator(
        object_list,
        page_size,
        allow_empty_first_page=allow_empty,
        orphans=orphans,
    )
    try:
        return paginator.page(int(request.GET.get(param, 1)))
    except (ValueError, InvalidPage):
        raise Http404("Invalid page")

from typing import Final

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

DEFAULT_PAGE_SIZE: Final = 30


def paginate(
    request: HttpRequest,
    queryset: QuerySet,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    param: str = "page",
) -> Page:
    """Returns paginated object."""
    return Paginator(queryset, page_size).get_page(request.GET.get(param, ""))


def paginate_lazy(*args, **kwargs) -> SimpleLazyObject:
    """Returns lazily-evaluated paginated object."""
    return SimpleLazyObject(lambda: paginate(*args, **kwargs))

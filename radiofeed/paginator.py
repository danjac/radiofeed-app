from typing import Final

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

DEFAULT_PAGE_SIZE: Final = 30


def paginate(
    request: HttpRequest,
    object_list: QuerySet,
    page_size: int = DEFAULT_PAGE_SIZE,
    param: str = "page",
    **pagination_kwargs,
) -> Page:
    """Returns pagination object."""

    return Paginator(object_list, page_size).get_page(
        request.GET.get(param, ""), **pagination_kwargs
    )


def paginate_lazy(*args, **kwargs) -> SimpleLazyObject:
    """Returns lazily-evaluated pagination object."""
    return SimpleLazyObject(lambda: paginate(*args, **kwargs))

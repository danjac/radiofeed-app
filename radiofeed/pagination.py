from collections.abc import Iterator
from typing import Final

from django.core.paginator import Page, Paginator
from django.http import HttpRequest

PAGE_SIZE: Final = 30


def paginate(
    request: HttpRequest,
    object_list: Iterator,
    *,
    page_size: int = PAGE_SIZE,
    param: str = "page",
    **kwargs,
) -> Page:
    """Returns paginated object list."""
    return Paginator(object_list, page_size).get_page(
        request.GET.get(param, ""), **kwargs
    )

from django.conf import settings
from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject


def paginate(
    request: HttpRequest,
    object_list: QuerySet,
    page_size: int = settings.PAGE_SIZE,
    param: str = "page",
    **pagination_kwargs,
) -> Page:
    """Returns paginated object list."""
    return Paginator(object_list, page_size).get_page(
        request.GET.get(param, ""), **pagination_kwargs
    )


def paginate_lazy(*args, **kwargs) -> SimpleLazyObject:
    """Returns lazily-evaluated pagination object.
    Use instead of `paginate()` in cases where the pagination is in a cached template snippet,
    so the database queries are not evaluated until the page obj is referenced.
    """
    return SimpleLazyObject(lambda: paginate(*args, **kwargs))

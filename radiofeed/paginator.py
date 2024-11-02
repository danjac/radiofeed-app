from django.conf import settings
from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.partials import render_partial_for_target


def paginate(
    request: HttpRequest,
    queryset: QuerySet,
    *,
    page_size: int | None = None,
    param: str = "page",
) -> Page:
    """Returns paginated object."""
    return Paginator(
        queryset,
        page_size or settings.DEFAULT_PAGE_SIZE,
    ).get_page(request.GET.get(param, ""))


def paginate_lazy(*args, **kwargs) -> SimpleLazyObject:
    """Returns lazily-evaluated paginated object."""
    return SimpleLazyObject(lambda: paginate(*args, **kwargs))


def render_paginated_response(  # noqa: PLR0913
    request: HttpRequest,
    template_name: str,
    queryset: QuerySet,
    extra_context: dict | None = None,
    target: str = "pagination",
    partial: str = "pagination",
    **pagination_kwargs,
) -> HttpResponse:
    """Render pagination response."""
    return render_partial_for_target(
        request,
        template_name,
        {
            "page": paginate_lazy(request, queryset, **pagination_kwargs),
            **(extra_context or {}),
        },
        target=target,
        partial=partial,
    )

from collections.abc import Sequence
from typing import Any

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.partials import render_partial_for_target


class CountlessPage(Sequence):
    """Pagination without COUNT(*) queries.

    See: https://testdriven.io/blog/django-avoid-counting/
    """

    def __init__(
        self,
        *,
        object_list: Sequence,
        number: int,
        has_next: bool,
        has_previous: bool,
    ) -> None:
        self.object_list = object_list
        self.number = number

        self._has_next = has_next
        self._has_previous = has_previous

    def __repr__(self) -> str:
        """Object representation."""
        return f"<Page {self.number}>"

    def __len__(self) -> int:
        """Returns total number of items"""
        return len(self.object_list)

    def __getitem__(self, index: int | slice) -> Any:
        """Returns indexed item."""
        return self.object_list[index]

    def next_page_number(self) -> int:
        """Returns the next page number."""
        if self.has_next():
            return self.number + 1
        raise EmptyPage("Next page does not exist")

    def previous_page_number(self) -> int:
        """Returns the previous page number."""
        if self.has_previous():
            return self.number - 1
        raise EmptyPage("Previous page does not exist")

    def has_next(self) -> bool:
        """Checks if there is a next page."""
        return self._has_next

    def has_previous(self) -> bool:
        """Checks if there is a previous page."""
        return self._has_previous

    def has_other_pages(self) -> bool:
        """Checks if there are other pages."""
        return self.has_previous() or self.has_next()


class CountlessPaginator:
    """Paginator without COUNT(*) queries."""

    def __init__(self, object_list: QuerySet | list, per_page: int) -> None:
        self.object_list = object_list
        self.per_page = per_page

    def validate_number(self, number: int | str) -> int:
        """Validates the page number."""
        try:
            number = int(number)
        except (TypeError, ValueError) as exc:
            raise PageNotAnInteger("Page number is not an integer") from exc
        if number < 1:
            raise EmptyPage("Page number is less than 1")
        return number

    def get_page(self, number: int | str) -> CountlessPage:
        """Returns a page object."""
        try:
            number = self.validate_number(number)
        except (PageNotAnInteger, EmptyPage):
            number = 1

        start = (number - 1) * self.per_page
        end = start + self.per_page + 1

        object_list = list(self.object_list[start:end])
        page_object_list = object_list[: self.per_page]

        has_next = len(object_list) > len(page_object_list)
        has_previous = number > 1

        return CountlessPage(
            object_list=page_object_list,
            number=number,
            has_next=has_next,
            has_previous=has_previous,
        )


def paginate(
    request: HttpRequest,
    queryset: QuerySet,
    *,
    page_size: int | None = None,
    param: str = "page",
) -> CountlessPage:
    """Returns paginated object."""
    return CountlessPaginator(
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

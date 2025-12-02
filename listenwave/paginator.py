from collections.abc import Sequence
from typing import TypeAlias, TypeVar

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db.models import Model, QuerySet
from django.template.response import TemplateResponse
from django.utils.functional import cached_property

from listenwave.partials import render_partial_response
from listenwave.request import HttpRequest

T = TypeVar("T")
T_Model = TypeVar("T_Model", bound=Model)

ObjectList: TypeAlias = Sequence[T | T_Model] | QuerySet[T_Model]


class Page:
    """Pagination without COUNT(*) queries.

    See: https://testdriven.io/blog/django-avoid-counting/

    The pagination should be done lazily, so we don't execute any database queries until the object list is accessed.
    """

    def __init__(self, *, paginator: "Paginator", number: int) -> None:
        self.paginator = paginator
        self.page_size = paginator.per_page
        self.number = number

    def __repr__(self) -> str:
        """Object representation."""
        return f"<Page {self.number}>"

    def __len__(self) -> int:
        """Returns total number of items"""
        return len(self.object_list)

    def __getitem__(self, index: int | slice) -> ObjectList:
        """Returns indexed item."""
        return self.object_list[index]

    @cached_property
    def next_page_number(self) -> int:
        """Returns the next page number."""
        if self.has_next:
            return self.number + 1
        raise EmptyPage("Next page does not exist")

    @cached_property
    def previous_page_number(self) -> int:
        """Returns the previous page number."""
        if self.has_previous:
            return self.number - 1
        raise EmptyPage("Previous page does not exist")

    @cached_property
    def has_next(self) -> bool:
        """Checks if there is a next page."""
        return len(self.object_list_with_next_item) > self.page_size

    @cached_property
    def has_previous(self) -> bool:
        """Checks if there is a previous page."""
        return self.number > 1

    @cached_property
    def has_other_pages(self) -> bool:
        """Checks if there are other pages."""
        return self.has_previous or self.has_next

    @cached_property
    def object_list(self) -> list:
        """Returns the object list."""
        return self.object_list_with_next_item[: self.page_size]

    @cached_property
    def object_list_with_next_item(self) -> list:
        """Returns object list including next item."""
        start = (self.number - 1) * self.page_size
        end = start + self.page_size + 1
        # Database query executed here with LIMIT and OFFSET
        return list(self.paginator.object_list[start:end])


class Paginator:
    """Paginator without COUNT(*) queries."""

    def __init__(self, object_list: ObjectList, per_page: int) -> None:
        self.object_list = object_list
        self.per_page = per_page

    def get_page(self, number: int | str) -> Page:
        """Returns a page object."""
        try:
            number = validate_page_number(number)
        except (PageNotAnInteger, EmptyPage):
            number = 1

        return Page(paginator=self, number=number)


def paginate(
    request: HttpRequest,
    object_list: ObjectList,
    *,
    param: str = "page",
    per_page: int = settings.DEFAULT_PAGE_SIZE,
) -> Page:
    """Paginate object list."""
    return Paginator(object_list, per_page=per_page).get_page(
        request.GET.get(param, "")
    )


def render_paginated_response(  # noqa: PLR0913
    request: HttpRequest,
    template_name: str,
    object_list: ObjectList,
    extra_context: dict | None = None,
    *,
    target: str = "pagination",
    partial: str = "pagination",
    **pagination_kwargs,
) -> TemplateResponse:
    """Render pagination response.

    This function is a wrapper around `render_partial_response` function.

    It renders a partial template with paginated data. The `Page` object is passed to the template context as `page`.
    """
    page = paginate(request, object_list, **pagination_kwargs)

    return render_partial_response(
        request,
        template_name,
        {
            "page": page,
            "page_size": page.page_size,
            "pagination_target": target,
        }
        | (extra_context or {}),
        target=target,
        partial=partial,
    )


def validate_page_number(number: int | str) -> int:
    """Validates the page number: it should be an integer greater than 1."""
    try:
        number = int(number)
    except (TypeError, ValueError) as exc:
        raise PageNotAnInteger("Page number is not an integer") from exc
    if number < 1:
        raise EmptyPage("Page number is less than 1")
    return number

from collections.abc import Sequence
from typing import TypeAlias, TypeVar

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db.models import Model, QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.functional import cached_property

from radiofeed.partials import render_partial_for_target

T = TypeVar("T")
T_Model = TypeVar("T_Model", bound=Model)

ObjectList: TypeAlias = Sequence[T | T_Model] | QuerySet[T_Model]


class Page:
    """Pagination without COUNT(*) queries.

    See: https://testdriven.io/blog/django-avoid-counting/

    The pagination should be done lazily, so we don't execute any database queries until the object list is accessed.
    """

    def __init__(
        self,
        *,
        paginator: "Paginator",
        number: int,
    ) -> None:
        self.paginator = paginator
        self.page_size = paginator.per_page
        self.number = number

    def __repr__(self) -> str:
        """Object representation."""
        return f"<Page {self.number}>"

    def __len__(self) -> int:
        """Returns total number of items"""
        return self._num_objects

    def __getitem__(self, index: int | slice) -> ObjectList:
        """Returns indexed item."""
        return self.object_list[index]

    def next_page_number(self) -> int:
        """Returns the next page number."""
        return self._next_page_number

    def previous_page_number(self) -> int:
        """Returns the previous page number."""
        return self._previous_page_number

    def has_next(self) -> bool:
        """Checks if there is a next page."""
        return self._has_next

    def has_previous(self) -> bool:
        """Checks if there is a previous page."""
        return self._has_previous

    def has_other_pages(self) -> bool:
        """Checks if there are other pages."""
        return self._has_other_pages

    @cached_property
    def object_list(self) -> list:
        """Returns the object list."""
        # Returns the object list for the current page. This should be bounded by the page size.
        return self._object_list[: self.page_size]

    @cached_property
    def _object_list(self) -> list:
        # Returns the object list for the current page. This should be slightly more than the page size.
        start = (self.number - 1) * self.page_size
        end = start + self.page_size + 1
        # Database query executed here with LIMIT and OFFSET
        return list(self.paginator.object_list[start:end])

    @cached_property
    def _has_next(self) -> bool:
        # If the object list is greater than the page size, then there is a next page.
        return len(self._object_list) > self.page_size

    @cached_property
    def _has_previous(self) -> bool:
        return self.number > 1

    @cached_property
    def _num_objects(self) -> int:
        return len(self.object_list)

    @cached_property
    def _next_page_number(self) -> int:
        if self.has_next():
            return self.number + 1
        raise EmptyPage("Next page does not exist")

    @cached_property
    def _previous_page_number(self) -> int:
        if self.has_previous():
            return self.number - 1
        raise EmptyPage("Previous page does not exist")

    @cached_property
    def _has_other_pages(self) -> bool:
        return self.has_previous() or self.has_next()


class Paginator:
    """Paginator without COUNT(*) queries."""

    def __init__(self, object_list: ObjectList, per_page: int) -> None:
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

    def get_page(self, number: int | str) -> Page:
        """Returns a page object."""
        try:
            number = self.validate_number(number)
        except (PageNotAnInteger, EmptyPage):
            number = 1

        return Page(paginator=self, number=number)


def paginate(
    request: HttpRequest,
    object_list: ObjectList,
    *,
    per_page: int | None = None,
    param: str = "page",
) -> Page:
    """Paginate object list."""
    return Paginator(
        object_list,
        per_page=per_page or settings.DEFAULT_PAGE_SIZE,
    ).get_page(request.GET.get(param, ""))


def render_pagination(  # noqa: PLR0913
    request: HttpRequest,
    template_name: str,
    object_list: ObjectList,
    extra_context: dict | None = None,
    *,
    target: str = "pagination",
    partial: str = "pagination",
    **pagination_kwargs,
) -> HttpResponse:
    """Render pagination response.

    This function is a wrapper around `render_partial_for_target` function.

    It renders a partial template with paginated data. The `Page` object is passed to the template context as `page`.
    """

    return render_partial_for_target(
        request,
        template_name,
        {
            "page": paginate(
                request,
                object_list,
                **pagination_kwargs,
            )
        }
        | (extra_context or {}),
        target=target,
        partial=partial,
    )

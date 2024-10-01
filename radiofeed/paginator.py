import dataclasses
from collections.abc import Iterable, Iterator
from typing import Final

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.functional import cached_property

DEFAULT_PAGE_SIZE: Final = 30


@dataclasses.dataclass(frozen=True)
class LazyPageObject:
    """Wrapper for Page/Paginator.

    Should only evaluate queryset when required in template.
    """

    request: HttpRequest
    queryset: QuerySet
    page_size: int = DEFAULT_PAGE_SIZE
    param: str = "page"

    def __bool__(self) -> bool:
        """Returns `True` if has any objects."""
        return self.count > 0

    def __iter__(self) -> Iterator:
        """Iterate through items in page."""
        return iter(self.object_list)

    @cached_property
    def paginator(self) -> Paginator:
        """Returns Paginator instance."""
        return Paginator(self.queryset, self.page_size)

    @cached_property
    def page(self) -> Page:
        """Returns current Page instance."""
        return self.paginator.get_page(self.request.GET.get(self.param, ""))

    @cached_property
    def count(self) -> int:
        """Return total number of objects."""
        return self.paginator.count

    @cached_property
    def object_list(self) -> Iterable:
        """Returns the page objects."""
        return self.page.object_list

    @cached_property
    def has_other_pages(self) -> bool:
        """If more than 1 page."""
        return self.page.has_other_pages()

    @cached_property
    def has_previous(self) -> bool:
        """Has previous page."""
        return self.page.has_previous()

    @cached_property
    def has_next(self) -> bool:
        """Has next page."""
        return self.page.has_next()

    @cached_property
    def previous_page(self) -> int | None:
        """Returns previous page or None if not any."""
        return self.page.previous_page_number() if self.has_previous else None

    @cached_property
    def next_page(self) -> int | None:
        """Returns next page or None if not any."""
        return self.page.next_page_number() if self.has_next else None


def paginate(request: HttpRequest, queryset: QuerySet, **kwargs) -> LazyPageObject:
    """Returns paginated result set."""
    return LazyPageObject(request, queryset, **kwargs)

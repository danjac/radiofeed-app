import dataclasses
from collections.abc import Iterator

from django.conf import settings
from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.functional import SimpleLazyObject, cached_property

from radiofeed.template import render_template_partial


@dataclasses.dataclass(frozen=True)
class CachedPage:
    """Page object wrapper using cached property values."""

    page: Page

    @cached_property
    def paginator(self) -> Paginator:
        """Returns Paginator instance."""
        return self.page.paginator

    @cached_property
    def object_list(self) -> Paginator:
        """Returns Paginator instance."""
        return self.page.object_list

    @cached_property
    def has_other_pages(self) -> bool:
        """If has other pages."""
        return self.page.has_other_pages()

    @cached_property
    def has_next(self) -> bool:
        """If has next page."""
        return self.page.has_next()

    @cached_property
    def has_previous(self) -> bool:
        """If has previous page."""
        return self.page.has_previous()

    @cached_property
    def next_page_number(self) -> bool:
        """If has next page."""
        return self.page.next_page_number()

    @cached_property
    def previous_page_number(self) -> bool:
        """If has previous page."""
        return self.page.previous_page_number()

    def __iter__(self) -> Iterator:
        """Iterate through current page items."""
        return iter(self.page)


def paginate(
    request: HttpRequest,
    object_list: QuerySet,
    page_size: int = settings.PAGE_SIZE,
    param: str = "page",
    **pagination_kwargs,
) -> CachedPage:
    """Returns paginated object list."""
    return CachedPage(
        page=Paginator(object_list, page_size).get_page(
            request.GET.get(param, ""), **pagination_kwargs
        )
    )


def paginate_lazy(*args, **kwargs) -> SimpleLazyObject:
    """Returns lazily-evaluated pagination object."""

    return SimpleLazyObject(lambda: paginate(*args, **kwargs))


def render_paginated_response(
    request: HttpRequest,
    template_name: str,
    object_list: QuerySet,
    extra_context: dict | None = None,
    **pagination_kwargs,
) -> TemplateResponse:
    """Shortcut for rendering a pagination template.

    This adds a `page_obj` to the template, which is a lazily-evaluated `Page` instance,
    i.e. database queries are not evaluated until page_obj is referenced in the template.
    """
    return render_template_partial(
        request,
        template_name,
        context={
            "page_obj": paginate_lazy(request, object_list, **pagination_kwargs),
        }
        | (extra_context or {}),
        partial="pagination",
        target="pagination",
    )
